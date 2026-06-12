"""Request and response schemas for text-to-speech generation."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_TTS_TEXT_LENGTH = 2_000
MAX_TTS_VOICE_ID_LENGTH = 80
MAX_TTS_READY_TEXT_LENGTH = 2_400
AudioFormat = Literal["wav", "pcm", "mp3"]
TTSBackendName = Literal["orpheus", "piper"]
TTSMode = Literal["one_to_one", "rpg"]


class TTSMoodSettings(BaseModel):
    """Per-character voice mood/fine-tuning controls for lightweight emotion routing."""

    baseline_expressiveness: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="How expressive this character should sound before scene boosts.",
    )
    emotional_sensitivity: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="How strongly memories, growth cues, and recent messages affect emotion.",
    )
    nsfw_intensity: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="How strongly intimate scene cues may boost TTS prosody.",
    )


class TTSEmotionMetadata(BaseModel):
    """Deterministic emotion/prosody metadata shared by chat and TTS."""

    scene: str
    intensity: float = Field(ge=0.0, le=2.0)
    tags: list[str] = Field(default_factory=list, max_length=8)
    is_high_emotion: bool = False
    is_intimate: bool = False
    cues: list[str] = Field(default_factory=list, max_length=12)
    visible_text_stripped: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)


class TTSContext(BaseModel):
    """Conversation context used to route text to an appropriate voice profile.

    The model is intentionally compact: it identifies whether a line should be
    treated as narrator text or character speech, the current conversation mode,
    and lightweight emotion/prosody hints used by deterministic tag injection.
    """

    character_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        description="Character ID associated with this line when known.",
    )
    is_narration: bool = Field(
        default=False,
        description="Explicitly route this line through the narrator voice.",
    )
    mode: TTSMode = Field(
        default="one_to_one",
        description="Conversation mode used by context-aware TTS routing.",
    )
    emotion_hint: str | None = Field(
        default=None,
        min_length=1,
        max_length=80,
        description="Lightweight emotion/prosody hint for deterministic tag injection.",
    )
    intensity: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Emotion intensity multiplier for deterministic TTS tag injection.",
    )
    mood_settings: TTSMoodSettings = Field(
        default_factory=TTSMoodSettings,
        description="Per-character mood/fine-tuning controls resolved from the linked VoiceProfile.",
    )
    scene_tags: list[str] = Field(
        default_factory=list,
        max_length=12,
        description="Lightweight current-scene tags from VN, memory, or growth routing.",
    )

    @field_validator("character_id", "emotion_hint")
    @classmethod
    def optional_context_text_must_not_be_blank(cls, value: str | None) -> str | None:
        """Normalize optional context fields without accepting blank strings."""

        if value is not None and not value.strip():
            raise ValueError("context field cannot be empty.")
        return value.strip() if value is not None else value


class TTSGenerateRequest(BaseModel):
    """Payload accepted by the TTS generation endpoint."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TTS_TEXT_LENGTH,
        description="Text to synthesize into speech.",
    )
    voice_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_TTS_VOICE_ID_LENGTH,
        description="Durable voice profile identifier to use for synthesis.",
    )
    character_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        description="Legacy character ID used to resolve an assigned voice profile.",
    )
    context: TTSContext | None = Field(
        default=None,
        description="Full context used for narration/character voice routing.",
    )
    tts_text: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_TTS_READY_TEXT_LENGTH,
        description=(
            "Optional pre-tagged speech text from chat; never shown as visible chat text."
        ),
    )
    emotion: TTSEmotionMetadata | None = Field(
        default=None,
        description="Optional deterministic emotion metadata from the chat pipeline.",
    )
    stream: bool = Field(
        default=False,
        description="Return audio bytes directly instead of a base64 JSON payload.",
    )
    audio_format: AudioFormat = Field(
        default="wav", description="Requested output container when supported."
    )

    @model_validator(mode="after")
    def merge_legacy_character_id_into_context(self) -> "TTSGenerateRequest":
        """Keep Task 2A/2B clients working while enabling full TTSContext calls."""

        if self.context is None:
            self.context = TTSContext(character_id=self.character_id)
        elif self.character_id is not None and self.context.character_id is None:
            self.context = self.context.model_copy(
                update={"character_id": self.character_id}
            )
        return self

    @field_validator("text", "tts_text")
    @classmethod
    def text_must_not_be_blank(cls, value: str | None) -> str | None:
        """Reject whitespace-only text before it reaches a local TTS backend."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("TTS text cannot be empty.")
        return value.strip()

    @field_validator("voice_id", "character_id")
    @classmethod
    def optional_identifier_must_not_be_blank(cls, value: str | None) -> str | None:
        """Reject blank optional IDs while still allowing profile fallback."""

        if value is not None and not value.strip():
            raise ValueError("identifier cannot be empty.")
        return value.strip() if value is not None else value


class TTSGenerateResponse(BaseModel):
    """Non-streaming TTS response with inline audio for simple clients."""

    request_id: str
    backend: TTSBackendName
    voice_id: str
    audio_format: AudioFormat
    audio_base64: str
    sample_rate: int
    duration_seconds: float | None = None
    fallback_used: bool = False
