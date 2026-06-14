"""Character runtime API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.config import Settings, get_settings
from app.api.routes.moment_capture import get_moment_capture_service
from app.repositories.character_repo import CharacterRepositoryError
from app.schemas.character_blueprint import (
    CharacterCreate,
    CharacterListResponse,
    CharacterResponse,
    CharacterUpdate,
)
from app.services.character_creator_service import (
    CharacterCreatorDraft,
    CharacterCreatorService,
    CharacterDraftValidationResponse,
    CreatorMomentCaptureRequest,
)
from app.services.character_service import CharacterNotFoundError, CharacterService
from app.services.moment_capture_service import (
    MomentCaptureResponse,
    MomentCaptureService,
)

router = APIRouter(prefix="/api/characters", tags=["characters"])


def get_character_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> CharacterService:
    return CharacterService.from_settings(settings)


def get_character_creator_service(
    moment_capture_service: Annotated[
        MomentCaptureService, Depends(get_moment_capture_service)
    ],
) -> CharacterCreatorService:
    return CharacterCreatorService(moment_capture_service=moment_capture_service)


def _not_found_exception(exc: CharacterNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": exc.user_message,
            "code": "character_not_found",
            "character_id": exc.character_id,
        },
    )


def _repository_exception(exc: CharacterRepositoryError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "error": exc.user_message,
            "code": "character_library_unavailable",
        },
    )


@router.post("/creator/validate", response_model=CharacterDraftValidationResponse)
def validate_creator_draft(
    request: CharacterCreatorDraft,
    service: Annotated[CharacterCreatorService, Depends(get_character_creator_service)],
) -> CharacterDraftValidationResponse:
    """Validate that a request-scoped creator draft can become a blueprint."""

    return service.validate_draft(request)


@router.post(
    "/creator/portrait-capture",
    response_model=MomentCaptureResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def capture_creator_first_portrait(
    request: CreatorMomentCaptureRequest,
    service: Annotated[CharacterCreatorService, Depends(get_character_creator_service)],
) -> MomentCaptureResponse:
    """Queue first-portrait Moment Capture from chat or VN creator context."""

    try:
        return await service.capture_first_portrait(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "creator_draft_capture_invalid",
                    "message": str(exc),
                    "retryable": False,
                }
            },
        ) from exc


@router.post("", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
def create_character(
    request: CharacterCreate,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterResponse:
    """Create a durable local character blueprint."""

    try:
        return CharacterResponse(character=service.create(request))
    except CharacterRepositoryError as exc:
        raise _repository_exception(exc) from exc


@router.get("", response_model=CharacterListResponse)
def list_characters(
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterListResponse:
    try:
        return CharacterListResponse(characters=service.list())
    except CharacterRepositoryError as exc:
        raise _repository_exception(exc) from exc


@router.get("/{character_id}", response_model=CharacterResponse)
def get_character(
    character_id: str,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterResponse:
    try:
        return CharacterResponse(character=service.load_by_id(character_id))
    except CharacterNotFoundError as exc:
        raise _not_found_exception(exc) from exc
    except CharacterRepositoryError as exc:
        raise _repository_exception(exc) from exc


@router.patch("/{character_id}", response_model=CharacterResponse)
def update_character(
    character_id: str,
    request: CharacterUpdate,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterResponse:
    try:
        return CharacterResponse(character=service.update(character_id, request))
    except CharacterNotFoundError as exc:
        raise _not_found_exception(exc) from exc
    except CharacterRepositoryError as exc:
        raise _repository_exception(exc) from exc


@router.delete(
    "/{character_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def delete_character(
    character_id: str,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> None:
    try:
        if not service.delete(character_id):
            raise CharacterNotFoundError(character_id)
    except CharacterNotFoundError as exc:
        raise _not_found_exception(exc) from exc
    except CharacterRepositoryError as exc:
        raise _repository_exception(exc) from exc
