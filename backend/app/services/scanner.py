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
HASH_SIZE_16 = 16  # 16x16 = 256-bit hash


def _dct_matrix(n: int) -> list[list[float]]:
    """Precompute DCT-II matrix."""
    mat = []
    for k in range(n):
        row = []
        for i in range(n):
            row.append(math.cos(math.pi * k * (2 * i + 1) / (2 * n)))
        mat.append(row)
    return mat

_DCT16 = _dct_matrix(32)  # We resize to 32x32, then take top-left 16x16 of DCT


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


def compute_phash16(image_bytes: bytes) -> bytes:
    """Compute a 256-bit DCT-based perceptual hash (much more robust to lighting). Returns 32 bytes."""
    # Resize to 32x32 for DCT, then use low-frequency 16x16 block
    img = Image.open(BytesIO(image_bytes)).convert("L").resize((32, 32), Image.Resampling.LANCZOS)
    pixels = list(img.getdata())

    # Apply 2D DCT: rows then columns
    rows = []
    for y in range(32):
        row_pixels = pixels[y * 32:(y + 1) * 32]
        dct_row = []
        for k in range(32):
            val = sum(row_pixels[i] * _DCT16[k][i] for i in range(32))
            dct_row.append(val)
        rows.append(dct_row)

    # DCT on columns, keep top-left 16x16
    dct_values = []
    for x in range(16):
        for k in range(16):
            val = sum(rows[i][x] * _DCT16[k][i] for i in range(32))
            dct_values.append(val)

    # Exclude DC component (first value), compute median of rest
    dct_values_no_dc = dct_values[1:]
    median = sorted(dct_values_no_dc)[len(dct_values_no_dc) // 2]

    # Generate hash: 1 if above median, 0 if below (256 bits = 32 bytes)
    bits = bytearray(32)
    for i, val in enumerate(dct_values[:256]):
        if val > median:
            bits[i // 8] |= 1 << (7 - (i % 8))
    return bytes(bits)


def hamming_distance(h1: int, h2: int) -> int:
    """Count differing bits between two 64-bit hashes."""
    return bin((h1 ^ h2) & 0xFFFFFFFFFFFFFFFF).count("1")


def hamming_distance_bytes(h1: bytes, h2: bytes) -> int:
    """Count differing bits between two byte-string hashes."""
    return sum(bin(a ^ b).count("1") for a, b in zip(h1, h2))


async def find_matches(image_bytes: bytes, threshold: int = 18, top_n: int = 5, game_id: str | None = None) -> list[dict]:
    """Match an image against the card_hash index. Returns top_n closest matches."""
    query_hash = compute_phash(image_bytes)
    query_hash16 = compute_phash16(image_bytes)

    async with async_session() as session:
        if game_id:
            rows = (await session.execute(text(
                "SELECT ch.card_id, ch.phash, ch.phash16 FROM card_hash ch JOIN card c ON c.id = ch.card_id WHERE c.game_id = :game_id"
            ), {"game_id": game_id})).fetchall()
        else:
            rows = (await session.execute(text("SELECT card_id, phash, phash16 FROM card_hash"))).fetchall()

    if not rows:
        return []

    # Use 16x16 hash if available, fall back to 8x8
    scored = []
    for row in rows:
        card_id, phash_val, phash16_val = row[0], row[1], row[2]
        if phash16_val:
            dist = hamming_distance_bytes(query_hash16, phash16_val)
            # Scale threshold: 256 bits vs 64 bits → multiply threshold by 4
            if dist <= threshold * 4:
                scored.append((dist / 4.0, card_id))  # normalize to 64-bit scale for confidence
        else:
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
                    phash16 = compute_phash16(resp.content)
                    hashes.append({"card_id": card_id, "phash": phash, "phash16": phash16})
            except Exception:
                continue

    if hashes:
        async with async_session() as session:
            conn = await session.connection()
            await conn.execute(
                text("INSERT OR IGNORE INTO card_hash (card_id, phash, phash16) VALUES (:card_id, :phash, :phash16)"),
                hashes,
            )
            await session.commit()

    logger.info("Built %d hashes (batch of %d)", len(hashes), batch_size)
    return len(hashes)
