"""FastAPI application entrypoint for the Reverie backend."""

from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.chat import router as chat_router
from app.core.config import Settings, get_settings
from app.core.ollama_client import OllamaClient


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
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

    return app


app = create_app()


@app.get("/health", tags=["health"])
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, str]:
    """Return API and Ollama health information."""

    ollama_client = OllamaClient(settings)

    try:
        ollama_status = await ollama_client.health()
    except Exception as exc:  # pragma: no cover - depends on local Ollama availability.
        return {
            "status": "degraded",
            "service": settings.app_name,
            "ollama": "unreachable",
            "detail": str(exc),
        }

    return {
        "status": "ok",
        "service": settings.app_name,
        **ollama_status,
    }
