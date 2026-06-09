"""Chat endpoints for local Ollama-backed companion responses."""

from collections.abc import AsyncIterator
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.ollama_client import ChatMessage, ollama_client

settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["chat"])

Role = Literal["system", "user", "assistant"]


class Message(BaseModel):
    """Single chat message exchanged with the local model."""

    role: Role = Field(description="Message author role.")
    content: str = Field(min_length=1, description="Message text.")


class ChatRequest(BaseModel):
    """Request body for a companion chat generation."""

    messages: list[Message] = Field(
        min_length=1,
        description="Conversation history to send to the model.",
    )
    model: str | None = Field(
        default=None,
        description="Optional Ollama model override for this request.",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Optional response creativity override.",
    )
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional nucleus sampling override.",
    )
    num_ctx: int | None = Field(
        default=None,
        ge=1024,
        description="Optional context window override.",
    )

    def to_ollama_messages(self) -> list[ChatMessage]:
        """Convert validated request messages to the Ollama SDK shape."""
        return [message.model_dump() for message in self.messages]


async def stream_response(request: ChatRequest) -> AsyncIterator[str]:
    """Stream text chunks from the local model to the HTTP client."""
    async for chunk in ollama_client.stream_chat(
        request.to_ollama_messages(),
        model=request.model,
        temperature=request.temperature,
        top_p=request.top_p,
        num_ctx=request.num_ctx,
    ):
        yield chunk


@router.post("/chat", response_class=StreamingResponse)
async def chat(request: ChatRequest) -> StreamingResponse:
    """Generate a streaming companion response from the local Ollama model."""
    return StreamingResponse(
        stream_response(request),
        media_type="text/plain; charset=utf-8",
    )
