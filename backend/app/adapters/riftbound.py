"""Riftbound adapter - using community gist data until Riot API key is obtained."""
import csv
import io
import json
import logging

import httpx

from app.adapters.base import BaseAdapter, CardResult
from app.database import async_session
from app.models.card import Card, CardName
from app.models.game import CardSet

logger = logging.getLogger(__name__)

GAME_ID = "riftbound"
GIST_URL = "https://gist.githubusercontent.com/OwenMelbz/e04dadf641cc9b81cb882b4612343112/raw"


class Adapter(BaseAdapter):
    game_id = GAME_ID

    async def sync_cards(self, sets: list[str] | None = None) -> int:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(GIST_URL)
            resp.raise_for_status()
            cards_data = resp.json()

        sets_seen: dict[str, dict] = {}
        cards_batch = []
        names_batch = []

        for c in cards_data:
            set_code = c.get("set", "OGS").lower()
            if sets and set_code not in sets:
                continue

            set_id = f"{GAME_ID}:{set_code}"
            if set_code not in sets_seen:
                sets_seen[set_code] = {
                    "id": set_id, "game_id": GAME_ID, "code": set_code,
                    "name": c.get("setName", set_code.upper()),
                    "released_at": None, "card_count": None, "icon_url": None,
                }

            collector_num = str(c.get("collectorNumber", "0"))
            card_id = f"{GAME_ID}:{set_code}:{collector_num}"
            name = c.get("name", "Unknown")
            public_code = c.get("publicCode", "")
            cdn_code = public_code.split("/")[0] if "/" in public_code else public_code
            image = f"https://cdn.piltoverarchive.com/cards/{cdn_code}.webp?width=480" if cdn_code else None
            rarity = c.get("rarity", {}).get("label") if isinstance(c.get("rarity"), dict) else c.get("rarity")
            card_types = c.get("cardType", [])
            card_type = card_types[0].get("label") if card_types and isinstance(card_types[0], dict) else None

            cards_batch.append({
                "id": card_id, "game_id": GAME_ID, "set_id": set_id,
                "collector_number": collector_num, "name_en": name,
                "rarity": rarity, "card_type": card_type,
                "subtypes": json.dumps([d.get("label", "") for d in c.get("domains", [])]),
                "colors": None,
                "mana_cost": str(c.get("energy")) if c.get("energy") else None,
                "image_url_small": image, "image_url_normal": image, "image_url_large": image,
                "external_ids": json.dumps({"riftbound_id": c.get("id")}),
            })
            names_batch.append({"card_id": card_id, "locale": "en", "name": name})

        async with async_session() as session:
            conn = await session.connection()
            if sets_seen:
                await conn.execute(CardSet.__table__.insert().prefix_with("OR IGNORE"), list(sets_seen.values()))
            if cards_batch:
                await conn.execute(Card.__table__.insert().prefix_with("OR IGNORE"), cards_batch)
                await conn.execute(CardName.__table__.insert().prefix_with("OR IGNORE"), names_batch)
            await session.commit()

        logger.info("Riftbound sync complete: %d cards, %d sets", len(cards_batch), len(sets_seen))
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

    async def import_csv(self, csv_content: str) -> int:
        """Import cards from CSV. Columns: set_code, collector_number, name, rarity, card_type"""
        reader = csv.DictReader(io.StringIO(csv_content))
        cards_batch = []
        names_batch = []
        sets_seen: dict[str, dict] = {}

        for row in reader:
            set_code = row.get("set_code", "base").strip()
            set_id = f"{GAME_ID}:{set_code}"
            if set_code not in sets_seen:
                sets_seen[set_code] = {
                    "id": set_id, "game_id": GAME_ID, "code": set_code,
                    "name": set_code.title(), "released_at": None, "card_count": None, "icon_url": None,
                }
            collector_num = row.get("collector_number", "0").strip()
            card_id = f"{GAME_ID}:{set_code}:{collector_num}"
            name = row.get("name", "Unknown").strip()
            cards_batch.append({
                "id": card_id, "game_id": GAME_ID, "set_id": set_id,
                "collector_number": collector_num, "name_en": name,
                "rarity": row.get("rarity", "").strip() or None,
                "card_type": row.get("card_type", "").strip() or None,
                "subtypes": None, "colors": None, "mana_cost": None,
                "image_url_small": None, "image_url_normal": None, "image_url_large": None,
                "external_ids": None,
            })
            names_batch.append({"card_id": card_id, "locale": "en", "name": name})

        async with async_session() as session:
            conn = await session.connection()
            if sets_seen:
                await conn.execute(CardSet.__table__.insert().prefix_with("OR IGNORE"), list(sets_seen.values()))
            if cards_batch:
                await conn.execute(Card.__table__.insert().prefix_with("OR IGNORE"), cards_batch)
                await conn.execute(CardName.__table__.insert().prefix_with("OR IGNORE"), names_batch)
            await session.commit()

        logger.info("Riftbound CSV import: %d cards", len(cards_batch))
        return len(cards_batch)
