"""
Application configuration — loaded from environment / .env file.
"""
from __future__ import annotations

import json
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    openai_api_key: str = "sk-placeholder"
    openai_base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4o-mini"

    # Telegram
    telegram_bot_token: str = ""
    telegram_agent_id: str = ""

    # App
    database_url: str = "sqlite:///./yuno_platform.db"
    chroma_persist_dir: str = "./chroma_data"
    secret_key: str = "change_me"
    backend_cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    log_level: str = "INFO"

    @property
    def cors_origins(self) -> List[str]:
        return self.backend_cors_origins


settings = Settings()
