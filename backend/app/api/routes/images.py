"""Image generation API routes."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse

from app.core.config import Settings, get_settings
from app.models.image import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    ImageHistoryResponse,
    ImageJobRead,
    ImageSaveToAssetsRequest,
    ImageSaveToAssetsResponse,
)
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


@router.get("/history/{conversation_id}", response_model=ImageHistoryResponse)
async def get_image_history(
    conversation_id: str,
    service: Annotated[ImageGenerationService, Depends(get_images_service)],
    character_id: str | None = Query(default=None, min_length=1, max_length=120),
    session_id: str | None = Query(default=None, min_length=1, max_length=120),
) -> ImageHistoryResponse:
    return service.list_history(
        conversation_id, character_id=character_id, session_id=session_id
    )


@router.delete("/history/{job_id}", response_model=ImageHistoryResponse)
async def delete_image_history_item(
    job_id: str,
    service: Annotated[ImageGenerationService, Depends(get_images_service)],
) -> ImageHistoryResponse:
    try:
        return await service.delete_history_item(job_id)
    except ImageGenerationError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND if not exc.retryable else status.HTTP_409_CONFLICT
        )
        raise _image_http_exception(exc, status_code=status_code) from exc


@router.post("/{job_id}/save-to-assets", response_model=ImageSaveToAssetsResponse)
async def save_image_to_character_assets(
    job_id: str,
    request: ImageSaveToAssetsRequest,
    service: Annotated[ImageGenerationService, Depends(get_images_service)],
) -> ImageSaveToAssetsResponse:
    try:
        return await service.save_to_character_assets(
            job_id,
            character_id=request.character_id,
            output_index=request.output_index,
            asset_label=request.asset_label,
        )
    except ImageGenerationError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND if not exc.retryable else status.HTTP_409_CONFLICT
        )
        raise _image_http_exception(exc, status_code=status_code) from exc


@router.get("/{job_id}", response_model=ImageJobRead)
async def get_image_job(
    job_id: str,
    service: Annotated[ImageGenerationService, Depends(get_images_service)],
) -> ImageJobRead:
    try:
        return service.get_job(job_id)
    except ImageGenerationError as exc:
        raise _image_http_exception(exc, status_code=status.HTTP_404_NOT_FOUND) from exc


@router.get("/{job_id}/outputs/{output_index}")
async def get_image_output(
    job_id: str,
    output_index: int,
    service: Annotated[ImageGenerationService, Depends(get_images_service)],
):
    """Serve only files that are already attached to a completed image job.

    Local files are returned directly when they resolve under Reverie's configured
    output directory. If ComfyUI owns the file, redirect to its /view endpoint for
    the same job-attached output reference rather than accepting arbitrary paths
    from the frontend.
    """

    try:
        reference = service.get_output_reference(job_id, output_index)
    except ImageGenerationError as exc:
        raise _image_http_exception(exc, status_code=status.HTTP_404_NOT_FOUND) from exc

    if reference.local_path is not None:
        return FileResponse(reference.local_path)
    if reference.comfyui_view_url is not None:
        return RedirectResponse(
            reference.comfyui_view_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )

    raise _image_http_exception(
        ImageGenerationError(
            "Image output is no longer available locally.",
            code="image_output_unavailable",
            retryable=True,
            details={"job_id": job_id, "output_index": output_index},
        ),
        status_code=status.HTTP_404_NOT_FOUND,
    )


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
