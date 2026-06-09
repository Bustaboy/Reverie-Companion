"""FastAPI entrypoint for the Reverie backend."""

from fastapi import FastAPI

from app.api.routes.chat import router as chat_router
from app.core.config import Settings, get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Local-first backend foundation for Reverie, powered by FastAPI "
            "and Ollama."
        ),
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        """Return basic service health and active runtime configuration."""

        return {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "ollama_model": settings.ollama_model,
        }

    app.include_router(chat_router)
    return app


app = create_app()
