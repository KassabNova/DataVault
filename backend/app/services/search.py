"""Full-text search using SQLite FTS5."""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

CREATE_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS card_search USING fts5(
    card_id,
    name,
    game_id,
    tokenize='unicode61'
);
"""


async def ensure_fts_table(db: AsyncSession):
    """Create FTS5 table if it doesn't exist."""
    await db.execute(text(CREATE_FTS))
    await db.commit()


async def rebuild_fts_index(db: AsyncSession):
    """Rebuild FTS index from card_name table."""
    await db.execute(text("DELETE FROM card_search;"))
    await db.execute(text("""
        INSERT INTO card_search (card_id, name, game_id)
        SELECT cn.card_id, cn.name, c.game_id
        FROM card_name cn
        JOIN card c ON c.id = cn.card_id;
    """))
    await db.commit()
    count = (await db.execute(text("SELECT COUNT(*) FROM card_search"))).scalar()
    logger.info("FTS index rebuilt: %d entries", count)
    return count


async def search_fts(db: AsyncSession, query: str, game: str | None = None, limit: int = 20, offset: int = 0):
    """Search cards using FTS5. Returns card_ids ranked by relevance."""
    # FTS5 query: prefix match with *
    fts_query = " ".join(f"{term}*" for term in query.strip().split())

    if game:
        sql = text("""
            SELECT cs.card_id, cs.name, cs.game_id, rank
            FROM card_search cs
            WHERE card_search MATCH :q AND cs.game_id = :game
            ORDER BY rank
            LIMIT :limit OFFSET :offset
        """)
        result = await db.execute(sql, {"q": fts_query, "game": game, "limit": limit, "offset": offset})
    else:
        sql = text("""
            SELECT cs.card_id, cs.name, cs.game_id, rank
            FROM card_search cs
            WHERE card_search MATCH :q
            ORDER BY rank
            LIMIT :limit OFFSET :offset
        """)
        result = await db.execute(sql, {"q": fts_query, "limit": limit, "offset": offset})

    return [{"card_id": row[0], "name": row[1], "game_id": row[2]} for row in result.fetchall()]
