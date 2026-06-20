from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScanSession(Base):
    __tablename__ = "scan_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    cards_scanned: Mapped[int] = mapped_column(Integer, default=0)
    cards_added: Mapped[int] = mapped_column(Integer, default=0)


class TradeIn(Base):
    __tablename__ = "trade_in"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    total_payout: Mapped[float] = mapped_column(Float, nullable=False)
    payment_method: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["TradeInItem"]] = relationship(back_populates="trade_in")


class TradeInItem(Base):
    __tablename__ = "trade_in_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_in_id: Mapped[int] = mapped_column(ForeignKey("trade_in.id"), nullable=False)
    card_id: Mapped[str] = mapped_column(ForeignKey("card.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    condition: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str] = mapped_column(String, nullable=False, default="en")
    is_foil: Mapped[bool] = mapped_column(Integer, nullable=False, default=False)
    offered_price: Mapped[float] = mapped_column(Float, nullable=False)

    trade_in: Mapped["TradeIn"] = relationship(back_populates="items")
