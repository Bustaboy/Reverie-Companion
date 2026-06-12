"""Request and response schemas for text-to-speech generation."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAX_TTS_TEXT_LENGTH = 2_000
MAX_TTS_VOICE_ID_LENGTH = 80
AudioFormat = Literal["wav", "pcm", "mp3"]
TTSBackendName = Literal["orpheus", "piper"]


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
        description="Optional character ID used to resolve an assigned voice profile.",
    )
    stream: bool = Field(
        default=False,
        description="Return audio bytes directly instead of a base64 JSON payload.",
    )
    audio_format: AudioFormat = Field(
        default="wav", description="Requested output container when supported."
    )

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
