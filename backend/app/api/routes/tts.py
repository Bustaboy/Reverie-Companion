"""Text-to-speech API routes."""

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

    Non-streaming requests return base64 WAV audio in JSON for easy early
    clients. Streaming requests return audio bytes directly; current backends
    synthesize whole files first and stream in bounded chunks.
    """

    request_id = str(uuid4())
    voice_id = request.voice_id
    logger.info(
        "Received TTS generation request",
        extra={
            "request_id": request_id,
            "voice_id": voice_id,
            "character_id": request.context.character_id
            if request.context
            else request.character_id,
            "tts_mode": request.context.mode if request.context else "one_to_one",
            "is_narration": request.context.is_narration if request.context else False,
            "stream": request.stream,
            "text_chars": len(request.text),
        },
    )

    try:
        result = await tts_service.generate_speech(
            text=request.text,
            voice_id=voice_id,
            character_id=request.character_id,
            context=request.context,
            audio_format=request.audio_format,
            request_id=request_id,
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

    if request.stream:
        return StreamingResponse(
            _iter_audio_chunks(
                result.audio_bytes,
                chunk_size=tts_service.settings.tts_stream_chunk_size_bytes,
            ),
            media_type=f"audio/{request.audio_format}",
            headers={
                "Cache-Control": "no-cache",
                "X-Request-ID": request_id,
                "X-TTS-Backend": result.backend,
            },
        )

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


async def _iter_audio_chunks(
    audio_bytes: bytes, *, chunk_size: int
) -> AsyncIterator[bytes]:
    for start in range(0, len(audio_bytes), chunk_size):
        yield audio_bytes[start : start + chunk_size]


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
