"""Lorcana adapter using lorcanajson.org API."""
import logging

import httpx

from app.adapters.base import BaseAdapter, CardResult
from app.database import async_session
from app.models.card import Card, CardName
from app.models.game import CardSet

logger = logging.getLogger(__name__)

GAME_ID = "lorcana"
BASE_URL = "https://lorcanajson.org"


class Adapter(BaseAdapter):
    game_id = GAME_ID

    async def sync_cards(self, sets: list[str] | None = None) -> int:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(f"{BASE_URL}/files/current/en/allCards.json")
            resp.raise_for_status()
            data = resp.json()

        # Parse sets
        sets_map = data.get("sets", {})
        sets_batch = []
        for code, s in sets_map.items():
            if sets and code not in sets:
                continue
            sets_batch.append({
                "id": f"{GAME_ID}:{code}",
                "game_id": GAME_ID,
                "code": code,
                "name": s.get("name", code),
                "released_at": s.get("releaseDate"),
                "card_count": None,
                "icon_url": None,
            })

        # Parse cards
        cards_data = data.get("cards", [])
        cards_batch = []
        names_batch = []

        for c in cards_data:
            set_code = str(c.get("setCode", "1"))
            if sets and set_code not in sets:
                continue

            collector_num = str(c.get("number", "0"))
            card_id = f"{GAME_ID}:{set_code}:{collector_num}"
            name = c.get("fullName") or c.get("name", "Unknown")
            images = c.get("images", {})

            cards_batch.append({
                "id": card_id,
                "game_id": GAME_ID,
                "set_id": f"{GAME_ID}:{set_code}",
                "collector_number": collector_num,
                "name_en": name,
                "rarity": c.get("rarity"),
                "card_type": c.get("type"),
                "subtypes": str(c.get("subtypes", [])),
                "colors": str([c.get("color", "")]) if c.get("color") else None,
                "mana_cost": str(c.get("cost")) if c.get("cost") else None,
                "image_url_small": images.get("thumbnail"),
                "image_url_normal": images.get("full"),
                "image_url_large": images.get("full"),
                "external_ids": None,
            })
            names_batch.append({"card_id": card_id, "locale": "en", "name": name})

        async with async_session() as session:
            conn = await session.connection()
            if sets_batch:
                await conn.execute(CardSet.__table__.insert().prefix_with("OR IGNORE"), sets_batch)
            for i in range(0, len(cards_batch), 5000):
                await conn.execute(Card.__table__.insert().prefix_with("OR IGNORE"), cards_batch[i:i+5000])
            for i in range(0, len(names_batch), 5000):
                await conn.execute(CardName.__table__.insert().prefix_with("OR IGNORE"), names_batch[i:i+5000])
            await session.commit()

        logger.info("Lorcana sync complete: %d cards, %d sets", len(cards_batch), len(sets_batch))
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
