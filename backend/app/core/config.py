"""Application configuration for the Reverie backend.

The backend is designed to be local-first. Settings are read from the
process environment and an optional `.env` file so users can tune Ollama
and generation behavior without changing code.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="REVERIE_",
        extra="ignore",
    )

    app_name: str = "Reverie Backend"
    app_version: str = "0.1.0"
    debug: bool = False

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: float = Field(default=120.0, gt=0)

    default_temperature: float = Field(default=0.75, ge=0.0, le=2.0)
    default_top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    default_num_predict: int = Field(default=512, gt=0)

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
