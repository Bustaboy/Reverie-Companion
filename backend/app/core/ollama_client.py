"""Thin async wrapper around the Ollama Python client."""

import json
from collections.abc import AsyncIterator

from ollama import AsyncClient

from app.core.config import Settings
from app.models.chat import ChatMessage, ChatRequest, ChatResponse


class OllamaClient:
    """Encapsulates Ollama chat calls behind a backend-owned interface.

    Keeping this wrapper small and explicit makes it easier to add memory,
    character prompt assembly, routing, telemetry, and growth hooks later
    without coupling API routes directly to the Ollama SDK.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncClient(
            host=settings.ollama_host,
            timeout=settings.ollama_timeout_seconds,
        )

    async def health(self) -> dict[str, str]:
        """Verify Ollama is reachable and return basic service status."""

        await self._client.list()
        return {
            "status": "ok",
            "ollama": "reachable",
            "model": self._settings.ollama_model,
        }

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Run a non-streaming chat completion."""

        model = request.model or self._settings.ollama_model
        response = await self._client.chat(
            model=model,
            messages=self._serialize_messages(request.messages),
            options=self._generation_options(request),
            stream=False,
        )
        message = self._read_value(response, "message", {})

        return ChatResponse(
            model=self._read_value(response, "model", model),
            message=ChatMessage(
                role=self._read_value(message, "role", "assistant"),
                content=self._read_value(message, "content", ""),
            ),
            done=self._read_value(response, "done", True),
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        """Stream chat completion chunks as Server-Sent Events."""

        model = request.model or self._settings.ollama_model
        stream = await self._client.chat(
            model=model,
            messages=self._serialize_messages(request.messages),
            options=self._generation_options(request),
            stream=True,
        )

        async for chunk in stream:
            message = self._read_value(chunk, "message", {})
            content = self._read_value(message, "content", "")
            done = self._read_value(chunk, "done", False)

            if content:
                yield self._format_sse(
                    event="message",
                    data={"content": content, "model": self._read_value(chunk, "model", model)},
                )

            if done:
                yield self._format_sse(event="done", data={"done": True})

    def _generation_options(self, request: ChatRequest) -> dict[str, float | int]:
        """Build Ollama generation options from request and defaults."""

        return {
            "temperature": request.temperature
            if request.temperature is not None
            else self._settings.default_temperature,
            "top_p": request.top_p if request.top_p is not None else self._settings.default_top_p,
            "num_predict": request.num_predict
            if request.num_predict is not None
            else self._settings.default_num_predict,
        }

    @staticmethod
    def _serialize_messages(messages: list[ChatMessage]) -> list[dict[str, str]]:
        """Convert Pydantic chat messages into Ollama SDK dictionaries."""

        return [message.model_dump() for message in messages]

    @staticmethod
    def _read_value(source: object, key: str, default: object) -> object:
        """Read a value from Ollama response objects or dictionaries."""

        if isinstance(source, dict):
            return source.get(key, default)

        return getattr(source, key, default)

    @staticmethod
    def _format_sse(event: str, data: dict[str, object]) -> str:
        """Format one Server-Sent Event frame."""

        return f"event: {event}\ndata: {json.dumps(data)}\n\n"
