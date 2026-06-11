"""Chat API routes for local Ollama-powered companion responses."""

import logging
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.core.memory import MemoryManager, get_memory_manager
from app.core.ollama_client import OllamaClient, OllamaClientError
from app.core.reflection import ReflectionManager
from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


def get_ollama_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> OllamaClient:
    """Provide an Ollama client for request handlers."""

    return OllamaClient(settings)


def get_chat_service(
    settings: Annotated[Settings, Depends(get_settings)],
    ollama_client: Annotated[OllamaClient, Depends(get_ollama_client)],
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
) -> ChatService:
    """Provide the service that assembles chat prompts and calls Ollama."""

    reflection_manager = ReflectionManager(memory_manager=memory_manager)
    return ChatService(
        settings=settings,
        ollama_client=ollama_client,
        memory_manager=memory_manager,
        reflection_manager=reflection_manager,
    )


@router.post("/chat", response_model=None)
async def chat(
    request: ChatRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
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
            return await chat_service.chat(request, request_id=request_id)
        except OllamaClientError as exc:
            logger.warning(
                "Chat request failed",
                extra={"request_id": request_id, "model": model, "error": exc.message},
            )
            raise HTTPException(
                status_code=exc.status_code,
                detail={
                    "error": exc.message,
                    "details": exc.details,
                    "request_id": request_id,
                },
            ) from exc
        except Exception as exc:  # pragma: no cover - unexpected defensive path.
            logger.exception(
                "Unhandled chat request failure",
                extra={"request_id": request_id, "model": model, "error": str(exc)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Unexpected chat service error.",
                    "request_id": request_id,
                },
            ) from exc

    return StreamingResponse(
        await chat_service.stream_chat(request, request_id=request_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request_id,
        },
    )
