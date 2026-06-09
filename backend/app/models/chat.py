"""Request and response schemas for chat interactions."""

from typing import Literal

from pydantic import BaseModel, Field


MessageRole = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    """A single chat message in Ollama-compatible format."""

    role: MessageRole
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    """Payload accepted by the chat endpoint."""

    messages: list[ChatMessage] = Field(..., min_length=1)
    model: str | None = Field(default=None, description="Optional Ollama model override.")
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    num_predict: int | None = Field(default=None, gt=0)
    stream: bool = Field(default=True, description="Whether to stream tokens using Server-Sent Events.")


class ChatResponse(BaseModel):
    """Non-streaming chat completion response."""

    model: str
    message: ChatMessage
    done: bool = True
