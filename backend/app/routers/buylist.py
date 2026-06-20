from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.card import Card
from app.models.inventory import InventoryItem
from app.models.scan import TradeIn, TradeInItem
from app.services.pricing import calculate_store_prices

router = APIRouter(prefix="/api/v1", tags=["buylist"])


@router.get("/buylist/quote/{card_id}")
async def get_buy_quote(card_id: str, condition: str = "NM", db: AsyncSession = Depends(get_db)):
    """Get the store's buy price offer for a card."""
    card = (await db.execute(select(Card).where(Card.id == card_id))).scalar_one_or_none()
    if not card:
        raise HTTPException(404, "Card not found")

    prices = await calculate_store_prices(db, card_id, card.game_id, card.rarity)

    # Apply condition modifier to buy price
    condition_mults = {"NM": 1.0, "LP": 0.85, "MP": 0.70, "HP": 0.50, "DMG": 0.25}
    mult = condition_mults.get(condition, 1.0)
    buy_price = round(prices["buy_price"] * mult, 2) if prices["buy_price"] else None

    return {
        "card_id": card_id,
        "card_name": card.name_en,
        "condition": condition,
        "buy_price": buy_price,
        "currency": "MXN",
        "image_url": card.image_url_small,
    }


class TradeInItemCreate(BaseModel):
    card_id: str
    quantity: int = Field(ge=1, default=1)
    condition: str = "NM"
    language: str = "en"
    is_foil: bool = False
    offered_price: float


class TradeInCreate(BaseModel):
    items: list[TradeInItemCreate] = Field(min_length=1)
    payment_method: str = "cash"
    notes: str | None = None


@router.post("/trade-ins", status_code=201)
async def create_trade_in(body: TradeInCreate, db: AsyncSession = Depends(get_db)):
    """Record a trade-in: pays customer, adds cards to inventory."""
    total_payout = sum(i.offered_price * i.quantity for i in body.items)

    trade_in = TradeIn(total_payout=total_payout, payment_method=body.payment_method, notes=body.notes)
    db.add(trade_in)
    await db.flush()

    for item in body.items:
        # Verify card exists
        card = (await db.execute(select(Card).where(Card.id == item.card_id))).scalar_one_or_none()
        if not card:
            raise HTTPException(404, f"Card not found: {item.card_id}")

        db.add(TradeInItem(
            trade_in_id=trade_in.id, card_id=item.card_id, quantity=item.quantity,
            condition=item.condition, language=item.language, is_foil=item.is_foil,
            offered_price=item.offered_price,
        ))

        # Add to inventory (upsert)
        existing = (await db.execute(
            select(InventoryItem).where(
                InventoryItem.card_id == item.card_id,
                InventoryItem.condition == item.condition,
                InventoryItem.language == item.language,
                InventoryItem.is_foil == item.is_foil,
            )
        )).scalar_one_or_none()

        if existing:
            existing.quantity += item.quantity
        else:
            db.add(InventoryItem(
                card_id=item.card_id, quantity=item.quantity, condition=item.condition,
                language=item.language, is_foil=item.is_foil, purchase_price=item.offered_price,
            ))

    await db.commit()
    return {"id": trade_in.id, "total_payout": total_payout, "items_count": len(body.items)}


@router.get("/trade-ins")
async def list_trade_ins(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TradeIn).order_by(TradeIn.created_at.desc()).limit(50))
    return [
        {"id": t.id, "total_payout": t.total_payout, "payment_method": t.payment_method,
         "created_at": t.created_at.isoformat() if t.created_at else None}
        for t in result.scalars().all()
    ]
