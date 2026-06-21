"""Flesh and Blood adapter using the-fab-cube GitHub JSON data."""
import json
import logging

import httpx

from app.adapters.base import BaseAdapter, CardResult
from app.database import async_session
from app.models.card import Card, CardName
from app.models.game import CardSet

logger = logging.getLogger(__name__)

GAME_ID = "fab"
REPO_BASE = "https://raw.githubusercontent.com/the-fab-cube/flesh-and-blood-cards/refs/heads/develop"


class Adapter(BaseAdapter):
    game_id = GAME_ID

    async def sync_cards(self, sets: list[str] | None = None) -> int:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            # Get card data from the JSON repo
            resp = await client.get(f"{REPO_BASE}/json/english/card.json")
            resp.raise_for_status()
            cards_data = resp.json()

        sets_seen: dict[str, dict] = {}
        cards_batch = []
        names_batch = []

        for c in cards_data:
            set_code = (c.get("setIdentifiers") or [{}])[0].get("set", "unknown") if c.get("setIdentifiers") else "promo"
            if sets and set_code not in sets:
                continue

            set_id = f"{GAME_ID}:{set_code}"
            if set_code not in sets_seen:
                sets_seen[set_code] = {
                    "id": set_id,
                    "game_id": GAME_ID,
                    "code": set_code,
                    "name": set_code.upper(),
                    "released_at": None,
                    "card_count": None,
                    "icon_url": None,
                }

            collector_num = (c.get("setIdentifiers") or [{}])[0].get("identifier", c.get("unique_id", "0")) if c.get("setIdentifiers") else c.get("unique_id", "0")
            card_id = f"{GAME_ID}:{set_code}:{collector_num}"

            # Get image from first printing
            printings = c.get("printings", [])
            image_url = printings[0].get("image_url") if printings else None

            cards_batch.append({
                "id": card_id,
                "game_id": GAME_ID,
                "set_id": set_id,
                "collector_number": collector_num,
                "name_en": c.get("name", "Unknown"),
                "rarity": c.get("rarity"),
                "card_type": c.get("types", [None])[0] if c.get("types") else None,
                "subtypes": str(c.get("subtypes", [])),
                "colors": None,
                "mana_cost": str(c.get("cost")) if c.get("cost") else None,
                "image_url_small": image_url,
                "image_url_normal": image_url,
                "image_url_large": image_url,
                "external_ids": json.dumps({"fab_id": c.get("unique_id")}),
            })
            names_batch.append({"card_id": card_id, "locale": "en", "name": c.get("name", "Unknown")})

        # Bulk insert
        async with async_session() as session:
            conn = await session.connection()
            if sets_seen:
                await conn.execute(CardSet.__table__.insert().prefix_with("OR IGNORE"), list(sets_seen.values()))
            for i in range(0, len(cards_batch), 5000):
                await conn.execute(Card.__table__.insert().prefix_with("OR IGNORE"), cards_batch[i:i+5000])
            # Update image URLs for cards that were previously missing them
            from sqlalchemy import text
            for c in cards_batch:
                if c["image_url_small"]:
                    await conn.execute(text(
                        "UPDATE card SET image_url_small=:img, image_url_normal=:img WHERE id=:id AND image_url_small IS NULL"
                    ), {"img": c["image_url_small"], "id": c["id"]})
            for i in range(0, len(names_batch), 5000):
                await conn.execute(CardName.__table__.insert().prefix_with("OR IGNORE"), names_batch[i:i+5000])
            await session.commit()

        logger.info("FaB sync complete: %d cards, %d sets", len(cards_batch), len(sets_seen))
        return len(cards_batch)

    async def sync_prices(self, card_ids: list[str] | None = None) -> int:
        from app.services.tcgtracking import sync_prices_from_tcgtracking
        return await sync_prices_from_tcgtracking(GAME_ID)

    async def search(self, query: str, locale: str = "en") -> list[CardResult]:
        from sqlalchemy import select
        async with async_session() as session:
            results = (await session.execute(
                select(Card).where(Card.game_id == GAME_ID, Card.name_en.ilike(f"%{query}%")).limit(10)
            )).scalars().all()
            return [CardResult(card_id=c.id, name=c.name_en, set_code=c.set_id.split(":")[1], collector_number=c.collector_number, image_url=c.image_url_small) for c in results]

    async def get_card_image_url(self, card_id: str, size: str = "small") -> str | None:
        return None
