"""Public storefront API - no auth required for browsing."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.card import Card
from app.models.inventory import InventoryItem
from app.models.product import Product

router = APIRouter(prefix="/api/v1/shop", tags=["shop"])


@router.get("/cards")
async def browse_cards(
    q: str | None = None,
    game: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=48),
    db: AsyncSession = Depends(get_db),
):
    """Browse cards available for online purchase."""
    query = (
        select(InventoryItem, Card.name_en, Card.image_url_small, Card.rarity, Card.set_id)
        .join(Card, InventoryItem.card_id == Card.id)
        .where(InventoryItem.available_online == True, InventoryItem.online_quantity > 0)
    )
    if q:
        query = query.where(Card.name_en.ilike(f"%{q}%"))
    if game:
        query = query.where(Card.game_id == game)

    total = (await db.execute(
        select(func.count(InventoryItem.id))
        .join(Card, InventoryItem.card_id == Card.id)
        .where(InventoryItem.available_online == True, InventoryItem.online_quantity > 0)
    )).scalar() or 0

    rows = (await db.execute(query.offset((page - 1) * per_page).limit(per_page))).all()

    return {
        "items": [
            {
                "id": inv.id, "card_id": inv.card_id, "name": name,
                "image_url": img, "rarity": rarity, "set_id": set_id,
                "condition": inv.condition, "is_foil": inv.is_foil,
                "price": inv.listed_price, "available": inv.online_quantity,
            }
            for inv, name, img, rarity, set_id in rows
        ],
        "total": total, "page": page, "per_page": per_page,
    }


@router.get("/products")
async def browse_products(
    game: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=48),
    db: AsyncSession = Depends(get_db),
):
    """Browse sealed products available for online purchase."""
    query = select(Product).where(Product.available_online == True, Product.online_quantity > 0)
    if game:
        query = query.where(Product.game_id == game)

    total = (await db.execute(
        select(func.count(Product.id)).where(Product.available_online == True, Product.online_quantity > 0)
    )).scalar() or 0

    rows = (await db.execute(query.offset((page - 1) * per_page).limit(per_page))).scalars().all()

    return {
        "items": [
            {
                "id": p.id, "name": p.name, "game_id": p.game_id,
                "product_type": p.product_type, "price": p.listed_price,
                "image_url": p.image_url, "available": p.online_quantity,
            }
            for p in rows
        ],
        "total": total, "page": page, "per_page": per_page,
    }
