"""Request and response schemas for chat interactions."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


MessageRole = Literal["system", "user", "assistant"]
GrowthNotificationStyle = Literal["whisper", "toast", "inline"]
MAX_MESSAGE_LENGTH = 8_000
MAX_MODEL_NAME_LENGTH = 128


class ChatMessage(BaseModel):
    """A single chat message in Ollama-compatible format."""

    role: MessageRole
    content: str = Field(
        ...,
        min_length=1,
        max_length=MAX_MESSAGE_LENGTH,
        description="Message text sent to or returned by the assistant.",
    )

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        """Reject whitespace-only messages before they reach Ollama."""

        if not value.strip():
            raise ValueError("Message content cannot be empty.")
        return value


class GrowthNotification(BaseModel):
    """A subtle, user-dismissible note about character growth.

    Growth notices are generated from existing reflection journal entries and
    intentionally avoid raw evidence or sensitive transcript details. They are
    metadata for the UI, not instructions for the model.
    """

    id: str = Field(..., min_length=1, max_length=160)
    journal_entry_id: str | None = Field(default=None, max_length=160)
    text: str = Field(..., min_length=1, max_length=220)
    theme: str | None = Field(default=None, max_length=80)
    style: GrowthNotificationStyle = "whisper"
    created_at: str = Field(..., min_length=1, max_length=80)
    controls: list[str] = Field(
        default_factory=lambda: ["dismiss", "review", "disable_similar"]
    )

    @field_validator("text")
    @classmethod
    def text_must_be_short_and_warm(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("Growth notification text cannot be empty.")
        return normalized


class ChatRequest(BaseModel):
    """Payload accepted by the chat endpoint.

    The canonical shape is `messages=[...]`. For early clients that send a
    single top-level `message` string, a pre-validation hook converts it into a
    one-message conversation so `/chat` remains backward compatible.
    """

    messages: list[ChatMessage] = Field(..., min_length=1)
    model: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_MODEL_NAME_LENGTH,
        description="Optional Ollama model override.",
    )
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    num_predict: int | None = Field(default=None, gt=0)
    stream: bool = Field(default=True, description="Whether to stream tokens using Server-Sent Events.")

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_message_payload(cls, data: Any) -> Any:
        """Support `{\"message\": \"...\"}` while preserving the messages API."""

        if isinstance(data, dict) and "messages" not in data and "message" in data:
            normalized = dict(data)
            normalized["messages"] = [{"role": "user", "content": normalized.pop("message")}]
            return normalized
        return data

    @field_validator("model")
    @classmethod
    def model_must_not_be_blank(cls, value: str | None) -> str | None:
        """Reject blank model overrides so settings fallback remains explicit."""

        if value is not None and not value.strip():
            raise ValueError("Model override cannot be empty.")
        return value


class ChatResponse(BaseModel):
    """Non-streaming chat completion response."""

    model: str
    message: ChatMessage
    done: bool = True
    growth_notification: GrowthNotification | None = None
