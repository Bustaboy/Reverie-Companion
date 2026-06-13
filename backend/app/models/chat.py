"""Request and response schemas for chat interactions."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.tts import TTSContext, TTSEmotionMetadata

MessageRole = Literal["system", "user", "assistant"]
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
    character_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=80,
        description="Optional selected companion identity used for scoped memory and prompt grounding.",
    )
    tts_context: TTSContext | None = Field(
        default=None,
        description="Optional TTS routing context supplied by chat or VN state.",
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

    @field_validator("character_id")
    @classmethod
    def character_id_must_not_be_blank(cls, value: str | None) -> str | None:
        """Keep selected character IDs stable and intentional."""

        if value is not None and not value.strip():
            raise ValueError("Choose a companion before starting this memory thread.")
        return value.strip() if value is not None else None


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


class ChatResponse(BaseModel):
    """Non-streaming chat completion response."""

    model: str
    message: ChatMessage
    done: bool = True
    growth_notification: GrowthNotification | None = None
    tts_context: TTSContext | None = None
    tts_text: str | None = None
    voice_id: str | None = None
    emotion: TTSEmotionMetadata | None = None
