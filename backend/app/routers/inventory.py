from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.card import Card
from app.models.inventory import InventoryItem
from app.schemas.inventory import (
    InventoryCreate,
    InventoryListResponse,
    InventoryResponse,
    InventoryUpdate,
)
from app.services.audit import log_action

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


def _to_response(item: InventoryItem, card_name: str | None = None, image_url: str | None = None, market_price: float | None = None) -> InventoryResponse:
    return InventoryResponse(
        id=item.id,
        card_id=item.card_id,
        card_name=card_name,
        quantity=item.quantity,
        condition=item.condition,
        language=item.language,
        is_foil=item.is_foil,
        purchase_price=item.purchase_price,
        listed_price=item.listed_price,
        notes=item.notes,
        image_url=image_url,
        market_price=market_price,
    )


@router.post("", response_model=InventoryResponse, status_code=201)
async def create_item(body: InventoryCreate, db: AsyncSession = Depends(get_db)):
    card = (await db.execute(select(Card).where(Card.id == body.card_id))).scalar_one_or_none()
    if not card:
        raise HTTPException(404, f"Card not found: {body.card_id}")

    item = InventoryItem(**body.model_dump())
    db.add(item)
    await db.flush()
    await log_action(db, "inventory_item", item.id, "create", body.model_dump())
    await db.commit()
    await db.refresh(item)
    return _to_response(item, card.name_en, card.image_url_small)


