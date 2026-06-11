"""Application configuration for the Reverie backend.

The backend is designed to be local-first. Settings are read from the
process environment and an optional `.env` file so users can tune Ollama,
logging, and generation behavior without changing code.
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
    log_level: str = "INFO"

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: float = Field(default=120.0, gt=0)

    default_temperature: float = Field(default=0.75, ge=0.0, le=2.0)
    default_top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    default_num_predict: int = Field(default=512, gt=0)

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # Long-term memory defaults are local-first and conservative for 8GB systems.
    # The hot path uses one Ollama embedding call plus embedded LanceDB search;
    # mem0 extraction is best-effort and can be disabled without losing direct
    # LanceDB recall.
    memory_enabled: bool = True
    memory_db_path: str = "./data/memory"
    memory_store_provider: str = "reverie_lancedb"
    memory_collection_name: str = "reverie_memories"
    memory_default_user_id: str = "local_user"
    memory_default_session_id: str | None = None
    memory_embedding_model: str = "nomic-embed-text"
    memory_embedding_dimensions: int = Field(default=768, gt=0)
    memory_llm_model: str | None = None
    memory_extraction_temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    memory_add_infer: bool = True
    memory_search_min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    memory_max_memory_chars: int = Field(default=4000, gt=500, le=20000)
    memory_max_context_memories: int = Field(default=6, gt=0, le=20)
    memory_context_max_chars: int = Field(default=4000, gt=500, le=20000)
    memory_mem0_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
