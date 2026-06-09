"""FastAPI application entrypoint for the Reverie backend."""

import logging
import platform
import sys
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.chat import router as chat_router
from app.core.config import Settings, get_settings
from app.core.ollama_client import OllamaClient, OllamaClientError

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


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        description="Local-first backend foundation for Reverie companion experiences.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)
    logger.info("Reverie backend application configured", extra={"app_version": settings.app_version})

    return app


app = create_app()


@app.get("/health", tags=["health"])
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, Any]:
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
        logger.warning("Health check degraded", extra={"error": exc.message, "details": exc.details})
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
