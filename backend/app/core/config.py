from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.pricing import DEFAULT_PRICES, ModelPrice


class Settings(BaseSettings):
    """App configuration, read from environment variables or a .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI"

    llm_provider: Literal["openai", "fake"] = "openai"
    llm_model: str = "gpt-5.5"
    # None = provider default; not every model accepts a temperature
    llm_temperature: float | None = Field(default=None, ge=0, le=2)
    openai_api_key: str | None = None
    system_prompt: str = "You are a helpful assistant."
    # Per-model prices (USD per 1M tokens) merged over DEFAULT_PRICES, as JSON in .env
    llm_prices: dict[str, ModelPrice] = {}
    # Fixed exchange rate for showing costs in CHF (OpenAI bills in USD); update occasionally
    usd_to_chf: float = Field(default=0.80, gt=0)

    auth_enabled: bool = False

    @property
    def model_prices(self) -> dict[str, ModelPrice]:
        return {**DEFAULT_PRICES, **self.llm_prices}


@lru_cache
def get_settings() -> Settings:
    return Settings()
