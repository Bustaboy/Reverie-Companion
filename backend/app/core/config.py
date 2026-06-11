"""Application configuration for the Reverie backend.

The backend is designed to be local-first. Settings are read from the
process environment and an optional `.env` file so users can tune Ollama,
logging, and generation behavior without changing code.
"""

from functools import lru_cache
from pathlib import Path

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
    log_level: str = "INFO"

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: float = Field(default=120.0, gt=0)

    default_temperature: float = Field(default=0.75, ge=0.0, le=2.0)
    default_top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    default_num_predict: int = Field(default=512, gt=0)

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    data_dir: Path = Path("./data")

    memory_enabled: bool = True
    memory_store_provider: str = "lancedb"
    memory_collection_name: str = "reverie_memories"
    memory_default_user_id: str = "local_user"
    memory_default_session_id: str = "default_session"
    memory_embedding_model: str = "nomic-embed-text"
    memory_embedding_dims: int = Field(default=768, gt=0)
    memory_llm_model: str | None = None
    memory_extraction_temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    memory_add_infer: bool = True
    memory_search_threshold: float = Field(default=0.1, ge=0.0, le=1.0)
    memory_context_limit: int = Field(default=6, gt=0, le=20)
    memory_context_max_chars: int = Field(default=4_000, gt=500, le=20_000)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
