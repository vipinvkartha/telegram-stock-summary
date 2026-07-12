from functools import lru_cache
from typing import Annotated

from pydantic import BeforeValidator, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.utils.time import parse_hhmm


def _split_csv(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


CsvList = Annotated[list[str], BeforeValidator(_split_csv)]


class Settings(BaseSettings):
    app_name: str = "Telegram AI Stock Analyst"
    environment: str = "local"
    log_level: str = "INFO"
    admin_api_token: str | None = None

    database_url: str = "sqlite+aiosqlite:///./dev.db"
    auto_create_schema: bool = True

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    ai_provider: str = "gemini"
    ai_request_timeout_seconds: float = 45.0

    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    session_file: str = "telegram_stock_summarizer.session"
    telegram_session_string: str | None = None
    telegram_channels: CsvList = Field(default_factory=list)

    bot_token: str | None = None

    report_times: CsvList = Field(default_factory=lambda: ["09:00", "18:00"])
    report_timezone: str = "Europe/Berlin"
    default_report_hours: int = 12
    max_messages_per_stock: int = 80
    max_report_stocks: int = 10

    normalize_remove_emoji: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        enable_decoding=False,
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("report_times")
    @classmethod
    def validate_report_times(cls, value: list[str]) -> list[str]:
        for item in value:
            parse_hhmm(item)
        return value

    @property
    def telegram_collection_enabled(self) -> bool:
        return bool(self.telegram_api_id and self.telegram_api_hash and self.telegram_channels)

    @property
    def telegram_bot_enabled(self) -> bool:
        return bool(self.bot_token)

    @property
    def real_gemini_enabled(self) -> bool:
        return self.ai_provider.lower() == "gemini" and bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
