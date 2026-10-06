from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="MARKET_HUNTER_", extra="ignore"
    )

    api_token: str | None = None
    database_path: Path = Path("data/market-hunter.db")
    request_timeout_seconds: float = Field(default=20, ge=2, le=60)
    max_results_per_source: int = Field(default=30, ge=1, le=100)
    user_agent: str = "MarketHunter/0.1 (personal deal monitor)"
    ebay_client_id: str | None = None
    ebay_client_secret: str | None = None
    ebay_marketplace_id: str = "EBAY_DE"
    api_url: str = "http://127.0.0.1:8000"
    scan_interval_seconds: int = Field(default=1800, ge=60, le=86_400)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
