"""Pricing rules engine - calculates store sell/buy prices from market data."""
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.price import PriceRecord, PricingRule


async def get_latest_price(db: AsyncSession, card_id: str, currency: str = "USD") -> PriceRecord | None:
    """Get most recent price record for a card."""
    result = await db.execute(
        select(PriceRecord)
        .where(PriceRecord.card_id == card_id, PriceRecord.currency == currency)
        .order_by(desc(PriceRecord.fetched_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_applicable_rule(db: AsyncSession, card_id: str, game_id: str, rarity: str | None) -> PricingRule | None:
    """Find the most specific pricing rule (highest priority) for a card."""
    result = await db.execute(
        select(PricingRule)
        .where(
            (PricingRule.card_id == card_id) |
            ((PricingRule.game_id == game_id) & (PricingRule.rarity == rarity) & (PricingRule.card_id.is_(None))) |
            ((PricingRule.game_id == game_id) & (PricingRule.rarity.is_(None)) & (PricingRule.card_id.is_(None))) |
            ((PricingRule.game_id.is_(None)) & (PricingRule.rarity.is_(None)) & (PricingRule.card_id.is_(None)))
        )
        .order_by(desc(PricingRule.priority))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def calculate_store_prices(db: AsyncSession, card_id: str, game_id: str, rarity: str | None) -> dict:
    """Calculate sell and buy prices based on market data + rules."""
    price = await get_latest_price(db, card_id)
    if not price or not price.price_market:
        return {"sell_price": None, "buy_price": None, "market_price": None, "currency": "MXN"}

    rule = await get_applicable_rule(db, card_id, game_id, rarity)
    sell_mult = rule.sell_multiplier if rule else settings.usd_to_mxn * 1.10
    buy_mult = rule.buy_multiplier if rule else settings.usd_to_mxn * 0.60

    market = price.price_market
    # Convert USD to MXN if needed
    if price.currency == "USD":
        market_mxn = market * settings.usd_to_mxn
    elif price.currency == "EUR":
        market_mxn = market * settings.usd_to_mxn * 1.08  # rough EUR->MXN
    else:
        market_mxn = market

    if rule:
        sell_price = round(market_mxn * rule.sell_multiplier, 2)
        buy_price = round(market_mxn * rule.buy_multiplier, 2)
    else:
        sell_price = round(market_mxn * 1.10, 2)
        buy_price = round(market_mxn * 0.60, 2)

    return {
        "market_price": round(market_mxn, 2),
        "sell_price": sell_price,
        "buy_price": buy_price,
        "currency": "MXN",
        "source": price.source,
        "source_currency": price.currency,
        "source_price": price.price_market,
    }
