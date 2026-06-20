import asyncio
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, buylist, cards, dashboard, inventory, orders, prices, products, sales, scan, shop, system, tournaments
from app.workers.price_sync import price_sync_loop

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(price_sync_loop())
    yield
    task.cancel()


app = FastAPI(title="TCG Store API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(dashboard.router)
app.include_router(auth.router)
app.include_router(inventory.router)
app.include_router(cards.router)
app.include_router(products.router)
app.include_router(prices.router)
app.include_router(sales.router)
app.include_router(orders.router)
app.include_router(buylist.router)
app.include_router(scan.router)
app.include_router(shop.router)
app.include_router(tournaments.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
