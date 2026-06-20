import time

from fastapi import APIRouter, BackgroundTasks, File, Query, UploadFile

from app.services.scanner import build_hash_index, find_matches

router = APIRouter(prefix="/api/v1/scan", tags=["scan"])


@router.post("/match")
async def match_card(image: UploadFile = File(...), threshold: int = Query(12, ge=1, le=32)):
    """Upload an image and get top card matches by perceptual hash."""
    start = time.time()
    image_bytes = await image.read()
    matches = await find_matches(image_bytes, threshold=threshold)
    elapsed = round((time.time() - start) * 1000)

    return {
        "matches": matches,
        "method": "phash",
        "processing_ms": elapsed,
    }


@router.post("/build-index")
async def trigger_build_index(
    game_id: str | None = None,
    batch_size: int = Query(200, ge=1, le=1000),
    background_tasks: BackgroundTasks = None,
):
    """Build pHash index by downloading card images. Run multiple times to index more cards."""
    count = await build_hash_index(game_id=game_id, batch_size=batch_size)
    return {"indexed": count, "message": f"Indexed {count} cards. Run again to index more."}
