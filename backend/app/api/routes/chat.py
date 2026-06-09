"""Chat API routes for local Ollama-powered companion responses."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.core.ollama_client import OllamaClient
from app.models.chat import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


def get_ollama_client(settings: Annotated[Settings, Depends(get_settings)]) -> OllamaClient:
    """Provide an Ollama client for request handlers."""

    return OllamaClient(settings)


@router.post("/chat", response_model=None)
async def chat(
    request: ChatRequest,
    ollama_client: Annotated[OllamaClient, Depends(get_ollama_client)],
) -> ChatResponse | StreamingResponse:
    """Generate a chat response, streaming by default.

    Streaming uses Server-Sent Events with `message` events for token chunks
    and a final `done` event. The non-streaming mode is useful for tests and
    simple integrations.
    """

    if not request.stream:
        return await ollama_client.chat(request)

    return StreamingResponse(
        ollama_client.stream_chat(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
