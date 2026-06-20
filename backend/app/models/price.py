from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PriceRecord(Base):
    __tablename__ = "price_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[str] = mapped_column(ForeignKey("card.id"), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    price_low: Mapped[float | None] = mapped_column(Float)
    price_mid: Mapped[float | None] = mapped_column(Float)
    price_high: Mapped[float | None] = mapped_column(Float)
    price_market: Mapped[float | None] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PricingRule(Base):
    __tablename__ = "pricing_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str | None] = mapped_column(ForeignKey("game.id"))
    rarity: Mapped[str | None] = mapped_column(String)
    card_id: Mapped[str | None] = mapped_column(ForeignKey("card.id"))
    sell_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    buy_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=0.6)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
