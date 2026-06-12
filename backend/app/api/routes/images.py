"""Image generation API routes for queued local ComfyUI jobs."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.models.image import ImageGenerateRequest, ImageGenerateResponse, ImageJobRead
from app.services.image_generation_service import (
    ImageGenerationService,
    ImageGenerationServiceError,
    get_image_generation_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/images", tags=["images"])


def get_images_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ImageGenerationService:
    """Provide the process-local image generation service singleton."""

    return get_image_generation_service(settings)


@router.post(
    "/generate",
    response_model=ImageGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_image(
    request: ImageGenerateRequest,
    service: Annotated[ImageGenerationService, Depends(get_images_service)],
) -> ImageGenerateResponse:
    """Queue a local image generation job without blocking chat or TTS."""

    try:
        job = await service.submit(request)
    except ImageGenerationServiceError as exc:
        raise _image_http_exception(exc) from exc
    return ImageGenerateResponse(job=job)


@router.get("/{job_id}", response_model=ImageJobRead)
async def get_image_job(
    job_id: str,
    service: Annotated[ImageGenerationService, Depends(get_images_service)],
) -> ImageJobRead:
    """Return the latest state for a queued image generation job."""

    try:
        return service.get_job(job_id)
    except ImageGenerationServiceError as exc:
        raise _image_http_exception(exc) from exc


@router.get("/{job_id}/events", response_model=None)
async def image_job_events(
    job_id: str,
    service: Annotated[ImageGenerationService, Depends(get_images_service)],
) -> StreamingResponse:
    """Stream structured image job lifecycle/progress events over SSE."""

    try:
        service.get_job(job_id)
    except ImageGenerationServiceError as exc:
        raise _image_http_exception(exc) from exc

    return StreamingResponse(
        _iter_sse(service, job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{job_id}/cancel", response_model=ImageJobRead)
async def cancel_image_job(
    job_id: str,
    service: Annotated[ImageGenerationService, Depends(get_images_service)],
) -> ImageJobRead:
    """Cancel a queued, paused, or running image generation job."""

    try:
        return await service.cancel(job_id)
    except ImageGenerationServiceError as exc:
        raise _image_http_exception(exc) from exc


@router.post("/{job_id}/pause", response_model=ImageJobRead)
async def pause_image_job(
    job_id: str,
    service: Annotated[ImageGenerationService, Depends(get_images_service)],
) -> ImageJobRead:
    """Manually pause an image job; automatic resource pauses use the same states."""

    try:
        return await service.pause(job_id)
    except ImageGenerationServiceError as exc:
        raise _image_http_exception(exc) from exc


@router.post("/{job_id}/resume", response_model=ImageJobRead)
async def resume_image_job(
    job_id: str,
    service: Annotated[ImageGenerationService, Depends(get_images_service)],
) -> ImageJobRead:
    """Resume a manually paused image job when resources are available."""

    try:
        return await service.resume(job_id)
    except ImageGenerationServiceError as exc:
        raise _image_http_exception(exc) from exc


async def _iter_sse(
    service: ImageGenerationService, job_id: str
) -> AsyncIterator[bytes]:
    async for event in service.events(job_id):
        payload = json.dumps(event.model_dump())
        yield (
            f"id: {event.sequence}\n"
            f"event: {event.event}\n"
            f"data: {payload}\n\n"
        ).encode("utf-8")


def _image_http_exception(exc: ImageGenerationServiceError) -> HTTPException:
    status_code = (
        status.HTTP_404_NOT_FOUND
        if exc.code == "image_job_not_found"
        else status.HTTP_400_BAD_REQUEST
    )
    if exc.code in {"image_queue_full", "image_comfyui_unavailable"}:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "retryable": exc.retryable,
            }
        },
    )
