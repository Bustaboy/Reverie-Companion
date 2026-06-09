"""Chat API routes for local Ollama-powered companion responses."""

import logging
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.core.ollama_client import OllamaClient, OllamaClientError
from app.models.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


def get_ollama_client(settings: Annotated[Settings, Depends(get_settings)]) -> OllamaClient:
    """Provide an Ollama client for request handlers.

    Keeping this as a dependency makes it easy to swap in a richer chat service
    later when memory, character state, and growth logic are introduced.
    """

    return OllamaClient(settings)


@router.post("/chat", response_model=None)
async def chat(
    request: ChatRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    ollama_client: Annotated[OllamaClient, Depends(get_ollama_client)],
) -> ChatResponse | StreamingResponse:
    """Generate a chat response, streaming by default.

    Streaming uses Server-Sent Events with `message` events for token chunks,
    a final `done` event, and an `error` event if Ollama fails after the HTTP
    stream has started.
    """

    request_id = str(uuid4())
    model = request.model or settings.ollama_model
    logger.info(
        "Received chat request",
        extra={
            "request_id": request_id,
            "model": model,
            "message_count": len(request.messages),
            "stream": request.stream,
        },
    )

    if not request.stream:
        try:
            return await ollama_client.chat(request, request_id=request_id)
        except OllamaClientError as exc:
            logger.warning(
                "Chat request failed",
                extra={"request_id": request_id, "model": model, "error": exc.message},
            )
            raise HTTPException(
                status_code=exc.status_code,
                detail={"error": exc.message, "details": exc.details, "request_id": request_id},
            ) from exc
        except Exception as exc:  # pragma: no cover - unexpected defensive path.
            logger.exception(
                "Unhandled chat request failure",
                extra={"request_id": request_id, "model": model, "error": str(exc)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "Unexpected chat service error.", "request_id": request_id},
            ) from exc

    return StreamingResponse(
        ollama_client.stream_chat(request, request_id=request_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request_id,
        },
    )
