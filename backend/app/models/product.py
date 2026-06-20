from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Product(Base):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    game_id: Mapped[str | None] = mapped_column(ForeignKey("game.id"))
    product_type: Mapped[str] = mapped_column(String, nullable=False)  # box, bundle, pack, accessory
    sku: Mapped[str | None] = mapped_column(String, unique=True)
    barcode: Mapped[str | None] = mapped_column(String)
    msrp: Mapped[float | None] = mapped_column(Float)
    listed_price: Mapped[float | None] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    available_online: Mapped[bool] = mapped_column(Boolean, default=False)
    online_quantity: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
