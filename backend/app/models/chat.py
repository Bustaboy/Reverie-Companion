"""Pydantic models for chat requests and responses."""

from typing import Literal

from pydantic import BaseModel, Field


ChatRole = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    """A single chat message in a conversation."""

    role: ChatRole
    content: str = Field(..., min_length=1)

    def to_ollama_message(self) -> dict[str, str]:
        """Convert the message to the shape expected by Ollama."""

        return {"role": self.role, "content": self.content}


class ChatRequest(BaseModel):
    """Request body for the `/chat` endpoint."""

    messages: list[ChatMessage] = Field(..., min_length=1)
    model: str | None = Field(
        default=None,
        description="Optional Ollama model override. Defaults to REVERIE_OLLAMA_MODEL.",
    )
    stream: bool = Field(
        default=True,
        description="When true, returns a streaming plain-text response.",
    )
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    """Non-streaming chat response."""

    model: str
    message: ChatMessage
