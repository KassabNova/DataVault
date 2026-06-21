"""Riftbound adapter - uses TCGTracking for card data + Piltover Archive CDN for images."""
import csv
import io
import json
import logging

import httpx

from app.adapters.base import BaseAdapter, CardResult
from app.database import async_session
from app.models.card import Card, CardName
from app.models.game import CardSet
from app.services.tcgtracking import sync_prices_from_tcgtracking

logger = logging.getLogger(__name__)

GAME_ID = "riftbound"
TCGTRACKING_CAT = 89
BASE_URL = "https://tcgtracking.com/tcgapi/v1"
CDN_BASE = "https://cdn.piltoverarchive.com/cards"


class Adapter(BaseAdapter):
    game_id = GAME_ID

    async def sync_cards(self, sets: list[str] | None = None) -> int:
        """Sync all Riftbound cards from TCGTracking API."""
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(f"{BASE_URL}/{TCGTRACKING_CAT}/sets")
            resp.raise_for_status()
            sets_data = resp.json().get("sets", [])

        sets_seen: dict[str, dict] = {}
        cards_batch = []
        names_batch = []

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for s in sets_data:
                set_tcg_id = s["id"]
                set_name = s.get("name", "Unknown")
                set_code = set_name.lower().replace(" ", "_")[:20]

                if sets and set_code not in sets:
                    continue

                set_id = f"{GAME_ID}:{set_code}"
                sets_seen[set_code] = {
                    "id": set_id, "game_id": GAME_ID, "code": set_code,
                    "name": set_name, "released_at": None,
                    "card_count": s.get("product_count"), "icon_url": None,
                }

                # Get products for this set
                prod_resp = await client.get(f"{BASE_URL}/{TCGTRACKING_CAT}/sets/{set_tcg_id}")
                if prod_resp.status_code != 200:
                    continue
                products = prod_resp.json().get("products", [])

                for p in products:
                    name = p.get("name", "Unknown")
                    number = p.get("number") or str(p["id"])
                    card_id = f"{GAME_ID}:{set_code}:{number}"

                    # Try to build Piltover CDN URL from number
                    # TCGTracking numbers may differ from CDN codes
                    image_url = p.get("image_url")  # TCGPlayer CDN as fallback

                    cards_batch.append({
                        "id": card_id, "game_id": GAME_ID, "set_id": set_id,
                        "collector_number": number, "name_en": name,
                        "rarity": p.get("rarity"),
                        "card_type": None,
                        "subtypes": None, "colors": None, "mana_cost": None,
                        "image_url_small": image_url,
                        "image_url_normal": image_url,
                        "image_url_large": image_url,
                        "external_ids": json.dumps({"tcg_product_id": p["id"]}),
                    })
                    names_batch.append({"card_id": card_id, "locale": "en", "name": name})

                logger.info("Riftbound: %s - %d cards", set_name, len(products))

        # Insert
        async with async_session() as session:
            conn = await session.connection()
            if sets_seen:
                await conn.execute(CardSet.__table__.insert().prefix_with("OR IGNORE"), list(sets_seen.values()))
            for i in range(0, len(cards_batch), 5000):
                await conn.execute(Card.__table__.insert().prefix_with("OR IGNORE"), cards_batch[i:i+5000])
            for i in range(0, len(names_batch), 5000):
                await conn.execute(CardName.__table__.insert().prefix_with("OR IGNORE"), names_batch[i:i+5000])
            await session.commit()

        logger.info("Riftbound sync complete: %d cards, %d sets", len(cards_batch), len(sets_seen))
        return len(cards_batch)

    async def sync_prices(self, card_ids: list[str] | None = None) -> int:
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

    async def import_csv(self, csv_content: str) -> int:
        """Import cards from CSV."""
        reader = csv.DictReader(io.StringIO(csv_content))
        cards_batch = []
        names_batch = []
        sets_seen: dict[str, dict] = {}
        for row in reader:
            set_code = row.get("set_code", "base").strip()
            set_id = f"{GAME_ID}:{set_code}"
            if set_code not in sets_seen:
                sets_seen[set_code] = {"id": set_id, "game_id": GAME_ID, "code": set_code, "name": set_code.title(), "released_at": None, "card_count": None, "icon_url": None}
            collector_num = row.get("collector_number", "0").strip()
            card_id = f"{GAME_ID}:{set_code}:{collector_num}"
            name = row.get("name", "Unknown").strip()
            cards_batch.append({"id": card_id, "game_id": GAME_ID, "set_id": set_id, "collector_number": collector_num, "name_en": name, "rarity": row.get("rarity"), "card_type": row.get("card_type"), "subtypes": None, "colors": None, "mana_cost": None, "image_url_small": None, "image_url_normal": None, "image_url_large": None, "external_ids": None})
            names_batch.append({"card_id": card_id, "locale": "en", "name": name})
        async with async_session() as session:
            conn = await session.connection()
            if sets_seen:
                await conn.execute(CardSet.__table__.insert().prefix_with("OR IGNORE"), list(sets_seen.values()))
            if cards_batch:
                await conn.execute(Card.__table__.insert().prefix_with("OR IGNORE"), cards_batch)
                await conn.execute(CardName.__table__.insert().prefix_with("OR IGNORE"), names_batch)
            await session.commit()
        return len(cards_batch)
