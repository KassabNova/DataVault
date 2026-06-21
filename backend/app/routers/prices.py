from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.card import Card
from app.models.price import PriceRecord, PricingRule
from app.services.pricing import calculate_store_prices
from app.workers.price_sync import get_sync_status, run_price_sync

router = APIRouter(prefix="/api/v1", tags=["pricing"])


@router.get("/prices/sync-status")
async def sync_status():
    return get_sync_status()


@router.post("/prices/sync")
async def trigger_sync():
    """Manually trigger price sync."""
    import asyncio
    asyncio.create_task(run_price_sync())
    return {"status": "started"}


@router.get("/prices/lookup")
async def get_card_prices(card_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    card = (await db.execute(select(Card).where(Card.id == card_id))).scalar_one_or_none()
    if not card:
        raise HTTPException(404, "Card not found")

    store_prices = await calculate_store_prices(db, card_id, card.game_id, card.rarity)

    # Also get raw price records
    records = (await db.execute(
        select(PriceRecord)
        .where(PriceRecord.card_id == card_id)
        .order_by(desc(PriceRecord.fetched_at))
        .limit(10)
    )).scalars().all()

    return {
        "card_id": card_id,
        "card_name": card.name_en,
        "store": store_prices,
        "records": [
            {"source": r.source, "currency": r.currency, "market": r.price_market,
             "low": r.price_low, "high": r.price_high, "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None}
            for r in records
        ],
    }


@router.get("/prices/history")
async def get_price_history(card_id: str = Query(...), limit: int = 50, db: AsyncSession = Depends(get_db)):
    records = (await db.execute(
        select(PriceRecord)
        .where(PriceRecord.card_id == card_id)
        .order_by(desc(PriceRecord.fetched_at))
        .limit(limit)
    )).scalars().all()
    return [
        {"source": r.source, "currency": r.currency, "market": r.price_market,
         "low": r.price_low, "high": r.price_high, "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None}
        for r in records
    ]


# --- Pricing Rules ---

class RuleCreate(BaseModel):
    game_id: str | None = None
    rarity: str | None = None
    card_id: str | None = None
    sell_multiplier: float = 1.10
    buy_multiplier: float = 0.60
    priority: int = 0


@router.get("/pricing/rules")
async def list_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PricingRule).order_by(desc(PricingRule.priority)))
    rules = result.scalars().all()
    return [
        {"id": r.id, "game_id": r.game_id, "rarity": r.rarity, "card_id": r.card_id,
         "sell_multiplier": r.sell_multiplier, "buy_multiplier": r.buy_multiplier, "priority": r.priority}
        for r in rules
    ]


@router.post("/pricing/rules", status_code=201)
async def create_rule(body: RuleCreate, db: AsyncSession = Depends(get_db)):
    rule = PricingRule(**body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return {"id": rule.id, **body.model_dump()}


@router.delete("/pricing/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    rule = (await db.execute(select(PricingRule).where(PricingRule.id == rule_id))).scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")
    await db.delete(rule)
    await db.commit()
