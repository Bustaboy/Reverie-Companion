"""FastAPI application entrypoint for the Reverie backend."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
import platform
import sys
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.chat import router as chat_router
from app.api.routes.growth import router as growth_router
from app.api.routes.journal import router as journal_router
from app.api.routes.tts import router as tts_router
from app.core.config import Settings, get_settings
from app.core.ollama_client import OllamaClient, OllamaClientError
from app.services.voice_manager import VoiceManager, VoiceManagerError

logger = logging.getLogger(__name__)


def configure_logging(settings: Settings) -> None:
    """Configure application logging once at startup.

    The standard library logger keeps the backend lightweight while still
    emitting useful structured fields through `extra={...}` for production logs.
    """

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return compact, structured validation errors for client mistakes.

    FastAPI's default validation response is useful for developers but can be
    noisy for app clients. This keeps the response predictable while preserving
    enough field-level detail to explain issues such as empty chat messages.
    """

    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    errors = [
        {
            "field": ".".join(
                str(part) for part in error.get("loc", []) if part != "body"
            ),
            "message": error.get("msg", "Invalid value."),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    logger.warning(
        "Request validation failed",
        extra={"request_id": request_id, "path": request.url.path, "errors": errors},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Invalid request payload.",
            "details": errors,
            "request_id": request_id,
        },
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Run lightweight local startup tasks before serving requests."""

    settings = get_settings()
    try:
        VoiceManager(settings).ensure_default_narrator_voice()
    except VoiceManagerError as exc:
        logger.warning(
            "Default narrator voice setup failed",
            extra={"code": exc.code, "details": exc.details},
        )
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        description="Local-first backend foundation for Reverie companion experiences.",
        lifespan=lifespan,
    )

    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)
    app.include_router(journal_router)
    app.include_router(growth_router)
    app.include_router(tts_router)
    logger.info(
        "Reverie backend application configured",
        extra={"app_version": settings.app_version},
    )

    return app


app = create_app()


@app.get("/health", tags=["health"])
async def health(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    """Return API, system, and Ollama health diagnostics."""

    ollama_client = OllamaClient(settings)
    response: dict[str, Any] = {
        "status": "ok",
        "service": {
            "name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug,
        },
        "system": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }

    try:
        ollama_status = await ollama_client.health()
        if ollama_status.get("status") != "ok":
            response["status"] = "degraded"
        response.update(ollama_status)
    except OllamaClientError as exc:
        logger.warning(
            "Health check degraded",
            extra={"error": exc.message, "details": exc.details},
        )
        response["status"] = "degraded"
        response["ollama"] = {
            "reachable": False,
            "host": settings.ollama_host,
            "configured_model": settings.ollama_model,
            "model_available": False,
            "model_loaded": False,
            "error": exc.message,
            "details": exc.details,
        }
    except Exception as exc:  # pragma: no cover - unexpected defensive path.
        logger.exception("Unexpected health check failure", extra={"error": str(exc)})
        response["status"] = "degraded"
        response["ollama"] = {
            "reachable": False,
            "host": settings.ollama_host,
            "configured_model": settings.ollama_model,
            "model_available": False,
            "model_loaded": False,
            "error": "Unexpected health check error.",
            "details": str(exc),
        }

    return response
