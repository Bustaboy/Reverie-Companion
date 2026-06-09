"""Async Ollama client wrapper used by Reverie's API layer."""

from collections.abc import AsyncIterator, Sequence

from ollama import AsyncClient

from app.core.config import Settings, get_settings
from app.models.chat import ChatMessage


class OllamaClient:
    """Small typed wrapper around the Ollama async client.

    The wrapper keeps the external dependency isolated so future prompt, memory,
    character, and growth systems can enrich messages before generation without
    coupling route handlers directly to Ollama's API surface.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = AsyncClient(
            host=self._settings.ollama_host,
            timeout=self._settings.ollama_request_timeout,
        )

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        """Return a complete assistant response for the provided conversation."""

        response = await self._client.chat(
            model=model or self._settings.ollama_model,
            messages=[message.to_ollama_message() for message in messages],
            options=self._generation_options(temperature=temperature, top_p=top_p),
            stream=False,
        )
        return response["message"]["content"]

    async def stream_chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> AsyncIterator[str]:
        """Yield assistant response chunks as Ollama streams them."""

        stream = await self._client.chat(
            model=model or self._settings.ollama_model,
            messages=[message.to_ollama_message() for message in messages],
            options=self._generation_options(temperature=temperature, top_p=top_p),
            stream=True,
        )

        async for chunk in stream:
            content = chunk.get("message", {}).get("content")
            if content:
                yield content

    def _generation_options(
        self,
        *,
        temperature: float | None,
        top_p: float | None,
    ) -> dict[str, float]:
        """Build Ollama generation options with configured defaults."""

        return {
            "temperature": temperature
            if temperature is not None
            else self._settings.default_temperature,
            "top_p": top_p if top_p is not None else self._settings.default_top_p,
        }