@router.get("", response_model=InventoryListResponse)
async def list_items(
    game: str | None = None,
    set_id: str | None = None,
    condition: str | None = None,
    card_type: str | None = None,
    is_foil: bool | None = None,
    in_stock: bool | None = None,
    q: str | None = None,
    sort: str = Query("recent", pattern="^(recent|name|price_asc|price_desc|quantity)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(InventoryItem, Card.name_en, Card.image_url_small).join(Card, InventoryItem.card_id == Card.id)
    count_query = select(func.count(InventoryItem.id)).select_from(InventoryItem).join(Card, InventoryItem.card_id == Card.id)

    if game:
        query = query.where(Card.game_id == game)
        count_query = count_query.where(Card.game_id == game)
    if set_id:
        query = query.where(Card.set_id == set_id)
    if condition:
        query = query.where(InventoryItem.condition == condition)
    if card_type:
        query = query.where(Card.card_type.ilike(f"%{card_type}%"))
    if is_foil is not None:
        query = query.where(InventoryItem.is_foil == is_foil)
    if in_stock:
        query = query.where(InventoryItem.quantity > 0)
    if q:
        query = query.where(Card.name_en.ilike(f"%{q}%"))

    # Sorting
    if sort == "name":
        query = query.order_by(Card.name_en)
    elif sort == "price_asc":
        query = query.order_by(InventoryItem.listed_price.asc().nullslast())
    elif sort == "price_desc":
        query = query.order_by(InventoryItem.listed_price.desc().nullsfirst())
    elif sort == "quantity":
        query = query.order_by(InventoryItem.quantity.desc())
    else:  # recent
        query = query.order_by(InventoryItem.added_at.desc())

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * per_page
    rows = (await db.execute(query.offset(offset).limit(per_page))).all()

    return InventoryListResponse(
        items=[_to_response(row[0], row[1], row[2]) for row in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/bulk-price-update")
async def bulk_price_update(db: AsyncSession = Depends(get_db)):
    """Apply pricing rules to update listed_price for all inventory items with market data."""
    from app.services.pricing import calculate_store_prices

    items = (await db.execute(
        select(InventoryItem, Card.game_id, Card.rarity)
        .join(Card, InventoryItem.card_id == Card.id)
    )).all()

    updated = 0
    for inv, game_id, rarity in items:
        prices = await calculate_store_prices(db, inv.card_id, game_id, rarity)
        if prices["sell_price"]:
            inv.listed_price = prices["sell_price"]
            updated += 1

    await db.commit()
    return {"updated": updated, "total": len(items)}


@router.get("/export/csv")
async def export_csv(db: AsyncSession = Depends(get_db)):
    """Export full inventory as CSV."""
    from fastapi.responses import StreamingResponse
    import io, csv

    rows = (await db.execute(
        select(InventoryItem, Card.name_en, Card.game_id, Card.set_id)
        .join(Card, InventoryItem.card_id == Card.id)
        .order_by(Card.game_id, Card.name_en)
    )).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["card_id", "name", "game", "set", "quantity", "condition", "language", "foil", "purchase_price", "listed_price", "available_online", "online_quantity"])
    for inv, name, game_id, set_id in rows:
        writer.writerow([inv.card_id, name, game_id, set_id, inv.quantity, inv.condition, inv.language, inv.is_foil, inv.purchase_price or "", inv.listed_price or "", inv.available_online, inv.online_quantity])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory.csv"},
    )


@router.get("/valuation")
async def inventory_valuation(db: AsyncSession = Depends(get_db)):
    """Inventory valuation report: cost vs market value."""
    from app.models.price import PriceRecord
    from app.config import settings

    items = (await db.execute(
        select(InventoryItem, Card.name_en, Card.game_id)
        .join(Card, InventoryItem.card_id == Card.id)
        .where(InventoryItem.quantity > 0)
    )).all()

    total_cost = 0.0
    total_market = 0.0
    total_listed = 0.0
    by_game: dict[str, dict] = {}

    for inv, name, game_id in items:
        qty = inv.quantity
        cost = (inv.purchase_price or 0) * qty
        listed = (inv.listed_price or 0) * qty

        price_row = (await db.execute(
            select(PriceRecord.price_market, PriceRecord.currency)
            .where(PriceRecord.card_id == inv.card_id)
            .order_by(PriceRecord.fetched_at.desc())
            .limit(1)
        )).one_or_none()

        market_val = 0.0
        if price_row and price_row[0]:
            rate = settings.usd_to_mxn if price_row[1] == "USD" else settings.usd_to_mxn * 1.08 if price_row[1] == "EUR" else 1
            market_val = price_row[0] * rate * qty

        total_cost += cost
        total_market += market_val
        total_listed += listed

        if game_id not in by_game:
            by_game[game_id] = {"cost": 0, "market": 0, "listed": 0, "items": 0}
        by_game[game_id]["cost"] += cost
        by_game[game_id]["market"] += market_val
        by_game[game_id]["listed"] += listed
        by_game[game_id]["items"] += 1

    return {
        "total_cost": round(total_cost, 2),
        "total_market_value": round(total_market, 2),
        "total_listed_value": round(total_listed, 2),
        "profit_potential": round(total_listed - total_cost, 2),
        "currency": "MXN",
        "by_game": {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in by_game.items()},
    }


@router.get("/audit-log")
async def get_audit_log(
    entity_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """View inventory change history."""
    from app.models.audit import AuditLog
    import json as _json
    query = select(AuditLog).where(AuditLog.entity_type == "inventory_item").order_by(AuditLog.created_at.desc())
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    rows = (await db.execute(query.limit(limit))).scalars().all()
    return [
        {"id": r.id, "entity_id": r.entity_id, "action": r.action,
         "changes": _json.loads(r.changes) if r.changes else None,
         "user": r.user, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]


@router.get("/{item_id}", response_model=InventoryResponse)
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
    row = (
        await db.execute(
            select(InventoryItem, Card.name_en, Card.image_url_small)
            .join(Card, InventoryItem.card_id == Card.id)
            .where(InventoryItem.id == item_id)
        )
    ).one_or_none()
    if not row:
        raise HTTPException(404, "Item not found")
    return _to_response(row[0], row[1], row[2])


@router.patch("/{item_id}", response_model=InventoryResponse)
async def update_item(item_id: int, body: InventoryUpdate, db: AsyncSession = Depends(get_db)):
    item = (await db.execute(select(InventoryItem).where(InventoryItem.id == item_id))).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await log_action(db, "inventory_item", item_id, "update", body.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(item)
    card = (await db.execute(select(Card.name_en).where(Card.id == item.card_id))).scalar()
    return _to_response(item, card)


@router.delete("/{item_id}", status_code=204)
async def delete_item(item_id: int, db: AsyncSession = Depends(get_db)):
    item = (await db.execute(select(InventoryItem).where(InventoryItem.id == item_id))).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item not found")
    await log_action(db, "inventory_item", item_id, "delete", {"card_id": item.card_id})
    await db.delete(item)
