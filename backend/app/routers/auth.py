from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.customer import Customer
from app.services.auth import create_token, hash_password, require_customer, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RegisterBody(BaseModel):
    email: str
    password: str
    name: str
    phone: str | None = None


class LoginBody(BaseModel):
    email: str
    password: str


@router.post("/register", status_code=201)
async def register(body: RegisterBody, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(Customer).where(Customer.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Email already registered")

    customer = Customer(
        email=body.email,
        hashed_password=hash_password(body.password),
        name=body.name,
        phone=body.phone,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    token = create_token(customer.id, customer.email)
    return {"token": token, "customer": {"id": customer.id, "email": customer.email, "name": customer.name}}


@router.post("/login")
async def login(body: LoginBody, db: AsyncSession = Depends(get_db)):
    customer = (await db.execute(select(Customer).where(Customer.email == body.email))).scalar_one_or_none()
    if not customer or not verify_password(body.password, customer.hashed_password):
        raise HTTPException(401, "Invalid email or password")

    token = create_token(customer.id, customer.email)
    return {"token": token, "customer": {"id": customer.id, "email": customer.email, "name": customer.name}}


@router.get("/me")
async def get_me(customer: Customer = Depends(require_customer)):
    return {"id": customer.id, "email": customer.email, "name": customer.name, "phone": customer.phone}
