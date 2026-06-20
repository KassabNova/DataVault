from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.customer import Customer
from app.models.inventory import InventoryItem
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.services.auth import require_customer

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


class OrderItemCreate(BaseModel):
    inventory_item_id: int | None = None
    product_id: int | None = None
    quantity: int = Field(ge=1, default=1)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(min_length=1)
    pickup_date: str  # ISO date string, must be at least tomorrow
    pickup_time: str | None = None
    notes: str | None = None


@router.post("", status_code=201)
async def create_order(
    body: OrderCreate,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    # Validate pickup date (at least 1 day ahead)
    min_date = (date.today() + timedelta(days=1)).isoformat()
    if body.pickup_date < min_date:
        raise HTTPException(400, f"Pickup date must be {min_date} or later")

    # Validate items and calculate total
    subtotal = 0.0
    order_items = []

    for item in body.items:
        if item.inventory_item_id:
            inv = (await db.execute(select(InventoryItem).where(InventoryItem.id == item.inventory_item_id))).scalar_one_or_none()
            if not inv:
                raise HTTPException(404, f"Inventory item {item.inventory_item_id} not found")
            if inv.online_quantity < item.quantity:
                raise HTTPException(400, f"Insufficient online stock for item {item.inventory_item_id}")
            price = inv.listed_price or 0
            order_items.append({"inv": inv, "product": None, "qty": item.quantity, "price": price, "name": inv.card_id})
            subtotal += price * item.quantity
        elif item.product_id:
            prod = (await db.execute(select(Product).where(Product.id == item.product_id))).scalar_one_or_none()
            if not prod:
                raise HTTPException(404, f"Product {item.product_id} not found")
            if prod.online_quantity < item.quantity:
                raise HTTPException(400, f"Insufficient online stock for product {item.product_id}")
            price = prod.listed_price or 0
            order_items.append({"inv": None, "product": prod, "qty": item.quantity, "price": price, "name": prod.name})
            subtotal += price * item.quantity
        else:
            raise HTTPException(400, "Each item must have inventory_item_id or product_id")

    # Create order
    order = Order(
        customer_id=customer.id, subtotal=subtotal, total=subtotal,
        pickup_date=body.pickup_date, pickup_time=body.pickup_time, notes=body.notes,
    )
    db.add(order)
    await db.flush()

    # Create items and decrement online stock
    for oi in order_items:
        db.add(OrderItem(
            order_id=order.id,
            inventory_item_id=oi["inv"].id if oi["inv"] else None,
            product_id=oi["product"].id if oi["product"] else None,
            quantity=oi["qty"], unit_price=oi["price"], item_name=oi["name"],
        ))
        if oi["inv"]:
            oi["inv"].online_quantity -= oi["qty"]
        if oi["product"]:
            oi["product"].online_quantity -= oi["qty"]

    await db.commit()
    await db.refresh(order)
    return _order_dict(order, order_items=[])


@router.get("")
async def list_orders(
    customer_id: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List orders. Store staff can filter by customer_id or status."""
    query = select(Order).order_by(Order.created_at.desc())
    if customer_id:
        query = query.where(Order.customer_id == customer_id)
    if status:
        query = query.where(Order.status == status)
    rows = (await db.execute(query.offset((page - 1) * per_page).limit(per_page))).scalars().all()
    total = (await db.execute(select(func.count(Order.id)))).scalar() or 0
    return {"items": [_order_dict(o) for o in rows], "total": total, "page": page}


@router.get("/my")
async def my_orders(
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Get current customer's orders."""
    rows = (await db.execute(
        select(Order).where(Order.customer_id == customer.id).order_by(Order.created_at.desc())
    )).scalars().all()
    return [_order_dict(o) for o in rows]


@router.get("/{order_id}")
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")
    items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order_id))).scalars().all()
    return _order_dict(order, items)


@router.patch("/{order_id}/status")
async def update_order_status(order_id: int, status: str, db: AsyncSession = Depends(get_db)):
    """Update order status (store staff). Valid: pending, confirmed, ready, picked_up, cancelled."""
    valid = {"pending", "confirmed", "ready", "picked_up", "cancelled"}
    if status not in valid:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid}")
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")
    order.status = status
    await db.commit()
    return {"id": order.id, "status": order.status}


def _order_dict(order: Order, order_items: list | None = None) -> dict:
    d = {
        "id": order.id, "customer_id": order.customer_id, "status": order.status,
        "subtotal": order.subtotal, "total": order.total,
        "pickup_date": order.pickup_date, "pickup_time": order.pickup_time,
        "notes": order.notes, "payment_status": order.payment_status,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }
    if order_items is not None:
        d["items"] = [
            {"id": i.id, "item_name": i.item_name, "quantity": i.quantity, "unit_price": i.unit_price,
             "inventory_item_id": i.inventory_item_id, "product_id": i.product_id}
            for i in order_items
        ]
    return d
