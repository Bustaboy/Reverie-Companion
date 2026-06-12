"""Schemas for durable local voice profiles."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

MAX_VOICE_ID_LENGTH = 80
MAX_VOICE_NAME_LENGTH = 120
MAX_REFERENCE_AUDIO_PATH_LENGTH = 500
VoiceProfileType = Literal["character", "narrator"]


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

class VoiceCloneRequest(BaseModel):
    """Create a local zero-shot voice profile from short reference audio."""

    name: str = Field(..., min_length=1, max_length=MAX_VOICE_NAME_LENGTH)
    audio_base64: str = Field(..., min_length=1)
    mime_type: str = Field(default="audio/wav", max_length=120)
    character_id: str | None = Field(default=None, min_length=1, max_length=120)
    duration_seconds: float | None = Field(default=None, ge=0.0, le=60.0)

    @field_validator("name", "mime_type", "character_id")
    @classmethod
    def strip_clone_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("value cannot be empty.")
        if "\x00" in stripped:
            raise ValueError("value cannot contain null bytes.")
        return stripped


class VoiceCloneResponse(BaseModel):
    """Voice profile returned after storing reference audio locally."""

    profile: VoiceProfile
    assigned_character_id: str | None = None
    cloning_backend: str = "orpheus_zero_shot"
    message: str
