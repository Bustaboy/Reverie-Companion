"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the Reverie backend.

    Defaults are intentionally local-first and conservative so the backend can
    run offline after the user has installed Ollama and downloaded a model.
    """

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = Field(default="Reverie Backend", description="API display name.")
    app_version: str = Field(default="0.1.0", description="Backend version.")
    api_prefix: str = Field(default="", description="Optional API route prefix.")

    ollama_host: str = Field(
        default="http://localhost:11434",
        description="Base URL for the local Ollama server.",
    )
    ollama_model: str = Field(
        default="llama3.1:8b",
        description="Default local Ollama model used for chat generation.",
    )
    ollama_temperature: float = Field(
        default=0.8,
        ge=0.0,
        le=2.0,
        description="Default creativity level for generated responses.",
    )
    ollama_top_p: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Default nucleus sampling value for generated responses.",
    )
    ollama_num_ctx: int = Field(
        default=8192,
        ge=1024,
        description="Default context window requested from Ollama.",
    )
    request_timeout_seconds: float = Field(
        default=120.0,
        gt=0.0,
        description="HTTP timeout for Ollama requests.",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings so configuration is parsed once per process."""
    return Settings()
