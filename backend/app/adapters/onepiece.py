"""One Piece TCG adapter using Bandai TCG Plus API."""
import json
import logging

import httpx

from app.adapters.base import BaseAdapter, CardResult
from app.database import async_session
from app.models.card import Card, CardName
from app.models.game import CardSet

logger = logging.getLogger(__name__)

GAME_ID = "onepiece"
BASE_URL = "https://api.bandai-tcg-plus.com/api/user/card/list"
GAME_TITLE_ID = 4  # One Piece TCG (English)


class Adapter(BaseAdapter):
    game_id = GAME_ID

    async def sync_cards(self, sets: list[str] | None = None) -> int:
        cards_batch = []
        names_batch = []
        sets_seen: dict[str, dict] = {}
        offset = 0
        limit = 100

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                resp = await client.get(BASE_URL, params={"game_title_id": GAME_TITLE_ID, "limit": limit, "offset": offset})
                if resp.status_code != 200:
                    break
                data = resp.json()
                cards = data.get("success", {}).get("cards", [])
                if not cards:
                    break

                for c in cards:
                    card_number = c.get("card_number", "0")
                    # Extract set from card number (e.g., OP01-001 → OP01)
                    set_code = card_number.split("-")[0] if "-" in card_number else "promo"
                    if sets and set_code.lower() not in [s.lower() for s in sets]:
                        continue

                    set_id = f"{GAME_ID}:{set_code.lower()}"
                    if set_code not in sets_seen:
                        sets_seen[set_code] = {
                            "id": set_id, "game_id": GAME_ID, "code": set_code.lower(),
                            "name": set_code, "released_at": None, "card_count": None, "icon_url": None,
                        }

                    card_id = f"{GAME_ID}:{set_code.lower()}:{card_number}"
                    name = c.get("card_name", "Unknown")

                    cards_batch.append({
                        "id": card_id, "game_id": GAME_ID, "set_id": set_id,
                        "collector_number": card_number, "name_en": name,
                        "rarity": c.get("rarity"),
                        "card_type": c.get("type"),
                        "subtypes": None,
                        "colors": json.dumps([c.get("color", "")]) if c.get("color") else None,
                        "mana_cost": str(c.get("cost")) if c.get("cost") else None,
                        "image_url_small": c.get("image_url"),
                        "image_url_normal": c.get("image_url"),
                        "image_url_large": c.get("image_url"),
                        "external_ids": json.dumps({"bandai_id": c.get("id")}),
                    })
                    names_batch.append({"card_id": card_id, "locale": "en", "name": name})

                offset += limit
                total = int(data.get("success", {}).get("total", 0))
                logger.info("One Piece: fetched %d/%d cards", min(offset, total), total)
                if offset >= total:
                    break

        async with async_session() as session:
            conn = await session.connection()
            if sets_seen:
                await conn.execute(CardSet.__table__.insert().prefix_with("OR IGNORE"), list(sets_seen.values()))
            for i in range(0, len(cards_batch), 5000):
                await conn.execute(Card.__table__.insert().prefix_with("OR IGNORE"), cards_batch[i:i+5000])
            for i in range(0, len(names_batch), 5000):
                await conn.execute(CardName.__table__.insert().prefix_with("OR IGNORE"), names_batch[i:i+5000])
            await session.commit()

        logger.info("One Piece sync complete: %d cards, %d sets", len(cards_batch), len(sets_seen))
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
