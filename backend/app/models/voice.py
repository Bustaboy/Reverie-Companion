"""Schemas for durable local voice profiles."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

MAX_VOICE_ID_LENGTH = 80
MAX_VOICE_NAME_LENGTH = 120
MAX_REFERENCE_AUDIO_PATH_LENGTH = 500
VoiceProfileType = Literal["character", "narrator"]


class VoiceMoodSettings(BaseModel):
    """Per-character speech mood controls stored with durable voice profiles.

    The values are intentionally small scalar knobs so the UI can fine-tune
    deterministic emotion tagging without loading extra models or increasing
    8GB memory pressure. ``1.0`` means neutral/default behavior.
    """

    baseline_expressiveness: float = Field(
        default=1.0, ge=0.0, le=2.0, description="Default prosody warmth."
    )
    emotional_sensitivity: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="How quickly emotional cues boost intensity.",
    )
    nsfw_intensity: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="How strongly intimate scene cues affect speech.",
    )


class VoiceProfile(BaseModel):
    """Durable voice profile used by TTS and future voice cloning.

    `reference_audio_path` and `metadata` are intentionally stored now so a
    later zero-shot cloning adapter can use the same profile records without a
    schema rewrite. No cloning work is performed in this milestone.
    """

    voice_id: str = Field(..., min_length=1, max_length=MAX_VOICE_ID_LENGTH)
    name: str = Field(..., min_length=1, max_length=MAX_VOICE_NAME_LENGTH)
    type: VoiceProfileType
    reference_audio_path: str | None = Field(
        default=None, max_length=MAX_REFERENCE_AUDIO_PATH_LENGTH
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    mood_settings: VoiceMoodSettings = Field(default_factory=VoiceMoodSettings)

    @field_validator("voice_id", "name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """Normalize identifiers and display names without allowing blanks."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("value cannot be empty.")
        return stripped

    @field_validator("reference_audio_path")
    @classmethod
    def normalize_reference_audio_path(cls, value: str | None) -> str | None:
        """Store a clean future cloning reference path when one is provided."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        if "\x00" in stripped:
            raise ValueError("reference_audio_path cannot contain null bytes.")
        return stripped


class VoiceProfileUpdate(BaseModel):
    """Partial update payload for voice profile CRUD operations."""

    name: str | None = Field(
        default=None, min_length=1, max_length=MAX_VOICE_NAME_LENGTH
    )
    type: VoiceProfileType | None = None
    reference_audio_path: str | None = Field(
        default=None, max_length=MAX_REFERENCE_AUDIO_PATH_LENGTH
    )
    metadata: dict[str, Any] | None = None
    mood_settings: VoiceMoodSettings | None = None

    @field_validator("name")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("name cannot be empty.")
        return stripped

    @field_validator("reference_audio_path")
    @classmethod
    def normalize_optional_reference_audio_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        if "\x00" in stripped:
            raise ValueError("reference_audio_path cannot contain null bytes.")
        return stripped
