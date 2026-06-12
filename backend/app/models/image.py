"""Schemas for local-first in-chat image generation jobs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ImageQualityPreset = Literal["preview_8gb", "balanced_8gb", "high_8gb"]
ImageJobStatus = Literal[
    "queued",
    "waiting_resources",
    "paused",
    "running",
    "completed",
    "failed",
    "cancelled",
]


class ImageGenerationContext(BaseModel):
    """Compact scene/TTS-style context for later prompt enrichment tasks.

    Task 3A deliberately avoids advanced prompt engineering. The context is
    still structured now so future chat, VN, memory, and Futa-Vision scene data
    can flow through the same API without becoming opaque prompt blobs.
    """

    character_id: str | None = Field(default=None, min_length=1, max_length=120)
    mode: str | None = Field(default=None, max_length=40)
    scene: str | None = Field(default=None, max_length=800)
    emotion_hint: str | None = Field(default=None, max_length=80)
    scene_tags: list[str] = Field(default_factory=list, max_length=16)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("character_id", "mode", "scene", "emotion_hint")
    @classmethod
    def optional_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("context field cannot be empty.")
        return value.strip() if value is not None else value


class ImageGenerateRequest(BaseModel):
    """Payload accepted by POST /api/images/generate."""

    prompt: str = Field(..., min_length=1, max_length=2000)
    context: ImageGenerationContext | dict[str, Any] | None = Field(default=None)
    quality_preset: ImageQualityPreset = Field(default="preview_8gb")

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("prompt cannot be empty.")
        return value.strip()


class ImageJobRead(BaseModel):
    """User-facing image generation job state."""

    job_id: str
    status: ImageJobStatus
    requested_preset: ImageQualityPreset
    effective_preset: ImageQualityPreset
    progress: float = Field(ge=0.0, le=1.0)
    phase: str
    message: str
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None
    paused_reason: str | None = None
    resource_mode: str = "queued"
    output_paths: list[str] = Field(default_factory=list)
    error: dict[str, Any] | None = None


class ImageGenerateResponse(BaseModel):
    """Response returned after a generation request is queued."""

    job: ImageJobRead


class ImageJobEvent(BaseModel):
    """Structured SSE payload for image job progress."""

    event: str
    job_id: str
    sequence: int
    timestamp: str
    status: ImageJobStatus
    phase: str
    progress: float = Field(ge=0.0, le=1.0)
    message: str
    resource_mode: str
    effective_preset: ImageQualityPreset
    paused_reason: str | None = None
    output_paths: list[str] = Field(default_factory=list)
    error: dict[str, Any] | None = None
