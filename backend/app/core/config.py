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

    # Reflection/journaling stays lightweight by default: chat can read compact
    # recent journal insights, while new reflections run as throttled background
    # work so local LLM responsiveness remains the priority on 8GB systems.
    reflection_enabled: bool = True
    reflection_frequency: str = Field(
        default="balanced",
        pattern="^(low|balanced|high)$",
        description=(
            "User-facing reflection cadence. Low waits longer between journal "
            "passes, balanced is conservative by default, and high reflects more "
            "readily while still throttling background work."
        ),
    )
    reflection_sensitivity: str = Field(
        default="balanced",
        pattern="^(conservative|balanced|responsive)$",
        description=(
            "How readily meaningful cues trigger reflection. Conservative favors "
            "explicit remember/learn requests and scheduled intervals; responsive "
            "also reacts to softer emotional and continuity cues."
        ),
    )
    reflection_user_message_interval: int = Field(default=6, gt=0, le=100)
    reflection_min_interval_seconds: float = Field(default=180.0, ge=0.0)
    reflection_min_user_messages: int = Field(default=2, gt=0, le=20)
    reflection_history_message_limit: int = Field(default=12, gt=0, le=50)
    reflection_context_entry_limit: int = Field(default=5, gt=0, le=20)
    reflection_context_max_chars: int = Field(default=1600, gt=200, le=8000)

    # Growth notifications are rare, privacy-safe UI whispers surfaced from
    # journal entries on later turns. Timing has three gates: enough user turns
    # have happened, the current turn lands on a coarse message interval, and
    # enough wall-clock time has passed since the last visible notice. They do
    # not trigger extra model calls.
    growth_notifications_enabled: bool = True
    growth_notification_min_user_messages: int = Field(default=6, gt=0, le=100)
    growth_notification_message_interval: int = Field(default=6, gt=0, le=100)
    growth_notification_min_interval_seconds: float = Field(default=900.0, ge=0.0)
    growth_notification_min_confidence: float = Field(default=0.62, ge=0.0, le=1.0)
    growth_notification_min_evidence_count: int = Field(default=2, gt=0, le=20)
    growth_notification_style: str = "whisper"


    # Personal LoRA is explicit, local, and disabled by default. Dataset
    # collection only creates reviewable candidates; adapter training requires
    # approved examples and runs outside the interactive chat path. Defaults use
    # tiny rank and micro-batches for RTX 4070 8GB-class systems.
    personal_lora_enabled: bool = False
    personal_lora_collect_examples: bool = False
    personal_lora_default_character_id: str = "default_companion"
    personal_lora_rank: int = Field(default=8, ge=1, le=16)
    personal_lora_max_rank: int = Field(default=16, ge=1, le=16)
    personal_lora_alpha: int = Field(default=16, ge=1, le=64)
    personal_lora_learning_rate: float = Field(default=1e-4, gt=0.0, le=1e-3)
    personal_lora_max_steps: int = Field(default=120, gt=0, le=1000)
    personal_lora_micro_batch_size: int = Field(default=1, ge=1, le=2)
    personal_lora_gradient_accumulation_steps: int = Field(default=8, ge=1, le=64)
    personal_lora_checkpoint_every_steps: int = Field(default=30, ge=1, le=500)
    personal_lora_min_confidence: float = Field(default=0.72, ge=0.0, le=1.0)
    personal_lora_min_evidence_count: int = Field(default=2, gt=0, le=20)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
