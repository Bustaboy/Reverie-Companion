"""Schemas for local 8GB resource status and recommendations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class VRAMStatus(BaseModel):
    free_mb: int | None = None
    total_mb: int | None = None
    used_mb: int | None = None
    source: str


class ResourceStatusResponse(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pressure: Literal["unknown", "normal", "elevated", "high", "critical"]
    message: str
    vram: VRAMStatus
    active_tts: bool
    active_image_jobs: int
    can_start_optional_gpu_work: bool
    should_downgrade: bool
    should_unload_optional_models: bool
    recommended_image_preset: Literal["preview_8gb", "balanced_8gb", "high_8gb"]
    recommended_tts_backend: Literal["orpheus", "piper"]
    notes: list[str] = Field(default_factory=list)
