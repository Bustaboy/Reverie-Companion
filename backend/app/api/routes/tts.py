"""Text-to-speech API routes."""

from __future__ import annotations

import base64
import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.models.tts import TTSGenerateRequest, TTSGenerateResponse
from app.services.tts_service import TTSBackendUnavailable, TTSService, TTSServiceError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tts", tags=["tts"])


def get_tts_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> TTSService:
    """Provide a TTS service with lazy local model loading."""

    if not settings.tts_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "tts_disabled",
                    "message": "Text-to-speech is disabled in settings.",
                    "details": {},
                    "retryable": False,
                }
            },
        )
    return TTSService(settings=settings)


@router.post("/generate", response_model=None)
async def generate_tts(
    request: TTSGenerateRequest,
    tts_service: Annotated[TTSService, Depends(get_tts_service)],
) -> TTSGenerateResponse | StreamingResponse:
    """Generate speech audio from text.

    Non-streaming requests return base64 WAV audio in JSON for simple clients.
    Streaming requests return newline-delimited JSON events so the UI can start
    playback as soon as Orpheus yields PCM chunks, while still falling back to a
    bounded full WAV payload when true backend streaming is unavailable.
    """

    request_id = str(uuid4())
    context = request.context
    voice_id = request.voice_id
    logger.info(
        "Received TTS generation request",
        extra={
            "request_id": request_id,
            "voice_id": voice_id,
            "character_id": (
                context.character_id if context is not None else request.character_id
            ),
            "tts_context_mode": context.mode if context is not None else None,
            "tts_context_is_narration": (
                context.is_narration if context is not None else None
            ),
            "stream": request.stream,
            "text_chars": len(request.text),
        },
    )

    if request.stream:
        return StreamingResponse(
            _iter_tts_events(request, tts_service=tts_service, request_id=request_id),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache", "X-Request-ID": request_id},
        )

    try:
        result = await tts_service.generate_speech(
            text=request.text,
            voice_id=voice_id,
            character_id=request.character_id,
            context=context,
            audio_format=request.audio_format,
            request_id=request_id,
            tts_text=request.tts_text,
        )
    except TTSBackendUnavailable as exc:
        raise _tts_http_exception(
            exc, request_id=request_id, status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        ) from exc
    except TTSServiceError as exc:
        raise _tts_http_exception(
            exc, request_id=request_id, status_code=status.HTTP_400_BAD_REQUEST
        ) from exc
    except Exception as exc:  # pragma: no cover - unexpected defensive path.
        logger.exception(
            "Unhandled TTS request failure",
            extra={"request_id": request_id, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "tts_unexpected_error",
                    "message": "Unexpected TTS service error.",
                    "details": {"request_id": request_id},
                    "retryable": False,
                }
            },
        ) from exc

    return TTSGenerateResponse(
        request_id=request_id,
        backend=result.backend,  # type: ignore[arg-type]
        voice_id=result.voice_id,
        audio_format=result.audio_format,  # type: ignore[arg-type]
        audio_base64=result.to_base64(),
        sample_rate=result.sample_rate,
        duration_seconds=result.duration_seconds,
        fallback_used=result.fallback_used,
    )


async def _iter_tts_events(
    request: TTSGenerateRequest, *, tts_service: TTSService, request_id: str
) -> AsyncIterator[bytes]:
    """Yield streaming TTS events as compact newline-delimited JSON."""

    try:
        yield _json_line({"type": "start", "request_id": request_id})
        async for chunk in tts_service.stream_speech_chunks(
            text=request.text,
            voice_id=request.voice_id,
            character_id=request.character_id,
            context=request.context,
            audio_format=request.audio_format,
            request_id=request_id,
            tts_text=request.tts_text,
        ):
            if chunk.is_final:
                yield _json_line(
                    {
                        "type": "done",
                        "request_id": request_id,
                        "backend": chunk.backend,
                        "voice_id": chunk.voice_id,
                        "audio_format": chunk.audio_format,
                        "sample_rate": chunk.sample_rate,
                        "fallback_used": chunk.fallback_used,
                        "duration_seconds": chunk.duration_seconds,
                    }
                )
                continue
            yield _json_line(
                {
                    "type": "chunk",
                    "request_id": request_id,
                    "backend": chunk.backend,
                    "voice_id": chunk.voice_id,
                    "audio_format": chunk.audio_format,
                    "sample_rate": chunk.sample_rate,
                    "sequence": chunk.sequence,
                    "fallback_used": chunk.fallback_used,
                    "audio_base64": base64.b64encode(chunk.audio_bytes).decode("ascii"),
                }
            )
    except TTSServiceError as exc:
        logger.warning(
            "Streaming TTS request failed",
            extra={
                "request_id": request_id,
                "code": exc.code,
                "retryable": exc.retryable,
            },
        )
        yield _json_line(
            {
                "type": "error",
                "request_id": request_id,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": {**exc.details, "request_id": request_id},
                    "retryable": exc.retryable,
                },
            }
        )


def _json_line(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")


def _tts_http_exception(
    exc: TTSServiceError,
    *,
    request_id: str,
    status_code: int,
) -> HTTPException:
    logger.warning(
        "TTS request failed",
        extra={"request_id": request_id, "code": exc.code, "retryable": exc.retryable},
    )
    return HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": {**exc.details, "request_id": request_id},
                "retryable": exc.retryable,
            }
        },
    )
