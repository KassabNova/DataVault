from importlib import import_module

from app.adapters.base import BaseAdapter

_registry: dict[str, BaseAdapter] = {}

ADAPTER_MODULES = {
    "mtg": "app.adapters.mtg",
    "pokemon": "app.adapters.pokemon",
    "lorcana": "app.adapters.lorcana",
    "fab": "app.adapters.fab",
    "riftbound": "app.adapters.riftbound",
    "yugioh": "app.adapters.yugioh",
    "swu": "app.adapters.swu",
    "onepiece": "app.adapters.onepiece",
}


def get_adapter(game_id: str) -> BaseAdapter:
    """Get an adapter instance by game_id. Lazy-loads on first access."""
    if game_id not in _registry:
        module_path = ADAPTER_MODULES.get(game_id)
        if not module_path:
            raise ValueError(f"No adapter registered for game: {game_id}")
        module = import_module(module_path)
        adapter_cls = getattr(module, "Adapter")
        _registry[game_id] = adapter_cls()
    return _registry[game_id]


def list_adapters() -> list[str]:
    """Return all registered game_ids."""
    return list(ADAPTER_MODULES.keys())
