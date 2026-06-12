"""Compatibility import for the canonical image generation FastAPI router."""

from app.api.routes.images import (  # noqa: F401
    cancel_image_job,
    generate_image,
    get_image_job,
    get_images_service,
    image_job_events,
    pause_image_job,
    resume_image_job,
    router,
)
