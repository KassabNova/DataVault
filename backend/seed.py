"""Seed the database with initial game entries."""
import asyncio

from sqlalchemy import select

from app.database import async_session, engine, Base
from app.models.game import Game

GAMES = [
    {"id": "mtg", "name": "Magic: The Gathering"},
    {"id": "pokemon", "name": "Pokémon TCG"},
    {"id": "lorcana", "name": "Disney Lorcana"},
    {"id": "fab", "name": "Flesh and Blood"},
    {"id": "riftbound", "name": "Riftbound"},
    {"id": "yugioh", "name": "Yu-Gi-Oh!"},
    {"id": "swu", "name": "Star Wars Unlimited"},
    {"id": "onepiece", "name": "One Piece TCG"},
]


async def seed():
    async with async_session() as session:
        existing = (await session.execute(select(Game))).scalars().all()
        if existing:
            print(f"Already seeded ({len(existing)} games). Skipping.")
            return
        for g in GAMES:
            session.add(Game(**g))
        await session.commit()
        print(f"Seeded {len(GAMES)} games.")


if __name__ == "__main__":
    asyncio.run(seed())
