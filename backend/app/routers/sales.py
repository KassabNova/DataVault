from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.inventory import InventoryItem
from app.models.sale import Sale, SaleItem

router = APIRouter(prefix="/api/v1/sales", tags=["sales"])


class SaleItemCreate(BaseModel):
    inventory_item_id: int
    quantity: int = Field(ge=1, default=1)
    unit_price: float


class SaleCreate(BaseModel):
    items: list[SaleItemCreate] = Field(min_length=1)
    discount: float = 0
    payment_method: str = "cash"
    notes: str | None = None


@router.post("", status_code=201)
async def create_sale(body: SaleCreate, db: AsyncSession = Depends(get_db)):
    # Validate stock and calculate subtotal
    subtotal = 0.0
    inventory_updates = []

    for item in body.items:
        inv = (await db.execute(select(InventoryItem).where(InventoryItem.id == item.inventory_item_id))).scalar_one_or_none()
        if not inv:
            raise HTTPException(404, f"Inventory item {item.inventory_item_id} not found")
        if inv.quantity < item.quantity:
            raise HTTPException(400, f"Insufficient stock for item {item.inventory_item_id} (have {inv.quantity}, need {item.quantity})")
        subtotal += item.unit_price * item.quantity
        inventory_updates.append((inv, item.quantity))

    total = subtotal - body.discount

    # Create sale
    sale = Sale(
        subtotal=subtotal,
        discount=body.discount,
        tax=0,
        total=total,
        payment_method=body.payment_method,
        notes=body.notes,
    )
    db.add(sale)
    await db.flush()

    # Create sale items and decrement inventory
    for (inv, qty), item_data in zip(inventory_updates, body.items):
        db.add(SaleItem(
            sale_id=sale.id,
            inventory_item_id=item_data.inventory_item_id,
            quantity=qty,
            unit_price=item_data.unit_price,
            condition=inv.condition,
        ))
        inv.quantity -= qty

    await db.commit()
    await db.refresh(sale)

    return {"id": sale.id, "total": sale.total, "payment_method": sale.payment_method, "created_at": sale.created_at.isoformat() if sale.created_at else None}


@router.get("")
async def list_sales(
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Sale).order_by(Sale.created_at.desc())
    if date_from:
        query = query.where(Sale.created_at >= date_from)
    if date_to:
        query = query.where(Sale.created_at <= date_to + " 23:59:59")

    rows = (await db.execute(query.offset((page - 1) * per_page).limit(per_page))).scalars().all()
    total = (await db.execute(select(func.count(Sale.id)))).scalar() or 0

    return {
        "items": [
            {"id": s.id, "total": s.total, "payment_method": s.payment_method,
             "discount": s.discount, "created_at": s.created_at.isoformat() if s.created_at else None}
            for s in rows
        ],
        "total": total, "page": page, "per_page": per_page,
    }


@router.get("/reports/daily")
async def daily_report(day: str | None = None, db: AsyncSession = Depends(get_db)):
    target = day or date.today().isoformat()
    start = f"{target} 00:00:00"
    end = f"{target} 23:59:59"

    sales = (await db.execute(
        select(Sale).where(Sale.created_at >= start, Sale.created_at <= end)
    )).scalars().all()

    total_revenue = sum(s.total for s in sales)
    total_sales = len(sales)
    by_method = {}
    for s in sales:
        by_method[s.payment_method] = by_method.get(s.payment_method, 0) + s.total

    return {
        "date": target,
        "total_sales": total_sales,
        "total_revenue": round(total_revenue, 2),
        "by_payment_method": by_method,
    }


@router.get("/{sale_id}")
async def get_sale(sale_id: int, db: AsyncSession = Depends(get_db)):
    sale = (await db.execute(select(Sale).where(Sale.id == sale_id))).scalar_one_or_none()
    if not sale:
        raise HTTPException(404, "Sale not found")

    items = (await db.execute(select(SaleItem).where(SaleItem.sale_id == sale_id))).scalars().all()

    return {
        "id": sale.id,
        "subtotal": sale.subtotal,
        "discount": sale.discount,
        "total": sale.total,
        "payment_method": sale.payment_method,
        "notes": sale.notes,
        "created_at": sale.created_at.isoformat() if sale.created_at else None,
        "items": [
            {"inventory_item_id": i.inventory_item_id, "quantity": i.quantity,
             "unit_price": i.unit_price, "condition": i.condition}
            for i in items
        ],
    }


@router.post("/{sale_id}/void")
async def void_sale(sale_id: int, db: AsyncSession = Depends(get_db)):
    """Void/undo a sale: restores inventory quantities."""
    sale = (await db.execute(select(Sale).where(Sale.id == sale_id))).scalar_one_or_none()
    if not sale:
        raise HTTPException(404, "Sale not found")
    if sale.notes and sale.notes.startswith("[VOIDED]"):
        raise HTTPException(400, "Sale already voided")

    items = (await db.execute(select(SaleItem).where(SaleItem.sale_id == sale_id))).scalars().all()
    for item in items:
        inv = (await db.execute(select(InventoryItem).where(InventoryItem.id == item.inventory_item_id))).scalar_one_or_none()
        if inv:
            inv.quantity += item.quantity

    sale.notes = f"[VOIDED] {sale.notes or ''}"
    await db.commit()
    return {"id": sale.id, "status": "voided", "items_restored": len(items)}
