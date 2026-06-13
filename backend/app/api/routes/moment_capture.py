"""Moment Capture API routes."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.routes.images import get_images_service
from app.core.config import Settings, get_settings
from app.schemas.moment_capture import (
    MomentCaptureRequest,
    VisualChangeCanonStatus,
    VisualChangeEvent,
    VisualChangeReviewRequest,
    VisualChangeReviewResponse,
    VisualFeedbackRequest,
    VisualFeedbackResponse,
)
from app.services.character_service import CharacterNotFoundError, CharacterService
from app.services.image_generation_service import (
    ImageGenerationError,
    ImageGenerationService,
)
from app.services.moment_capture_service import (
    MomentCaptureResponse,
    MomentCaptureService,
)

logger = logging.getLogger(__name__)

# Keep Moment Capture at a top-level companion-native route instead of nesting it
# under /api/images. Although the orchestration queues an image job, this API is
# a character/session capture workflow that also creates durable capture records
# for gallery, memory, and future review flows. Generic image controls remain
# grouped under /api/images.
router = APIRouter(prefix="/api/moment-capture", tags=["moment-capture"])


def get_character_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> CharacterService:
    return CharacterService.from_settings(settings)


def get_moment_capture_service(
    settings: Annotated[Settings, Depends(get_settings)],
    character_service: Annotated[CharacterService, Depends(get_character_service)],
    image_service: Annotated[ImageGenerationService, Depends(get_images_service)],
) -> MomentCaptureService:
    return MomentCaptureService(
        settings=settings,
        character_service=character_service,
        image_service=image_service,
    )


@router.post(
    "", response_model=MomentCaptureResponse, status_code=status.HTTP_202_ACCEPTED
)
async def create_moment_capture(
    request: MomentCaptureRequest,
    service: Annotated[MomentCaptureService, Depends(get_moment_capture_service)],
) -> MomentCaptureResponse:
    """Queue a character-linked Moment Capture job without waiting for output."""

    try:
        return await service.capture(request)
    except CharacterNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "character_not_found",
                    "message": (
                        "Requested character_id was not found; Moment Capture "
                        "requires an explicit existing character."
                    ),
                    "details": {"character_id": exc.character_id},
                    "retryable": False,
                }
            },
        ) from exc
    except ImageGenerationError as exc:
        logger.warning(
            "Moment Capture image queue rejected request", extra={"code": exc.code}
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "retryable": exc.retryable,
                }
            },
        ) from exc


@router.post("/{capture_id}/feedback", response_model=VisualFeedbackResponse)
async def submit_moment_capture_feedback(
    capture_id: str,
    request: VisualFeedbackRequest,
    service: Annotated[MomentCaptureService, Depends(get_moment_capture_service)],
) -> VisualFeedbackResponse:
    """Persist user visual feedback and create reviewable change events when needed."""

    try:
        return service.submit_feedback(capture_id, request)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="capture_not_found"
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.get("/visual-changes", response_model=list[VisualChangeEvent])
async def list_visual_changes(
    service: Annotated[MomentCaptureService, Depends(get_moment_capture_service)],
    character_id: str | None = None,
    status_filter: VisualChangeCanonStatus | None = VisualChangeCanonStatus.proposed,
) -> list[VisualChangeEvent]:
    """List pending visual change events by default for minimal review UI."""

    return service.list_visual_changes(status=status_filter, character_id=character_id)


@router.get("/visual-changes/{event_id}", response_model=VisualChangeEvent)
async def read_visual_change(
    event_id: str,
    service: Annotated[MomentCaptureService, Depends(get_moment_capture_service)],
) -> VisualChangeEvent:
    """Read one visual change event with provenance and rollback metadata."""

    event = service.get_visual_change(event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="visual_change_not_found"
        )
    return event


@router.post(
    "/visual-changes/{event_id}/approve", response_model=VisualChangeReviewResponse
)
async def approve_visual_change(
    event_id: str,
    request: VisualChangeReviewRequest,
    service: Annotated[MomentCaptureService, Depends(get_moment_capture_service)],
) -> VisualChangeReviewResponse:
    try:
        return service.approve_visual_change(event_id, request)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="visual_change_not_found"
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.post(
    "/visual-changes/{event_id}/reject", response_model=VisualChangeReviewResponse
)
async def reject_visual_change(
    event_id: str,
    request: VisualChangeReviewRequest,
    service: Annotated[MomentCaptureService, Depends(get_moment_capture_service)],
) -> VisualChangeReviewResponse:
    try:
        return service.reject_visual_change(event_id, request)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="visual_change_not_found"
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.post(
    "/visual-changes/{event_id}/rollback", response_model=VisualChangeReviewResponse
)
async def rollback_visual_change(
    event_id: str,
    request: VisualChangeReviewRequest,
    service: Annotated[MomentCaptureService, Depends(get_moment_capture_service)],
) -> VisualChangeReviewResponse:
    try:
        return service.rollback_visual_change(event_id, request)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="visual_change_not_found"
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
