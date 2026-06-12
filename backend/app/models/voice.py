"""Voice profile schemas for narrator and character speech identity."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_VOICE_ID_LENGTH = 80
MAX_VOICE_NAME_LENGTH = 120
VoiceProfileType = Literal["character", "narrator"]


class VoiceProfile(BaseModel):
    """Durable voice identity used by local TTS backends.

    The schema intentionally stores reference audio and flexible metadata now so
    future zero-shot voice cloning can be added without changing callers. Task 2B
    only routes profiles to existing local TTS adapters; it does not clone voices.
    """

    model_config = ConfigDict(extra="forbid")

    voice_id: str = Field(
        ...,
        min_length=1,
        max_length=MAX_VOICE_ID_LENGTH,
        description="Stable unique identifier used by TTS adapters and assignments.",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=MAX_VOICE_NAME_LENGTH,
        description="Human-readable voice display name.",
    )
    type: VoiceProfileType = Field(
        ...,
        description="Whether this voice belongs to a character or narrator role.",
    )
    reference_audio_path: str | None = Field(
        default=None,
        description="Optional local reference audio path reserved for future cloning.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Future cloning/style metadata such as gender, accent, or provider hints.",
    )

    @field_validator("voice_id", "name")
    @classmethod
    def text_fields_must_not_be_blank(cls, value: str) -> str:
        """Normalize simple text fields and reject whitespace-only values."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("Voice profile text fields cannot be empty.")
        return stripped

    @field_validator("reference_audio_path")
    @classmethod
    def reference_audio_path_must_not_be_blank(cls, value: str | None) -> str | None:
        """Keep the cloning extension point explicit without accepting blanks."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("reference_audio_path cannot be empty.")
        return stripped
