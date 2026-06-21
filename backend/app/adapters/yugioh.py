"""Yu-Gi-Oh adapter using YGOProDeck API (db.ygoprodeck.com)."""
import json
import logging

import httpx

from app.adapters.base import BaseAdapter, CardResult
from app.database import async_session
from app.models.card import Card, CardName
from app.models.game import CardSet

logger = logging.getLogger(__name__)

GAME_ID = "yugioh"
BASE_URL = "https://db.ygoprodeck.com/api/v7"


class Adapter(BaseAdapter):
    game_id = GAME_ID

    async def sync_cards(self, sets: list[str] | None = None) -> int:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(f"{BASE_URL}/cardinfo.php")
            resp.raise_for_status()
            data = resp.json()

        cards_data = data.get("data", [])
        sets_seen: dict[str, dict] = {}
        cards_batch = []
        names_batch = []

        for c in cards_data:
            # Use first set appearance
            card_sets = c.get("card_sets") or []
            if sets and card_sets:
                if not any(cs.get("set_code", "").split("-")[0] in sets for cs in card_sets):
                    continue

            set_code = card_sets[0]["set_code"].split("-")[0] if card_sets else "promo"
            set_id = f"{GAME_ID}:{set_code}"
            if set_code not in sets_seen:
                set_name = card_sets[0].get("set_name", set_code) if card_sets else "Promo"
                sets_seen[set_code] = {
                    "id": set_id, "game_id": GAME_ID, "code": set_code,
                    "name": set_name, "released_at": None, "card_count": None, "icon_url": None,
                }

            card_id_num = str(c["id"])
            card_id = f"{GAME_ID}:{set_code}:{card_id_num}"
            images = c.get("card_images", [{}])[0]

            cards_batch.append({
                "id": card_id, "game_id": GAME_ID, "set_id": set_id,
                "collector_number": card_id_num,
                "name_en": c["name"],
                "rarity": card_sets[0].get("set_rarity") if card_sets else None,
                "card_type": c.get("type"),
                "subtypes": json.dumps([c.get("race", "")]),
                "colors": json.dumps([c.get("attribute", "")]) if c.get("attribute") else None,
                "mana_cost": str(c.get("level")) if c.get("level") else None,
                "image_url_small": images.get("image_url_small"),
                "image_url_normal": images.get("image_url"),
                "image_url_large": images.get("image_url"),
                "external_ids": json.dumps({"ygoprodeck": c["id"]}),
            })
            names_batch.append({"card_id": card_id, "locale": "en", "name": c["name"]})

        async with async_session() as session:
            conn = await session.connection()
            if sets_seen:
                await conn.execute(CardSet.__table__.insert().prefix_with("OR IGNORE"), list(sets_seen.values()))
            for i in range(0, len(cards_batch), 5000):
                await conn.execute(Card.__table__.insert().prefix_with("OR IGNORE"), cards_batch[i:i+5000])
            for i in range(0, len(names_batch), 5000):
                await conn.execute(CardName.__table__.insert().prefix_with("OR IGNORE"), names_batch[i:i+5000])
            await session.commit()

        logger.info("Yu-Gi-Oh sync complete: %d cards, %d sets", len(cards_batch), len(sets_seen))
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
        from sqlalchemy import select
        async with async_session() as session:
            card = (await session.execute(select(Card).where(Card.id == card_id))).scalar_one_or_none()
            return card.image_url_small if card else None
