"""Request and response schemas for chat interactions."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MessageRole = Literal["system", "user", "assistant"]
VisualExpression = Literal[
    "neutral",
    "happy",
    "tender",
    "teasing",
    "shy",
    "embarrassed",
    "confident",
    "dominant",
    "aroused",
    "angry",
    "sad",
    "surprised",
]
VisualPose = Literal["idle", "close", "leaning", "guarded", "assertive"]
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
    stream: bool = Field(
        default=True, description="Whether to stream tokens using Server-Sent Events."
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_message_payload(cls, data: Any) -> Any:
        """Support `{\"message\": \"...\"}` while preserving the messages API."""

        if isinstance(data, dict) and "messages" not in data and "message" in data:
            normalized = dict(data)
            normalized["messages"] = [
                {"role": "user", "content": normalized.pop("message")}
            ]
            return normalized
        return data

    @field_validator("model")
    @classmethod
    def model_must_not_be_blank(cls, value: str | None) -> str | None:
        """Reject blank model overrides so settings fallback remains explicit."""

        if value is not None and not value.strip():
            raise ValueError("Model override cannot be empty.")
        return value


class GrowthNotification(BaseModel):
    """Subtle, user-visible note that a grounded growth signal was recorded."""

    id: str
    journal_entry_id: str
    created_at: str
    message: str
    why: str | None = None
    theme: str | None = None
    style: str = "whisper"
    controls: list[str] = Field(
        default_factory=lambda: ["dismiss", "review", "disable_similar"]
    )


class VisualState(BaseModel):
    """Deterministic VN visual metadata for one assistant turn.

    This is runtime scene state only. It must not be treated as durable growth,
    character canon, or evidence for training without a separate journal path.
    """

    character_id: str = Field(default="reverie", min_length=1, max_length=128)
    emotion: VisualExpression = "neutral"
    expression: VisualExpression = "neutral"
    pose: VisualPose = "idle"
    background: str = Field(default="default", min_length=1, max_length=128)
    intensity: float = Field(default=0.15, ge=0.0, le=1.0)
    confidence: float = Field(default=0.25, ge=0.0, le=1.0)
    sources: list[str] = Field(default_factory=lambda: ["fallback_neutral"], max_length=8)
    growth_cue: str | None = Field(default=None, max_length=128)


class ChatResponse(BaseModel):
    """Non-streaming chat completion response."""

    model: str
    message: ChatMessage
    done: bool = True
    growth_notification: GrowthNotification | None = None
    visual_state: VisualState | None = None
