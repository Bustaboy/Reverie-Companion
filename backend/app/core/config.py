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

    # Personal LoRA is an explicit, local-only advanced growth feature. The
    # foundation stores reviewable examples and training manifests, but keeps
    # collection and training disabled until the user opts in. Defaults are
    # intentionally conservative for 8GB GPUs: rank 8, batch size 1, short
    # sequence length, and one low-priority background job at a time.
    personal_lora_enabled: bool = True
    personal_lora_data_path: str = "./data/personal_lora"
    personal_lora_rank: int = Field(default=8, ge=8, le=16)
    personal_lora_max_rank: int = Field(default=16, ge=8, le=16)
    personal_lora_min_confidence: float = Field(default=0.68, ge=0.0, le=1.0)
    personal_lora_min_evidence_count: int = Field(default=2, gt=0, le=20)
    personal_lora_max_example_chars: int = Field(default=1600, gt=200, le=4000)
    personal_lora_max_examples_per_job: int = Field(default=128, gt=0, le=512)

    # TTS defaults are local-first and 8GB-aware. Orpheus TTS 3B is the
    # primary high-quality emotional backend and is loaded lazily with 4-bit
    # quantization by default; Piper stays available as a fast CPU fallback.
    tts_enabled: bool = True
    tts_primary_backend: str = Field(default="orpheus", pattern="^(orpheus|piper)$")
    tts_orpheus_model_id: str = "canopylabs/orpheus-3b-0.1-ft"
    tts_orpheus_model_path: str | None = None
    tts_orpheus_timeout_seconds: float = Field(default=20.0, gt=0)
    tts_piper_binary_path: str | None = None
    tts_piper_voice_dir: str = "./models/piper"
    tts_piper_model_path: str | None = None
    tts_piper_timeout_seconds: float = Field(default=8.0, gt=0)
    tts_device: str = Field(default="auto", pattern="^(auto|cuda|cpu)$")
    tts_quantization: str = Field(default="4bit", pattern="^(4bit|8bit|none)$")
    tts_min_free_vram_mb: int = Field(default=3600, ge=0, le=8192)
    tts_default_voice_id: str = "reverie_default"
    voice_profile_store_path: str = "./data/voices/voice_profiles.json"
    voice_reference_audio_dir: str = "./data/voices/reference_audio"
    voice_reference_audio_max_mb: int = Field(default=25, gt=0, le=100)
    voice_default_narrator_voice_id: str = "reverie_default"
    voice_default_character_voice_behavior: str = Field(
        default="narrator",
        pattern="^(narrator|none)$",
        description=(
            "Fallback for characters without an assigned voice. 'narrator' uses "
            "the default narrator profile; 'none' requires explicit assignment."
        ),
    )
    tts_sample_rate: int = Field(default=24000, gt=0)
    tts_max_text_chars: int = Field(default=2000, gt=0, le=8000)
    tts_stream_chunk_size_bytes: int = Field(default=64_000, gt=0, le=1_000_000)

    # Image generation is a queued, low-priority media workload. Defaults target
    # RTX 4070 8GB laptops: ComfyUI must run in lowvram mode with Flux GGUF,
    # batch size 1, conservative resolutions, and TTS always preempts images.
    image_generation_enabled: bool = True
    image_generation_comfyui_url: str = "http://127.0.0.1:8188"
    image_generation_output_dir: str = "./data/images/generated"
    image_generation_history_path: str = "./data/images/history.json"
    character_assets_dir: str = "./data/characters"
    image_generation_default_preset: str = Field(
        default="preview_8gb", pattern="^(preview_8gb|balanced_8gb|high_8gb)$"
    )
    image_generation_min_free_vram_mb: int = Field(default=2800, ge=0, le=8192)
    image_generation_resume_poll_seconds: float = Field(default=2.0, gt=0, le=30)
    image_generation_comfy_timeout_seconds: float = Field(default=600.0, gt=1)
    image_generation_max_queue_size: int = Field(default=8, gt=0, le=100)
    image_generation_cpu_fallback: bool = True
    image_generation_allow_unknown_vram: bool = True


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
