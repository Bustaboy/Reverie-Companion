"""Request and response schemas for text-to-speech generation."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_TTS_TEXT_LENGTH = 2_000
MAX_TTS_VOICE_ID_LENGTH = 80
MAX_TTS_CHARACTER_ID_LENGTH = 120
MAX_TTS_EMOTION_HINT_LENGTH = 80
AudioFormat = Literal["wav", "pcm", "mp3"]
TTSBackendName = Literal["orpheus", "piper"]
TTSMode = Literal["one_to_one", "rpg"]


class TTSContext(BaseModel):
    """Conversation-aware routing context for TTS voice selection.

    The context is intentionally compact so chat, VN, and RPG clients can pass
    it through without coupling the TTS layer to their full state objects.
    Emotion and intensity are accepted for forward compatibility; Task 2C only
    routes voices and does not inject prosody or emotion tags.
    """

    character_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_TTS_CHARACTER_ID_LENGTH,
        description="Optional speaking character ID from the current chat/VN state.",
    )
    is_narration: bool = Field(
        default=False,
        description="Explicit narration flag. Narration routes to narrator voices.",
    )
    mode: TTSMode = Field(
        default="one_to_one",
        description="Conversation mode used by the routing heuristic.",
    )
    emotion_hint: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_TTS_EMOTION_HINT_LENGTH,
        description="Optional future prosody hint; stored but not applied in Task 2C.",
    )
    intensity: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Future emotion/prosody intensity multiplier.",
    )

    @field_validator("character_id", "emotion_hint")
    @classmethod
    def optional_context_text_must_not_be_blank(cls, value: str | None) -> str | None:
        """Reject blank optional context fields while normalizing whitespace."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("context value cannot be empty.")
        return stripped


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
        max_length=MAX_TTS_CHARACTER_ID_LENGTH,
        description=(
            "Legacy optional character ID used to resolve an assigned voice profile. "
            "Prefer context.character_id for new clients."
        ),
    )
    context: TTSContext | None = Field(
        default=None,
        description="Conversation-aware routing context from chat or VN state.",
    )
    stream: bool = Field(
        default=False,
        description="Return audio bytes directly instead of a base64 JSON payload.",
    )
    audio_format: AudioFormat = Field(
        default="wav", description="Requested output container when supported."
    )

    @model_validator(mode="after")
    def normalize_legacy_context(self) -> "TTSGenerateRequest":
        """Promote legacy character_id into context for router consistency."""

        if self.context is None and self.character_id is not None:
            self.context = TTSContext(character_id=self.character_id)
        elif (
            self.context is not None
            and self.context.character_id is None
            and self.character_id is not None
        ):
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
