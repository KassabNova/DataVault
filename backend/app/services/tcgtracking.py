"""TCGTracking.com universal price sync - covers all games except MTG (uses Scryfall)."""
import logging

import httpx
from sqlalchemy import text

from app.database import async_session

logger = logging.getLogger(__name__)

BASE_URL = "https://tcgtracking.com/tcgapi/v1"

# Map our game_ids to TCGTracking category IDs
GAME_CATEGORIES = {
    "pokemon": 3,
    "yugioh": 2,
    "lorcana": 71,
    "onepiece": 68,
    "swu": 79,
    "fab": 62,
    "riftbound": 89,
}


async def sync_prices_from_tcgtracking(game_id: str) -> int:
    """Fetch prices from TCGTracking for a game. Returns count of price records created."""
    cat_id = GAME_CATEGORIES.get(game_id)
    if not cat_id:
        return 0

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        # Get sets for this game
        resp = await client.get(f"{BASE_URL}/{cat_id}/sets")
        if resp.status_code != 200:
            logger.error("TCGTracking sets request failed for %s: %d", game_id, resp.status_code)
            return 0
        sets_data = resp.json().get("sets", [])

        total = 0
        for s in sets_data:
            set_id = s["id"]
            # Get products (for name→card_id mapping)
            prod_resp = await client.get(f"{BASE_URL}/{cat_id}/sets/{set_id}")
            if prod_resp.status_code != 200:
                continue
            products = prod_resp.json().get("products", [])

            # Get pricing
            price_resp = await client.get(f"{BASE_URL}/{cat_id}/sets/{set_id}/pricing")
            if price_resp.status_code != 200:
                continue
            prices = price_resp.json().get("prices", {})

            # Build price records — match by name to our DB
            records = []
            for prod in products:
                prod_id = str(prod["id"])
                price_data = prices.get(prod_id, {}).get("tcg", {})
                if not price_data:
                    continue

                # Get first available subtype prices
                for subtype, p in price_data.items():
                    market = p.get("market")
                    low = p.get("low")
                    if market or low:
                        records.append({
                            "product_name": prod.get("name", ""),
                            "tcg_product_id": prod_id,
                            "market": market,
                            "low": low,
                            "subtype": subtype,
                        })
                    break  # just first subtype (Normal usually)

            # Match products to our card IDs by name and insert price records
            if records:
                count = await _insert_price_records(game_id, records)
                total += count
                logger.info("TCGTracking %s set %s: %d prices", game_id, s.get("name", set_id), count)

    logger.info("TCGTracking sync complete for %s: %d total records", game_id, total)
    return total


async def _insert_price_records(game_id: str, records: list[dict]) -> int:
    """Match product names to our card_ids and insert PriceRecord entries.
    Products that don't match cards get inserted into the product table as sealed products."""
    count = 0
    sealed_products = []

    async with async_session() as session:
        conn = await session.connection()
        for r in records:
            name = r["product_name"]

            # Match by exact card name within game
            result = await conn.execute(
                text("SELECT id FROM card WHERE game_id = :game AND name_en = :name LIMIT 1"),
                {"game": game_id, "name": name},
            )
            row = result.fetchone()

            if row:
                card_id = row[0]
                await conn.execute(
                    text("""INSERT INTO price_record (card_id, source, currency, price_low, price_market)
                            VALUES (:card_id, 'tcgtracking', 'USD', :low, :market)"""),
                    {"card_id": card_id, "low": r.get("low"), "market": r.get("market")},
                )
                count += 1
            else:
                # No card match — likely a sealed product (booster box, pack, etc.)
                sealed_products.append({
                    "name": name, "game_id": game_id,
                    "product_type": _guess_product_type(name),
                    "sku": f"tcg-{r['tcg_product_id']}",
                    "msrp": r.get("market"), "listed_price": r.get("market"),
                })

        # Insert sealed products
        if sealed_products:
            await conn.execute(
                text("""INSERT OR IGNORE INTO product (name, game_id, product_type, sku, msrp, listed_price, quantity, available_online, online_quantity)
                        VALUES (:name, :game_id, :product_type, :sku, :msrp, :listed_price, 0, 0, 0)"""),
                sealed_products,
            )

        await session.commit()
    return count


def _guess_product_type(name: str) -> str:
    """Guess product type from name."""
    lower = name.lower()
    if 'booster' in lower and ('display' in lower or 'box' in lower or 'case' in lower):
        return 'box'
    if 'booster' in lower or 'pack' in lower:
        return 'pack'
    if 'bundle' in lower:
        return 'bundle'
    if 'deck' in lower:
        return 'deck'
    return 'accessory'
