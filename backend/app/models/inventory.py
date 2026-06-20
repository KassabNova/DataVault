from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[str] = mapped_column(ForeignKey("card.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    condition: Mapped[str] = mapped_column(String, nullable=False, default="NM")
    language: Mapped[str] = mapped_column(String, nullable=False, default="en")
    is_foil: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    purchase_price: Mapped[float | None] = mapped_column(Float)
    listed_price: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(String)
    available_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    online_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("card_id", "condition", "language", "is_foil"),)
