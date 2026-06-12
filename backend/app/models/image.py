"""Schemas for local image generation jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.tts import TTSContext

MAX_IMAGE_PROMPT_CHARS = 2400
MAX_IMAGE_NEGATIVE_PROMPT_CHARS = 1000


class ImageQualityPreset(StrEnum):
    preview_8gb = "preview_8gb"
    balanced_8gb = "balanced_8gb"
    high_8gb = "high_8gb"


class ImageJobStatus(StrEnum):
    queued = "queued"
    waiting_for_resources = "waiting_for_resources"
    paused = "paused"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ImageGenerateRequest(BaseModel):
    """Request accepted by POST /api/images/generate.

    Callers may send a simple ``prompt`` or provide richer chat/VN/memory
    ``context`` with an optional prompt-like field. ImagePromptEngine turns both
    shapes into a deterministic, bounded ComfyUI-ready prompt.
    """

    prompt: str | None = Field(
        default=None, min_length=1, max_length=MAX_IMAGE_PROMPT_CHARS
    )
    negative_prompt: str | None = Field(
        default=None, max_length=MAX_IMAGE_NEGATIVE_PROMPT_CHARS
    )
    context: dict[str, Any] | TTSContext | None = Field(
        default=None,
        description="Compact TTSContext-style or full chat/VN/memory metadata for deterministic prompt enrichment.",
    )
    quality_preset: ImageQualityPreset = ImageQualityPreset.preview_8gb

    @model_validator(mode="after")
    def require_prompt_or_context(self) -> "ImageGenerateRequest":
        if self.prompt is None and self.context is None:
            raise ValueError("Image generation requires either prompt or context.")
        return self

    @field_validator("prompt", "negative_prompt")
    @classmethod
    def optional_prompt_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("Image prompt field cannot be empty.")
        return value.strip()


class ImageJobRead(BaseModel):
    """Public image job state for route responses and SSE events."""

    job_id: str
    status: ImageJobStatus
    prompt: str
    original_prompt: str | None = None
    negative_prompt: str | None = None
    prompt_metadata: dict[str, Any] = Field(default_factory=dict)
    requested_preset: ImageQualityPreset
    active_preset: ImageQualityPreset
    created_at: datetime
    updated_at: datetime
    progress: float = Field(ge=0.0, le=1.0)
    phase: str
    message: str
    output_paths: list[str] = Field(default_factory=list)
    error: dict[str, Any] | None = None
    fallback_used: bool = False
    resource_mode: str = "queued"
    vram_free_mb: int | None = None
    vram_required_mb: int | None = None


class ImageGenerateResponse(BaseModel):
    request_id: str
    job: ImageJobRead


class ImageJobEvent(BaseModel):
    event: str
    job_id: str
    sequence: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: ImageJobStatus
    phase: str
    progress: float = Field(ge=0.0, le=1.0)
    message: str
    resource_mode: str = "queued"
    output_paths: list[str] = Field(default_factory=list)
    error: dict[str, Any] | None = None
    fallback_used: bool = False
    vram_free_mb: int | None = None
    vram_required_mb: int | None = None
