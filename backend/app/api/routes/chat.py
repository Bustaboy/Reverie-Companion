"""Chat API routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.core.ollama_client import OllamaClient
from app.models.chat import ChatMessage, ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


def get_ollama_client(settings: Settings = Depends(get_settings)) -> OllamaClient:
    """Create an Ollama client for the current request."""

    return OllamaClient(settings)


@router.post("/chat", response_model=ChatResponse | None)
async def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
    ollama_client: OllamaClient = Depends(get_ollama_client),
) -> ChatResponse | StreamingResponse:
    """Generate a companion response from the configured local Ollama model.

    The endpoint streams plain text by default to keep the UI responsive during
    longer generations. Set `stream` to `false` for a complete JSON response.
    """

    model_name = request.model or settings.ollama_model

    if request.stream:
        return StreamingResponse(
            ollama_client.stream_chat(
                request.messages,
                model=model_name,
                temperature=request.temperature,
                top_p=request.top_p,
            ),
            media_type="text/plain; charset=utf-8",
        )

    content = await ollama_client.chat(
        request.messages,
        model=model_name,
        temperature=request.temperature,
        top_p=request.top_p,
    )
    return ChatResponse(
        model=model_name,
        message=ChatMessage(role="assistant", content=content),
    )
