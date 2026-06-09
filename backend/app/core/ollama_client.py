"""Async Ollama integration for the Reverie backend.

This module intentionally keeps Ollama-specific behavior behind a small
application-owned boundary. Future memory, character, and growth systems can
prepare context before calling this client without the API route knowing about
Ollama SDK details.
"""

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from httpx import TimeoutException
from ollama import AsyncClient, ResponseError

from app.core.config import Settings
from app.models.chat import ChatMessage, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


class OllamaClientError(Exception):
    """Base exception for expected Ollama integration failures."""

    status_code = 502

    def __init__(self, message: str, *, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class OllamaConnectionError(OllamaClientError):
    """Raised when the local Ollama server cannot be reached."""

    status_code = 503


class OllamaModelUnavailableError(OllamaClientError):
    """Raised when the requested model is not available to Ollama."""

    status_code = 404


class OllamaGenerationError(OllamaClientError):
    """Raised when Ollama rejects or fails a generation request."""

    status_code = 502


class OllamaTimeoutError(OllamaClientError):
    """Raised when Ollama does not respond within the configured timeout."""

    status_code = 504


class OllamaClient:
    """Encapsulates Ollama chat calls behind a backend-owned interface.

    The methods accept full `ChatRequest` objects today, but message preparation
    is isolated in `_prepare_messages()` so future systems can insert memory,
    character state, or growth context without changing route code.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncClient(
            host=settings.ollama_host,
            timeout=settings.ollama_timeout_seconds,
        )

    async def health(self) -> dict[str, Any]:
        """Return detailed Ollama diagnostics for `/health`.

        `model_available` means the configured model exists in Ollama's local
        model list. `model_loaded` means Ollama reports it as currently loaded
        in memory, when the installed Ollama version exposes that information.
        """

        logger.debug("Checking Ollama health", extra={"ollama_host": self._settings.ollama_host})

        try:
            models_response = await self._client.list()
        except Exception as exc:  # pragma: no cover - depends on local Ollama availability.
            logger.warning(
                "Ollama health check failed",
                extra={"ollama_host": self._settings.ollama_host, "error": str(exc)},
            )
            raise OllamaConnectionError(
                "Ollama is not reachable. Make sure the local Ollama service is running.",
                details=str(exc),
            ) from exc

        available_models = self._extract_model_names(models_response)
        configured_model = self._settings.ollama_model
        model_available = configured_model in available_models
        loaded_models = await self._loaded_model_names()
        model_loaded = configured_model in loaded_models if loaded_models is not None else None

        status = "ok" if model_available else "degraded"
        logger.info(
            "Ollama health check completed",
            extra={
                "status": status,
                "configured_model": configured_model,
                "model_available": model_available,
                "model_loaded": model_loaded,
                "available_model_count": len(available_models),
            },
        )

        return {
            "status": status,
            "ollama": {
                "reachable": True,
                "host": self._settings.ollama_host,
                "configured_model": configured_model,
                "model_available": model_available,
                "model_loaded": model_loaded,
                "available_models": available_models,
                "available_model_count": len(available_models),
                "loaded_models": loaded_models or [],
            },
        }

    async def chat(self, request: ChatRequest, *, request_id: str | None = None) -> ChatResponse:
        """Run a non-streaming chat completion."""

        model = request.model or self._settings.ollama_model
        logger.info(
            "Starting Ollama chat completion",
            extra={"request_id": request_id, "model": model, "stream": False},
        )

        try:
            response = await self._client.chat(
                model=model,
                messages=self._prepare_messages(request),
                options=self._generation_options(request),
                stream=False,
            )
        except Exception as exc:
            raise self._map_exception(exc, model=model, request_id=request_id) from exc

        message = self._read_value(response, "message", {})
        content = self._read_value(message, "content", "")

        if not isinstance(content, str) or not content:
            logger.error(
                "Ollama returned an empty chat response",
                extra={"request_id": request_id, "model": model},
            )
            raise OllamaGenerationError("Ollama returned an empty response.")

        logger.info(
            "Completed Ollama chat completion",
            extra={"request_id": request_id, "model": model, "response_chars": len(content)},
        )

        return ChatResponse(
            model=str(self._read_value(response, "model", model)),
            message=ChatMessage(role="assistant", content=content),
            done=bool(self._read_value(response, "done", True)),
        )

    async def stream_chat(
        self,
        request: ChatRequest,
        *,
        request_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion chunks as Server-Sent Events.

        Once a streaming HTTP response has started, FastAPI can no longer change
        the status code. Expected and unexpected Ollama failures are therefore
        sent as an `error` SSE event. A `done` event is emitted from `finally` so
        clients can reliably clean up listeners even when generation fails.
        """

        model = request.model or self._settings.ollama_model
        emitted_chunks = 0
        done_sent = False
        stream_completed = False
        logger.info(
            "Starting Ollama streaming chat completion",
            extra={"request_id": request_id, "model": model, "stream": True},
        )

        try:
            stream = await self._client.chat(
                model=model,
                messages=self._prepare_messages(request),
                options=self._generation_options(request),
                stream=True,
            )

            async for chunk in stream:
                message = self._read_value(chunk, "message", {})
                content = self._read_value(message, "content", "")
                done = bool(self._read_value(chunk, "done", False))

                if isinstance(content, str) and content:
                    emitted_chunks += 1
                    yield self._format_sse(
                        event="message",
                        data={
                            "content": content,
                            "model": self._read_value(chunk, "model", model),
                            "request_id": request_id,
                        },
                    )

                if done:
                    stream_completed = True
                    logger.info(
                        "Completed Ollama streaming chat completion",
                        extra={
                            "request_id": request_id,
                            "model": model,
                            "chunks": emitted_chunks,
                        },
                    )
                    yield self._format_sse(
                        event="done",
                        data={"done": True, "request_id": request_id},
                    )
                    done_sent = True
                    return

            # Ollama should finish streaming with a chunk containing done=true.
            # If iteration stops first, tell the client the stream was incomplete
            # instead of silently pretending the generation completed normally.
            logger.warning(
                "Ollama stream ended without a done marker",
                extra={"request_id": request_id, "model": model, "chunks": emitted_chunks},
            )
            yield self._format_sse(
                event="error",
                data={
                    "error": "Ollama stream ended before completion.",
                    "request_id": request_id,
                },
            )
        except Exception as exc:
            mapped_error = self._map_exception(exc, model=model, request_id=request_id)
            logger.error(
                "Ollama streaming chat failed",
                extra={
                    "request_id": request_id,
                    "model": model,
                    "error": mapped_error.message,
                    "details": mapped_error.details,
                    "chunks": emitted_chunks,
                },
            )
            yield self._format_sse(
                event="error",
                data={
                    "error": mapped_error.message,
                    "request_id": request_id,
                },
            )
        finally:
            if not done_sent:
                yield self._format_sse(
                    event="done",
                    data={
                        "done": stream_completed,
                        "request_id": request_id,
                    },
                )

    def _generation_options(self, request: ChatRequest) -> dict[str, float | int]:
        """Build Ollama generation options from request overrides and defaults."""

        return {
            "temperature": request.temperature
            if request.temperature is not None
            else self._settings.default_temperature,
            "top_p": request.top_p if request.top_p is not None else self._settings.default_top_p,
            "num_predict": request.num_predict
            if request.num_predict is not None
            else self._settings.default_num_predict,
        }

    def _prepare_messages(self, request: ChatRequest) -> list[dict[str, str]]:
        """Prepare messages for Ollama.

        This is the extension seam for future memory retrieval, character card
        injection, relationship state, and growth/reflection context.
        """

        return [message.model_dump() for message in request.messages]

    async def _loaded_model_names(self) -> list[str] | None:
        """Return models currently loaded in Ollama, if supported."""

        ps = getattr(self._client, "ps", None)
        if ps is None:
            return None

        try:
            loaded_response = await ps()
        except Exception as exc:  # pragma: no cover - optional diagnostic only.
            logger.debug("Could not query loaded Ollama models", extra={"error": str(exc)})
            return None

        return self._extract_model_names(loaded_response)

    def _map_exception(
        self,
        exc: Exception,
        *,
        model: str,
        request_id: str | None = None,
    ) -> OllamaClientError:
        """Map SDK/network exceptions into API-friendly client errors."""

        if isinstance(exc, OllamaClientError):
            return exc

        if isinstance(exc, TimeoutException):
            logger.error(
                "Ollama request timed out",
                extra={
                    "request_id": request_id,
                    "model": model,
                    "timeout_seconds": self._settings.ollama_timeout_seconds,
                    "error": str(exc),
                },
            )
            return OllamaTimeoutError(
                "Ollama did not respond before the configured timeout.",
                details=f"Timed out after {self._settings.ollama_timeout_seconds} seconds.",
            )

        if isinstance(exc, ResponseError):
            status_code = int(getattr(exc, "status_code", 502) or 502)
            message = str(exc)
            logger.error(
                "Ollama returned an error response",
                extra={
                    "request_id": request_id,
                    "model": model,
                    "status_code": status_code,
                    "error": message,
                },
            )
            if status_code == 404:
                return OllamaModelUnavailableError(
                    f"Ollama model '{model}' is not available. Pull it with `ollama pull {model}`.",
                    details=message,
                )
            return OllamaGenerationError("Ollama failed to generate a response.", details=message)

        logger.exception(
            "Unexpected Ollama client failure",
            extra={"request_id": request_id, "model": model, "error": str(exc)},
        )
        return OllamaConnectionError(
            "Could not connect to Ollama or the local model backend failed.",
            details=str(exc),
        )

    @classmethod
    def _extract_model_names(cls, source: object) -> list[str]:
        """Extract model names from Ollama list/ps responses."""

        models = cls._read_value(source, "models", [])
        names: list[str] = []

        if not isinstance(models, list):
            return names

        for model in models:
            name = cls._read_value(model, "name", None) or cls._read_value(model, "model", None)
            if isinstance(name, str):
                names.append(name)

        return sorted(set(names))

    @staticmethod
    def _read_value(source: object, key: str, default: Any) -> Any:
        """Read a value from Ollama response objects or dictionaries."""

        if isinstance(source, dict):
            return source.get(key, default)

        return getattr(source, key, default)

    @staticmethod
    def _format_sse(event: str, data: dict[str, object]) -> str:
        """Format one Server-Sent Event frame."""

        return f"event: {event}\ndata: {json.dumps(data)}\n\n"
