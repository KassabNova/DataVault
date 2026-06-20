from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.product import Product

router = APIRouter(prefix="/api/v1/products", tags=["products"])


class ProductCreate(BaseModel):
    name: str
    game_id: str | None = None
    product_type: str = "box"
    sku: str | None = None
    barcode: str | None = None
    msrp: float | None = None
    listed_price: float | None = None
    quantity: int = 0
    available_online: bool = False
    online_quantity: int = 0
    image_url: str | None = None
    description: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    listed_price: float | None = None
    quantity: int | None = None
    available_online: bool | None = None
    online_quantity: int | None = None
    image_url: str | None = None
    description: str | None = None


@router.post("", status_code=201)
async def create_product(body: ProductCreate, db: AsyncSession = Depends(get_db)):
    product = Product(**body.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return _to_dict(product)


@router.get("")
async def list_products(
    game: str | None = None,
    product_type: str | None = None,
    online_only: bool = False,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product)
    if game:
        query = query.where(Product.game_id == game)
    if product_type:
        query = query.where(Product.product_type == product_type)
    if online_only:
        query = query.where(Product.available_online == True, Product.online_quantity > 0)
    total = (await db.execute(select(func.count(Product.id)))).scalar() or 0
    rows = (await db.execute(query.offset((page - 1) * per_page).limit(per_page))).scalars().all()
    return {"items": [_to_dict(p) for p in rows], "total": total, "page": page}


@router.get("/lookup")
async def lookup_by_barcode(barcode: str | None = None, sku: str | None = None, db: AsyncSession = Depends(get_db)):
    """Lookup product by barcode or SKU (for hardware scanner input)."""
    if not barcode and not sku:
        raise HTTPException(400, "Provide barcode or sku parameter")
    if barcode:
        product = (await db.execute(select(Product).where(Product.barcode == barcode))).scalar_one_or_none()
    else:
        product = (await db.execute(select(Product).where(Product.sku == sku))).scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")
    return _to_dict(product)


@router.get("/{product_id}")
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    product = (await db.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")
    return _to_dict(product)


@router.patch("/{product_id}")
async def update_product(product_id: int, body: ProductUpdate, db: AsyncSession = Depends(get_db)):
    product = (await db.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return _to_dict(product)


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    product = (await db.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")
    await db.delete(product)
    await db.commit()


def _to_dict(p: Product) -> dict:
    return {
        "id": p.id, "name": p.name, "game_id": p.game_id, "product_type": p.product_type,
        "sku": p.sku, "barcode": p.barcode, "msrp": p.msrp, "listed_price": p.listed_price,
        "quantity": p.quantity, "available_online": p.available_online,
        "online_quantity": p.online_quantity, "image_url": p.image_url, "description": p.description,
    }
