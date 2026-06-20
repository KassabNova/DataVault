"""MTG adapter using Scryfall bulk data."""
import json
import logging
from pathlib import Path

import httpx
from sqlalchemy import select

from app.adapters.base import BaseAdapter, CardResult
from app.database import async_session
from app.models.card import Card, CardName
from app.models.game import CardSet

logger = logging.getLogger(__name__)

BULK_DATA_URL = "https://api.scryfall.com/bulk-data"
GAME_ID = "mtg"
DATA_DIR = Path("data")


class Adapter(BaseAdapter):
    game_id = GAME_ID

    async def sync_cards(self, sets: list[str] | None = None) -> int:
        bulk_path = await self._download_bulk_data()
        count = await self._import_cards(bulk_path, sets)
        return count

    async def sync_prices(self, card_ids: list[str] | None = None) -> int:
        """Extract prices from Scryfall bulk data (must run after sync_cards)."""
        bulk_path = DATA_DIR / "scryfall_bulk.json"
        if not bulk_path.exists():
            bulk_path = await self._download_bulk_data()
        return await self._extract_prices(bulk_path, card_ids)

    async def search(self, query: str, locale: str = "en") -> list[CardResult]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.scryfall.com/cards/search",
                params={"q": query},
                timeout=15,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            return [
                CardResult(
                    card_id=f"{GAME_ID}:{c['set']}:{c['collector_number']}",
                    name=c.get("printed_name", c["name"]) if locale == "es" else c["name"],
                    set_code=c["set"],
                    collector_number=c["collector_number"],
                    image_url=(c.get("image_uris") or {}).get("small"),
                )
                for c in data.get("data", [])[:10]
            ]

    async def get_card_image_url(self, card_id: str, size: str = "small") -> str | None:
        # card_id format: mtg:set:num
        parts = card_id.split(":")
        if len(parts) != 3:
            return None
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.scryfall.com/cards/{parts[1]}/{parts[2]}",
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            return (resp.json().get("image_uris") or {}).get(size)

    async def _download_bulk_data(self) -> Path:
        """Download the 'default_cards' bulk file from Scryfall."""
        DATA_DIR.mkdir(exist_ok=True)
        bulk_path = DATA_DIR / "scryfall_bulk.json"

        async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
            # Get bulk data download URL
            resp = await client.get(BULK_DATA_URL)
            resp.raise_for_status()
            bulk_items = resp.json()["data"]
            default = next(i for i in bulk_items if i["type"] == "default_cards")
            download_url = default["download_uri"]

            logger.info("Downloading Scryfall bulk data (%s)...", default.get("size", "?"))
            # Stream download to disk
            async with client.stream("GET", download_url) as stream:
                stream.raise_for_status()
                with open(bulk_path, "wb") as f:
                    async for chunk in stream.aiter_bytes(chunk_size=1024 * 256):
                        f.write(chunk)

        logger.info("Bulk data saved to %s", bulk_path)
        return bulk_path

    async def _import_cards(self, bulk_path: Path, sets_filter: list[str] | None) -> int:
        """Parse bulk JSON and upsert into DB."""
        logger.info("Parsing bulk data...")
        with open(bulk_path) as f:
            cards_data = json.load(f)

        # Collect unique sets
        sets_seen: dict[str, dict] = {}
        cards_batch: list[dict] = []
        names_batch: list[dict] = []

        for c in cards_data:
            # Skip tokens, emblems, art_series, etc.
            if c.get("layout") in ("token", "double_faced_token", "art_series"):
                continue
            if c.get("digital", False):
                continue

            set_code = c["set"]
            if sets_filter and set_code not in sets_filter:
                continue

            set_id = f"{GAME_ID}:{set_code}"
            if set_code not in sets_seen:
                sets_seen[set_code] = {
                    "id": set_id,
                    "game_id": GAME_ID,
                    "code": set_code,
                    "name": c.get("set_name", set_code),
                    "released_at": c.get("released_at"),
                    "card_count": None,
                    "icon_url": c.get("set_uri"),
                }

            card_id = f"{GAME_ID}:{set_code}:{c['collector_number']}"
            images = c.get("image_uris") or {}

            cards_batch.append({
                "id": card_id,
                "game_id": GAME_ID,
                "set_id": set_id,
                "collector_number": c["collector_number"],
                "name_en": c["name"],
                "rarity": c.get("rarity"),
                "card_type": c.get("type_line"),
                "subtypes": json.dumps(c.get("keywords", [])),
                "colors": json.dumps(c.get("colors", [])),
                "mana_cost": c.get("mana_cost"),
                "image_url_small": images.get("small"),
                "image_url_normal": images.get("normal"),
                "image_url_large": images.get("large"),
                "external_ids": json.dumps({"scryfall": c["id"]}),
            })

            # English name
            names_batch.append({"card_id": card_id, "locale": "en", "name": c["name"]})
            # Spanish name if available
            printed_name = c.get("printed_name")
            if printed_name and c.get("lang") == "es":
                names_batch.append({"card_id": card_id, "locale": "es", "name": printed_name})

        # Bulk upsert - use OR IGNORE via raw insert to avoid sqlite3 version issues
        count = 0
        async with async_session() as session:
            conn = await session.connection()

            # Upsert sets
            for s in sets_seen.values():
                await conn.execute(
                    CardSet.__table__.insert().prefix_with("OR IGNORE"),
                    s,
                )

            # Upsert cards in batches
            batch_size = 5000
            for i in range(0, len(cards_batch), batch_size):
                batch = cards_batch[i:i + batch_size]
                await conn.execute(
                    Card.__table__.insert().prefix_with("OR IGNORE"),
                    batch,
                )
                count += len(batch)
                if count % 20000 == 0:
                    logger.info("Inserted %d cards...", count)

            # Upsert names
            for i in range(0, len(names_batch), batch_size):
                batch = names_batch[i:i + batch_size]
                await conn.execute(
                    CardName.__table__.insert().prefix_with("OR IGNORE"),
                    batch,
                )

            await session.commit()

        logger.info("Import complete: %d cards, %d sets", count, len(sets_seen))
        return count

    async def _extract_prices(self, bulk_path: Path, card_ids: list[str] | None) -> int:
        """Extract price data from Scryfall bulk JSON into PriceRecord."""
        from app.models.price import PriceRecord

        with open(bulk_path) as f:
            cards_data = json.load(f)

        prices_batch = []
        for c in cards_data:
            if c.get("layout") in ("token", "double_faced_token", "art_series"):
                continue
            if c.get("digital", False):
                continue

            card_id = f"{GAME_ID}:{c['set']}:{c['collector_number']}"
            if card_ids and card_id not in card_ids:
                continue

            prices = c.get("prices", {})
            usd = prices.get("usd")
            usd_foil = prices.get("usd_foil")
            eur = prices.get("eur")

            if usd or usd_foil:
                prices_batch.append({
                    "card_id": card_id,
                    "source": "scryfall",
                    "currency": "USD",
                    "price_low": float(usd) if usd else None,
                    "price_mid": float(usd) if usd else None,
                    "price_high": float(usd_foil) if usd_foil else None,
                    "price_market": float(usd) if usd else None,
                })
            if eur:
                prices_batch.append({
                    "card_id": card_id,
                    "source": "scryfall",
                    "currency": "EUR",
                    "price_low": float(eur),
                    "price_mid": float(eur),
                    "price_high": float(prices.get("eur_foil") or eur),
                    "price_market": float(eur),
                })

        # Bulk insert
        batch_size = 5000
        count = 0
        async with async_session() as session:
            conn = await session.connection()
            for i in range(0, len(prices_batch), batch_size):
                await conn.execute(
                    PriceRecord.__table__.insert(),
                    prices_batch[i:i + batch_size],
                )
                count += len(prices_batch[i:i + batch_size])
            await session.commit()

        logger.info("Price extraction complete: %d records", count)
        return count
