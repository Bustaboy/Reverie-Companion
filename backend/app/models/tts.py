"""Pydantic schemas for local text-to-speech generation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, constr


class TTSGenerateRequest(BaseModel):
    """Client request for generating companion speech from text."""

    text: constr(strip_whitespace=True, min_length=1, max_length=4000)
    voice_id: constr(strip_whitespace=True, min_length=1, max_length=128) = "default"
    stream: bool = False
    format: Literal["wav"] = "wav"


class TTSGenerateResponse(BaseModel):
    """Base64 response for non-streamed speech generation."""

    audio_base64: str
    format: Literal["wav"] = "wav"
    voice_id: str
    engine: Literal["orpheus", "piper"]
    sample_rate: int | None = None
    duration_ms: int | None = None
    fallback_used: bool = False
    request_id: str
