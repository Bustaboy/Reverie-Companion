"""Request and response schemas for chat interactions."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


MessageRole = Literal["system", "user", "assistant"]
MAX_CHAT_MESSAGE_LENGTH = 8_000
MAX_CHAT_MESSAGES = 100


def _strip_and_validate_text(value: str, *, field_name: str) -> str:
    """Normalize chat text and reject whitespace-only values."""

    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must not be empty or whitespace only.")
    return stripped


class ChatMessage(BaseModel):
    """A single chat message in Ollama-compatible format."""

    role: MessageRole
    content: str = Field(
        ...,
        min_length=1,
        max_length=MAX_CHAT_MESSAGE_LENGTH,
        description="Message text. Whitespace-only messages are rejected.",
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        """Keep Ollama from receiving empty or whitespace-only chat turns."""

        return _strip_and_validate_text(value, field_name="content")


class ChatRequest(BaseModel):
    """Payload accepted by the chat endpoint.

    `messages` remains the primary, Ollama-compatible request shape. The
    optional top-level `message` field is accepted as a convenience for simple
    clients and is converted into one user message before validation.
    """

    messages: list[ChatMessage] = Field(
        default_factory=list,
        min_length=1,
        max_length=MAX_CHAT_MESSAGES,
        description="Conversation messages to send to Ollama.",
    )
    message: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_CHAT_MESSAGE_LENGTH,
        description="Optional shorthand for a single user message.",
    )
    model: str | None = Field(default=None, description="Optional Ollama model override.")
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    num_predict: int | None = Field(default=None, gt=0)
    stream: bool = Field(default=True, description="Whether to stream tokens using Server-Sent Events.")

    @model_validator(mode="before")
    @classmethod
    def support_single_message_payload(cls, data: Any) -> Any:
        """Accept `{\"message\": \"...\"}` without breaking existing clients.

        This preserves the existing `messages` API while giving the endpoint the
        simple `message` validation requested for early frontend integrations.
        """

        if not isinstance(data, dict):
            return data

        if not data.get("messages") and data.get("message") is not None:
            data = data.copy()
            message = data["message"]
            if isinstance(message, str) and message.strip():
                data["messages"] = [{"role": "user", "content": message}]
        return data

    @model_validator(mode="after")
    def require_messages(self) -> "ChatRequest":
        """Require at least one message after shorthand conversion runs."""

        if not self.messages:
            raise ValueError("Either messages or message is required.")
        return self

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str | None) -> str | None:
        """Validate the convenience top-level `message` field when present."""

        if value is None:
            return value
        return _strip_and_validate_text(value, field_name="message")

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str | None) -> str | None:
        """Avoid passing blank model overrides to Ollama."""

        if value is None:
            return value
        return _strip_and_validate_text(value, field_name="model")


class ChatResponse(BaseModel):
    """Non-streaming chat completion response."""

    model: str
    message: ChatMessage
    done: bool = True
