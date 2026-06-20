from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CardResult:
    card_id: str
    name: str
    set_code: str
    collector_number: str
    image_url: str | None = None


class BaseAdapter(ABC):
    """Abstract interface all game adapters must implement."""

    game_id: str

    @abstractmethod
    async def sync_cards(self, sets: list[str] | None = None) -> int:
        """Sync card catalog from external source. Returns count of cards synced."""
        ...

    @abstractmethod
    async def sync_prices(self, card_ids: list[str] | None = None) -> int:
        """Sync price data. Returns count of price records created."""
        ...

    @abstractmethod
    async def search(self, query: str, locale: str = "en") -> list[CardResult]:
        """Search cards by name in the external API."""
        ...

    @abstractmethod
    async def get_card_image_url(self, card_id: str, size: str = "small") -> str | None:
        """Return image URL for a card."""
        ...
