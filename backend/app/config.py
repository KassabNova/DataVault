from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./data/store.db"
    default_locale: str = "es"
    currency: str = "MXN"
    usd_to_mxn: float = 17.5
    sync_schedule_hours: int = 6

    class Config:
        env_prefix = "TCG_"


settings = Settings()
