"""Background price sync worker."""
import asyncio
import logging
from datetime import datetime

from app.adapters.registry import get_adapter, list_adapters
from app.config import settings

logger = logging.getLogger(__name__)

_sync_status: dict = {"last_sync": None, "in_progress": False, "results": {}}


def get_sync_status() -> dict:
    return _sync_status


async def run_price_sync():
    """Run price sync for all enabled games."""
    if _sync_status["in_progress"]:
        logger.warning("Price sync already in progress, skipping")
        return

    _sync_status["in_progress"] = True
    _sync_status["results"] = {}

    for game_id in list_adapters():
        try:
            adapter = get_adapter(game_id)
            count = await adapter.sync_prices()
            _sync_status["results"][game_id] = {"count": count, "error": None}
            logger.info("Price sync %s: %d records", game_id, count)
        except Exception as e:
            _sync_status["results"][game_id] = {"count": 0, "error": str(e)}
            logger.error("Price sync %s failed: %s", game_id, e)

    _sync_status["last_sync"] = datetime.utcnow().isoformat()
    _sync_status["in_progress"] = False


async def price_sync_loop():
    """Background loop that runs price sync on schedule."""
    interval = settings.sync_schedule_hours * 3600
    while True:
        await asyncio.sleep(interval)
        await run_price_sync()
