from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Order(Base):
    __tablename__ = "order"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")  # pending, confirmed, ready, picked_up, cancelled
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    total: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_date: Mapped[str] = mapped_column(String, nullable=False)  # ISO date, min tomorrow
    pickup_time: Mapped[str | None] = mapped_column(String)  # optional preferred time
    notes: Mapped[str | None] = mapped_column(String)
    payment_method: Mapped[str | None] = mapped_column(String)  # for future: mercadopago, stripe
    payment_status: Mapped[str] = mapped_column(String, default="pending")  # pending, paid, refunded
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("order.id"), nullable=False)
    # Either a card inventory item or a product
    inventory_item_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_item.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product.id"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    item_name: Mapped[str] = mapped_column(String, nullable=False)  # denormalized for display

    order: Mapped["Order"] = relationship(back_populates="items")
