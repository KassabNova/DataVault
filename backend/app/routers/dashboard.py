from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.card import Card
from app.models.inventory import InventoryItem
from app.models.sale import Sale

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    # Inventory stats
    inv_result = await db.execute(
        select(func.count(InventoryItem.id), func.sum(InventoryItem.quantity))
    )
    inv_row = inv_result.one()
    total_items = inv_row[0] or 0
    total_cards = inv_row[1] or 0

    # Inventory value
    value_result = await db.execute(
        select(func.sum(InventoryItem.listed_price * InventoryItem.quantity))
    )
    inventory_value = value_result.scalar() or 0

    # Cards in catalog
    catalog_count = (await db.execute(select(func.count(Card.id)))).scalar() or 0

    # Cards by game
    by_game = (await db.execute(
        select(Card.game_id, func.count(Card.id)).group_by(Card.game_id)
    )).all()

    # Today's sales
    today = date.today().isoformat()
    today_sales = (await db.execute(
        select(func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0))
        .where(Sale.created_at >= f"{today} 00:00:00")
    )).one()

    # Total sales all time
    all_sales = (await db.execute(
        select(func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0))
    )).one()

    # Low stock (quantity <= 2)
    low_stock = (await db.execute(
        select(func.count(InventoryItem.id))
        .where(InventoryItem.quantity <= 2, InventoryItem.quantity > 0)
    )).scalar() or 0

    return {
        "inventory": {
            "total_items": total_items,
            "total_cards": total_cards,
            "estimated_value": round(inventory_value, 2),
            "low_stock_count": low_stock,
        },
        "catalog": {
            "total_cards": catalog_count,
            "by_game": {row[0]: row[1] for row in by_game},
        },
        "sales": {
            "today_count": today_sales[0],
            "today_revenue": round(float(today_sales[1]), 2),
            "all_time_count": all_sales[0],
            "all_time_revenue": round(float(all_sales[1]), 2),
        },
    }
