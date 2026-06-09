"""Thin async wrapper around Ollama chat generation."""

from collections.abc import AsyncIterator, Sequence
from typing import Any

from ollama import AsyncClient

from app.core.config import Settings, get_settings

ChatMessage = dict[str, str]


class OllamaClient:
    """Client for local Ollama-backed language generation.

    This wrapper keeps route handlers small and provides a stable seam for
    future prompt orchestration, memory retrieval, character state, and growth
    logic without coupling those systems directly to the Ollama SDK.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = AsyncClient(
            host=self._settings.ollama_host,
            timeout=self._settings.request_timeout_seconds,
        )

    async def stream_chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        num_ctx: int | None = None,
    ) -> AsyncIterator[str]:
        """Yield generated response chunks from Ollama as plain text."""
        stream = await self._client.chat(
            model=model or self._settings.ollama_model,
            messages=list(messages),
            stream=True,
            options={
                "temperature": temperature
                if temperature is not None
                else self._settings.ollama_temperature,
                "top_p": top_p if top_p is not None else self._settings.ollama_top_p,
                "num_ctx": num_ctx if num_ctx is not None else self._settings.ollama_num_ctx,
            },
        )

        async for chunk in stream:
            content = chunk.get("message", {}).get("content")
            if content:
                yield content

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        num_ctx: int | None = None,
    ) -> str:
        """Return a complete chat response from Ollama."""
        response: dict[str, Any] = await self._client.chat(
            model=model or self._settings.ollama_model,
            messages=list(messages),
            stream=False,
            options={
                "temperature": temperature
                if temperature is not None
                else self._settings.ollama_temperature,
                "top_p": top_p if top_p is not None else self._settings.ollama_top_p,
                "num_ctx": num_ctx if num_ctx is not None else self._settings.ollama_num_ctx,
            },
        )
        return response.get("message", {}).get("content", "")


ollama_client = OllamaClient()
