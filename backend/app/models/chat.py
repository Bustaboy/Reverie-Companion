"""Request and response schemas for chat interactions."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


MessageRole = Literal["system", "user", "assistant"]
MAX_MESSAGE_CONTENT_LENGTH = 4_000
MAX_CHAT_MESSAGES = 50


class ChatMessage(BaseModel):
    """A single chat message in Ollama-compatible format."""

    role: MessageRole
    content: str = Field(
        ...,
        min_length=1,
        max_length=MAX_MESSAGE_CONTENT_LENGTH,
        description="Message text. Whitespace-only content is rejected.",
    )

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        """Reject blank messages and normalize surrounding whitespace.

        Pydantic's built-in `min_length` catches empty strings, but this keeps
        whitespace-only input from reaching Ollama and producing confusing
        downstream errors.
        """

        stripped = value.strip()
        if not stripped:
            raise ValueError("Message content must not be empty.")
        return stripped


class ChatRequest(BaseModel):
    """Payload accepted by the chat endpoint.

    `messages` remains the canonical shape used by the current API. A top-level
    `message` string is accepted as a lightweight convenience for simple clients
    and is converted into a single user message before the route runs.
    """

    messages: list[ChatMessage] = Field(..., min_length=1, max_length=MAX_CHAT_MESSAGES)
    model: str | None = Field(default=None, description="Optional Ollama model override.")
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    num_predict: int | None = Field(default=None, gt=0)
    stream: bool = Field(default=True, description="Whether to stream tokens using Server-Sent Events.")

    @model_validator(mode="before")
    @classmethod
    def accept_single_message(cls, data: Any) -> Any:
        """Allow `{"message": "..."}` without breaking existing clients.

        The frontend can continue sending Ollama-style `messages`, while tests
        or minimal callers can send the requested `message` field and receive the
        same behavior as a one-turn user chat.
        """

        if not isinstance(data, dict) or "messages" in data or "message" not in data:
            return data

        message = data.get("message")
        data = data.copy()
        data["messages"] = [{"role": "user", "content": message}]
        return data


class ChatResponse(BaseModel):
    """Non-streaming chat completion response."""

    model: str
    message: ChatMessage
    done: bool = True
