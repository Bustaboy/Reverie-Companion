"""FastAPI application entrypoint for the Reverie backend."""

from fastapi import FastAPI

from app.api.routes.chat import router as chat_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local-first backend foundation for Reverie's offline AI companion.",
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Return a lightweight readiness signal for local clients."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }


app.include_router(chat_router)
