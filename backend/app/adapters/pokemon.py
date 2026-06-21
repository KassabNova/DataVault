"""Pokémon TCG adapter using pokemontcg.io API."""
import logging

import httpx

from app.adapters.base import BaseAdapter, CardResult
from app.database import async_session
from app.models.card import Card, CardName
from app.models.game import CardSet

logger = logging.getLogger(__name__)

BASE_URL = "https://api.pokemontcg.io/v2"
GAME_ID = "pokemon"


class Adapter(BaseAdapter):
    game_id = GAME_ID

    async def sync_cards(self, sets: list[str] | None = None) -> int:
        async with httpx.AsyncClient(timeout=30) as client:
            # Sync sets first
            await self._sync_sets(client, sets)
            # Then sync cards
            return await self._sync_cards(client, sets)

    async def sync_prices(self, card_ids: list[str] | None = None) -> int:
        from app.services.tcgtracking import sync_prices_from_tcgtracking
        return await sync_prices_from_tcgtracking(GAME_ID)  # pokemontcg.io has limited price data

    async def search(self, query: str, locale: str = "en") -> list[CardResult]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{BASE_URL}/cards", params={"q": f"name:{query}*", "pageSize": 10})
            if resp.status_code != 200:
                return []
            return [
                CardResult(
                    card_id=f"{GAME_ID}:{c['set']['id']}:{c['number']}",
                    name=c["name"],
                    set_code=c["set"]["id"],
                    collector_number=c["number"],
                    image_url=c.get("images", {}).get("small"),
                )
                for c in resp.json().get("data", [])
            ]

    async def get_card_image_url(self, card_id: str, size: str = "small") -> str | None:
        parts = card_id.split(":")
        if len(parts) != 3:
            return None
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{BASE_URL}/cards", params={"q": f"set.id:{parts[1]} number:{parts[2]}", "pageSize": 1})
            if resp.status_code != 200:
                return None
            data = resp.json().get("data", [])
            if not data:
                return None
            return data[0].get("images", {}).get(size)

    async def _sync_sets(self, client: httpx.AsyncClient, sets_filter: list[str] | None):
        resp = await client.get(f"{BASE_URL}/sets", params={"orderBy": "releaseDate"})
        resp.raise_for_status()
        sets_data = resp.json()["data"]

        batch = []
        for s in sets_data:
            if sets_filter and s["id"] not in sets_filter:
                continue
            batch.append({
                "id": f"{GAME_ID}:{s['id']}",
                "game_id": GAME_ID,
                "code": s["id"],
                "name": s["name"],
                "released_at": s.get("releaseDate"),
                "card_count": s.get("total"),
                "icon_url": s.get("images", {}).get("symbol"),
            })

        async with async_session() as session:
            conn = await session.connection()
            await conn.execute(CardSet.__table__.insert().prefix_with("OR IGNORE"), batch)
            await session.commit()
        logger.info("Synced %d Pokémon sets", len(batch))

    async def _sync_cards(self, client: httpx.AsyncClient, sets_filter: list[str] | None) -> int:
        page = 1
        total = 0
        cards_batch = []
        names_batch = []

        while True:
            params: dict = {"pageSize": 250, "page": page}
            if sets_filter:
                params["q"] = " OR ".join(f"set.id:{s}" for s in sets_filter)

            resp = await client.get(f"{BASE_URL}/cards", params=params)
            if resp.status_code != 200:
                logger.warning("Pokémon API returned %d on page %d", resp.status_code, page)
                break

            data = resp.json()
            cards = data.get("data", [])
            if not cards:
                break

            for c in cards:
                set_code = c["set"]["id"]
                card_id = f"{GAME_ID}:{set_code}:{c['number']}"
                images = c.get("images", {})

                cards_batch.append({
                    "id": card_id,
                    "game_id": GAME_ID,
                    "set_id": f"{GAME_ID}:{set_code}",
                    "collector_number": c["number"],
                    "name_en": c["name"],
                    "rarity": c.get("rarity"),
                    "card_type": c.get("supertype"),
                    "subtypes": str(c.get("subtypes", [])),
                    "colors": str(c.get("types", [])),
                    "mana_cost": None,
                    "image_url_small": images.get("small"),
                    "image_url_normal": images.get("large"),
                    "image_url_large": images.get("large"),
                    "external_ids": f'{{"pokemontcg": "{c["id"]}"}}',
                })
                names_batch.append({"card_id": card_id, "locale": "en", "name": c["name"]})

            total += len(cards)
            logger.info("Pokémon: fetched page %d (%d cards so far)", page, total)

            # Check if more pages
            total_count = data.get("totalCount", 0)
            if total >= total_count:
                break
            page += 1

        # Bulk insert
        if cards_batch:
            async with async_session() as session:
                conn = await session.connection()
                for i in range(0, len(cards_batch), 5000):
                    await conn.execute(Card.__table__.insert().prefix_with("OR IGNORE"), cards_batch[i:i+5000])
                for i in range(0, len(names_batch), 5000):
                    await conn.execute(CardName.__table__.insert().prefix_with("OR IGNORE"), names_batch[i:i+5000])
                await session.commit()

        logger.info("Pokémon sync complete: %d cards", total)
        return total
