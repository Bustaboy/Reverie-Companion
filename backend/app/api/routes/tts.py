"""Text-to-speech API routes for local voice generation."""

from __future__ import annotations

import logging
from typing import Annotated, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.models.tts import TTSGenerateRequest, TTSGenerateResponse
from app.services.tts_service import TTSGenerationResult, TTSService, TTSServiceError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tts", tags=["tts"])


def get_tts_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> TTSService:
    """Provide the local-first TTS service for request handlers."""

    return TTSService(settings=settings)


@router.post("/generate", response_model=None)
async def generate_tts(
    request: TTSGenerateRequest,
    tts_service: Annotated[TTSService, Depends(get_tts_service)],
) -> TTSGenerateResponse | StreamingResponse:
    """Generate speech using Orpheus first, then Piper when needed."""

    request_id = str(uuid4())
    logger.info(
        "Received TTS generation request",
        extra={
            "request_id": request_id,
            "voice_id": request.voice_id,
            "stream": request.stream,
            "text_chars": len(request.text),
        },
    )
    try:
        result_or_stream = await tts_service.generate_speech(
            text=request.text,
            voice_id=request.voice_id,
            stream=request.stream,
            request_id=request_id,
        )
    except TTSServiceError as exc:
        logger.warning(
            "TTS request failed",
            extra={
                "request_id": request_id,
                "code": exc.code,
                "retryable": exc.retryable,
            },
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "retryable": exc.retryable,
                },
                "request_id": request_id,
            },
        ) from exc

    if request.stream:
        return StreamingResponse(
            result_or_stream,  # type: ignore[arg-type]
            media_type="audio/wav",
            headers={
                "Cache-Control": "no-cache",
                "X-Request-ID": request_id,
            },
        )

    result = cast(TTSGenerationResult, result_or_stream)
    return TTSGenerateResponse(
        audio_base64=result.as_base64(),
        format=result.format,
        voice_id=result.voice_id,
        engine=result.engine,
        sample_rate=result.sample_rate,
        duration_ms=result.duration_ms,
        fallback_used=result.fallback_used,
        request_id=request_id,
    )
