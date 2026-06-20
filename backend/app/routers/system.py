import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.registry import get_adapter, list_adapters
from app.database import get_db
from app.models.game import Game

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


@router.get("/games")
async def list_games(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Game))
    games = result.scalars().all()
    return [{"id": g.id, "name": g.name, "enabled": g.enabled} for g in games]


@router.post("/sync/cards")
async def sync_cards(game_id: str, background_tasks: BackgroundTasks):
    if game_id not in list_adapters():
        raise HTTPException(404, f"No adapter for game: {game_id}")
    background_tasks.add_task(_run_sync, game_id)
    return {"status": "started", "game_id": game_id}


async def _run_sync(game_id: str):
    logger.info("Starting card sync for %s", game_id)
    adapter = get_adapter(game_id)
    count = await adapter.sync_cards()
    logger.info("Sync complete for %s: %d cards", game_id, count)
