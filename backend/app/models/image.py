"""Schemas for local image generation jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.tts import TTSContext

MAX_IMAGE_PROMPT_CHARS = 1200
MAX_IMAGE_NEGATIVE_PROMPT_CHARS = 1200


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
    """Request accepted by POST /api/images/generate."""

    prompt: str = Field(..., min_length=1, max_length=MAX_IMAGE_PROMPT_CHARS)
    context: dict[str, Any] | TTSContext | None = Field(
        default=None,
        description="Compact TTSContext-style or scene metadata for deterministic prompt enrichment.",
    )
    negative_prompt: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_IMAGE_NEGATIVE_PROMPT_CHARS,
        description="Optional negative prompt merged with Reverie safety/quality negatives.",
    )
    quality_preset: ImageQualityPreset = ImageQualityPreset.preview_8gb

    @field_validator("prompt", "negative_prompt")
    @classmethod
    def prompt_must_not_be_blank(cls, value: str) -> str:
        if value is not None and not value.strip():
            raise ValueError("Image prompt cannot be empty.")
        return value.strip() if value is not None else value


class ImageJobRead(BaseModel):
    """Public image job state for route responses and SSE events."""

    job_id: str
    status: ImageJobStatus
    prompt: str
    negative_prompt: str
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
