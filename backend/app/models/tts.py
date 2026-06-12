"""Request and response schemas for text-to-speech generation."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_TTS_TEXT_LENGTH = 2_000
MAX_TTS_VOICE_ID_LENGTH = 80
AudioFormat = Literal["wav", "pcm", "mp3"]
TTSBackendName = Literal["orpheus", "piper"]
TTSMode = Literal["one_to_one", "rpg"]


class TTSContext(BaseModel):
    """Conversation context used to route text to an appropriate voice profile.

    The model is intentionally compact for Task 2C: it identifies whether a
    line should be treated as narrator text or character speech, the current
    conversation mode, and lightweight future emotion/prosody hints without
    applying emotional tag injection yet.
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
        description="Future emotion/prosody hint; not injected into prompts yet.",
    )
    intensity: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Future emotion intensity multiplier; reserved for Task 2D.",
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

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        """Reject whitespace-only text before it reaches a local TTS backend."""

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
