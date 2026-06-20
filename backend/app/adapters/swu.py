"""Star Wars Unlimited adapter using api.swu-db.com."""
import json
import logging

import httpx

from app.adapters.base import BaseAdapter, CardResult
from app.database import async_session
from app.models.card import Card, CardName
from app.models.game import CardSet

logger = logging.getLogger(__name__)

GAME_ID = "swu"
BASE_URL = "https://api.swu-db.com"
# Known sets
SETS = ["SOR", "SHD", "TWI", "JTL", "LOF"]


class Adapter(BaseAdapter):
    game_id = GAME_ID

    async def sync_cards(self, sets: list[str] | None = None) -> int:
        target_sets = sets or SETS
        cards_batch = []
        names_batch = []
        sets_seen: dict[str, dict] = {}

        async with httpx.AsyncClient(timeout=30) as client:
            for set_code in target_sets:
                resp = await client.get(f"{BASE_URL}/cards/search?q=set:{set_code}")
                if resp.status_code != 200:
                    logger.warning("SWU API returned %d for set %s", resp.status_code, set_code)
                    continue
                data = resp.json()
                cards = data.get("data", [])

                set_id = f"{GAME_ID}:{set_code.lower()}"
                sets_seen[set_code] = {
                    "id": set_id, "game_id": GAME_ID, "code": set_code.lower(),
                    "name": set_code, "released_at": None, "card_count": len(cards), "icon_url": None,
                }

                for c in cards:
                    num = str(c.get("Number", "0"))
                    card_id = f"{GAME_ID}:{set_code.lower()}:{num}"
                    name = c.get("Name", "Unknown")
                    subtitle = c.get("Subtitle")
                    full_name = f"{name}, {subtitle}" if subtitle else name

                    cards_batch.append({
                        "id": card_id, "game_id": GAME_ID, "set_id": set_id,
                        "collector_number": num, "name_en": full_name,
                        "rarity": c.get("Rarity"),
                        "card_type": c.get("Type"),
                        "subtypes": json.dumps(c.get("Traits", [])),
                        "colors": json.dumps(c.get("Aspects", [])),
                        "mana_cost": str(c.get("Cost")) if c.get("Cost") else None,
                        "image_url_small": c.get("FrontArt"),
                        "image_url_normal": c.get("FrontArt"),
                        "image_url_large": c.get("FrontArt"),
                        "external_ids": None,
                    })
                    names_batch.append({"card_id": card_id, "locale": "en", "name": full_name})

                logger.info("SWU: fetched %d cards from set %s", len(cards), set_code)

        async with async_session() as session:
            conn = await session.connection()
            if sets_seen:
                await conn.execute(CardSet.__table__.insert().prefix_with("OR IGNORE"), list(sets_seen.values()))
            for i in range(0, len(cards_batch), 5000):
                await conn.execute(Card.__table__.insert().prefix_with("OR IGNORE"), cards_batch[i:i+5000])
            for i in range(0, len(names_batch), 5000):
                await conn.execute(CardName.__table__.insert().prefix_with("OR IGNORE"), names_batch[i:i+5000])
            await session.commit()

        logger.info("SWU sync complete: %d cards, %d sets", len(cards_batch), len(sets_seen))
        return len(cards_batch)

    async def sync_prices(self, card_ids: list[str] | None = None) -> int:
        return 0

    async def search(self, query: str, locale: str = "en") -> list[CardResult]:
        from sqlalchemy import select
        async with async_session() as session:
            results = (await session.execute(
                select(Card).where(Card.game_id == GAME_ID, Card.name_en.ilike(f"%{query}%")).limit(10)
            )).scalars().all()
            return [CardResult(card_id=c.id, name=c.name_en, set_code=c.set_id.split(":")[1], collector_number=c.collector_number, image_url=c.image_url_small) for c in results]

    async def get_card_image_url(self, card_id: str, size: str = "small") -> str | None:
        from sqlalchemy import select
        async with async_session() as session:
            card = (await session.execute(select(Card).where(Card.id == card_id))).scalar_one_or_none()
            return card.image_url_small if card else None
