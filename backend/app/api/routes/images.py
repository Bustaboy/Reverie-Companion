"""Image generation API routes."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse

from app.core.config import Settings, get_settings
from app.models.image import ImageGenerateRequest, ImageGenerateResponse, ImageJobRead
from app.services.image_generation_service import (
    ImageGenerationError,
    ImageGenerationService,
    get_image_generation_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/images", tags=["images"])
SSE_MEDIA_TYPE = "text/event-stream; charset=utf-8"
SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def get_images_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ImageGenerationService:
    if not settings.image_generation_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "image_generation_disabled",
                    "message": "Image generation is disabled in settings.",
                    "details": {},
                    "retryable": False,
                }
            },
        )
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
    """Queue a local ComfyUI image generation job without blocking chat or TTS."""

    request_id = str(uuid4())
    try:
        job = await service.submit(request)
    except ImageGenerationError as exc:
        raise _image_http_exception(exc, status_code=status.HTTP_409_CONFLICT) from exc
    logger.info(
        "Queued image generation job",
        extra={
            "request_id": request_id,
            "job_id": job.job_id,
            "preset": job.requested_preset,
        },
    )
    return ImageGenerateResponse(request_id=request_id, job=job)


@router.get("/{job_id}", response_model=ImageJobRead)
async def get_image_job(
    job_id: str,
    service: Annotated[ImageGenerationService, Depends(get_images_service)],
) -> ImageJobRead:
    try:
        return service.get_job(job_id)
    except ImageGenerationError as exc:
        raise _image_http_exception(exc, status_code=status.HTTP_404_NOT_FOUND) from exc


@router.get("/{job_id}/outputs/{filename}")
async def get_image_output(
    job_id: str,
    filename: str,
    service: Annotated[ImageGenerationService, Depends(get_images_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse | RedirectResponse:
    """Serve completed local image outputs without exposing arbitrary paths."""

    try:
        job = service.get_job(job_id)
    except ImageGenerationError as exc:
        raise _image_http_exception(exc, status_code=status.HTTP_404_NOT_FOUND) from exc

    safe_name = Path(filename).name
    output_names = {Path(output_path).name for output_path in job.output_paths}
    if safe_name not in output_names:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image output was not found for this job.",
        )

    output_path = (Path(settings.image_generation_output_dir) / safe_name).resolve()
    output_root = Path(settings.image_generation_output_dir).resolve()
    if output_root not in output_path.parents and output_path != output_root:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image output path is invalid.",
        )
    if output_path.is_file():
        return FileResponse(output_path)

    comfy_query = urlencode({'filename': safe_name, 'type': 'output'})
    comfy_base_url = settings.image_generation_comfyui_url.rstrip('/')
    comfy_view_url = f'{comfy_base_url}/view?{comfy_query}'
    return RedirectResponse(comfy_view_url)


@router.post("/{job_id}/cancel", response_model=ImageJobRead)
async def cancel_image_job(
    job_id: str,
    service: Annotated[ImageGenerationService, Depends(get_images_service)],
) -> ImageJobRead:
    try:
        return await service.cancel(job_id)
    except ImageGenerationError as exc:
        raise _image_http_exception(exc, status_code=status.HTTP_404_NOT_FOUND) from exc


@router.get("/{job_id}/events")
async def image_job_events(
    job_id: str,
    service: Annotated[ImageGenerationService, Depends(get_images_service)],
) -> StreamingResponse:
    """Stream ordered image job lifecycle/progress events via SSE."""

    try:
        service.get_job(job_id)
    except ImageGenerationError as exc:
        raise _image_http_exception(exc, status_code=status.HTTP_404_NOT_FOUND) from exc
    return StreamingResponse(
        _iter_sse(service, job_id),
        media_type=SSE_MEDIA_TYPE,
        headers=SSE_HEADERS,
    )


async def _iter_sse(
    service: ImageGenerationService, job_id: str
) -> AsyncIterator[bytes]:
    async for event in service.events(job_id):
        payload = event.model_dump(mode="json")
        yield f"id: {event.sequence}\nevent: {event.event}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n".encode(
            "utf-8"
        )


def _image_http_exception(
    exc: ImageGenerationError, *, status_code: int
) -> HTTPException:
    logger.warning(
        "Image request failed", extra={"code": exc.code, "retryable": exc.retryable}
    )
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
