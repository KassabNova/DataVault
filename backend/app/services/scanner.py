"""Perceptual hash computation and matching using Pillow only (DCT-based average hash)."""
import logging
import math
from io import BytesIO

from PIL import Image
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session

logger = logging.getLogger(__name__)

HASH_SIZE = 8  # 8x8 = 64-bit hash


def compute_phash(image_bytes: bytes) -> int:
    """Compute a 64-bit perceptual hash (average hash) from image bytes. Returns signed int for SQLite."""
    img = Image.open(BytesIO(image_bytes)).convert("L").resize((HASH_SIZE, HASH_SIZE), Image.Resampling.LANCZOS)
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = 0
    for i, px in enumerate(pixels):
        if px > avg:
            bits |= 1 << (63 - i)
    # Convert to signed 64-bit for SQLite compatibility
    if bits >= (1 << 63):
        bits -= (1 << 64)
    return bits


def hamming_distance(h1: int, h2: int) -> int:
    """Count differing bits between two hashes."""
    return bin((h1 ^ h2) & 0xFFFFFFFFFFFFFFFF).count("1")


async def find_matches(image_bytes: bytes, threshold: int = 10, top_n: int = 5) -> list[dict]:
    """Match an image against the card_hash index. Returns top_n closest matches."""
    query_hash = compute_phash(image_bytes)

    async with async_session() as session:
        # Load all hashes (for ~100K cards this is fast - 64-bit ints are tiny)
        rows = (await session.execute(text("SELECT card_id, phash FROM card_hash"))).fetchall()

    if not rows:
        return []

    # Find nearest matches by Hamming distance
    scored = []
    for card_id, phash_val in rows:
        dist = hamming_distance(query_hash, phash_val)
        if dist <= threshold:
            scored.append((dist, card_id))

    scored.sort(key=lambda x: x[0])
    top = scored[:top_n]

    # Fetch card details
    if not top:
        return []

    card_ids = [card_id for _, card_id in top]
    from app.models.card import Card
    async with async_session() as session:
        cards = (await session.execute(select(Card).where(Card.id.in_(card_ids)))).scalars().all()
        cards_map = {c.id: c for c in cards}

    results = []
    for dist, card_id in top:
        card = cards_map.get(card_id)
        if card:
            confidence = max(0, 1.0 - (dist / 64.0))
            results.append({
                "card_id": card_id,
                "confidence": round(confidence, 3),
                "name": card.name_en,
                "image_url": card.image_url_small,
                "set_id": card.set_id,
                "distance": dist,
            })

    return results


async def build_hash_index(game_id: str | None = None, batch_size: int = 100) -> int:
    """Download card images and compute pHash for indexing. Returns count of hashes built."""
    import httpx
    from app.models.card import Card

    async with async_session() as session:
        query = select(Card.id, Card.image_url_small).where(Card.image_url_small.isnot(None))
        if game_id:
            query = query.where(Card.game_id == game_id)

        # Only hash cards we haven't hashed yet
        query = query.where(~Card.id.in_(select(text("card_id")).select_from(text("card_hash"))))
        query = query.limit(batch_size)
        rows = (await session.execute(query)).all()

    if not rows:
        return 0

    hashes = []
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for card_id, image_url in rows:
            try:
                resp = await client.get(image_url)
                if resp.status_code == 200:
                    phash = compute_phash(resp.content)
                    hashes.append({"card_id": card_id, "phash": phash})
            except Exception:
                continue

    if hashes:
        async with async_session() as session:
            conn = await session.connection()
            from app.models.card import Card  # reuse connection
            await conn.execute(
                text("INSERT OR IGNORE INTO card_hash (card_id, phash) VALUES (:card_id, :phash)"),
                hashes,
            )
            await session.commit()

    logger.info("Built %d hashes (batch of %d)", len(hashes), batch_size)
    return len(hashes)
