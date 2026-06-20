from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.card import Card
from app.services.search import ensure_fts_table, rebuild_fts_index, search_fts

router = APIRouter(prefix="/api/v1/cards", tags=["cards"])


@router.get("/search")
async def search_cards(
    q: str = Query(min_length=2),
    game: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page

    # Handle set:number syntax (e.g., "mh3:42")
    if ':' in q and not q.startswith('mtg:'):
        parts = q.split(':')
        if len(parts) == 2:
            set_code, num = parts[0].strip(), parts[1].strip()
            results = (await db.execute(
                select(Card).where(Card.set_id.ilike(f"%:{set_code}"), Card.collector_number == num).limit(per_page)
            )).scalars().all()
            if results:
                return [_card_to_dict(c) for c in results]

    # Try FTS5 first
    try:
        fts_results = await search_fts(db, q, game=game, limit=per_page, offset=offset)
        if fts_results:
            card_ids = [r["card_id"] for r in fts_results]
            cards = (await db.execute(select(Card).where(Card.id.in_(card_ids)))).scalars().all()
            cards_map = {c.id: c for c in cards}
            # Preserve FTS ranking order
            return [
                _card_to_dict(cards_map[r["card_id"]])
                for r in fts_results if r["card_id"] in cards_map
            ]
    except Exception:
        pass  # FTS table may not exist yet, fall back to ILIKE

    # Fallback: ILIKE search
    query = select(Card).where(Card.name_en.ilike(f"%{q}%"))
    if game:
        query = query.where(Card.game_id == game)
    results = (await db.execute(query.order_by(Card.name_en).offset(offset).limit(per_page))).scalars().all()
    return [_card_to_dict(c) for c in results]


@router.post("/search/rebuild-index")
async def rebuild_index(db: AsyncSession = Depends(get_db)):
    """Rebuild the FTS5 search index from all card names."""
    await ensure_fts_table(db)
    count = await rebuild_fts_index(db)
    return {"status": "rebuilt", "entries": count}


@router.post("/import")
async def import_csv(file: UploadFile = File(...)):
    """Import cards from CSV for games without an API (e.g., Riftbound)."""
    from app.adapters.riftbound import Adapter
    content = (await file.read()).decode("utf-8")
    adapter = Adapter()
    count = await adapter.import_csv(content)
    return {"imported": count}


def _card_to_dict(c: Card) -> dict:
    return {
        "id": c.id,
        "name": c.name_en,
        "game_id": c.game_id,
        "set_id": c.set_id,
        "rarity": c.rarity,
        "collector_number": c.collector_number,
        "image_url": c.image_url_small,
        "card_type": c.card_type,
    }
