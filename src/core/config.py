from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "production"] = "development"

    # Database
    database_url: str = "postgresql+asyncpg://daijoubu:dev_password@localhost:5432/daijoubu"

    # Discord
    discord_bot_token: str = ""
    discord_guild_id: str | None = None

    # OpenAI
    openai_api_key: str = ""

    # AI Model settings
    embedding_model: str = "text-embedding-3-small"
    classification_model: str = "gpt-4.1-nano"
    summary_model: str = "gpt-4.1-mini"
    vision_model: str = "gpt-4.1-mini"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
