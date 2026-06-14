"""Character runtime API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.config import Settings, get_settings
from app.repositories.character_repo import CharacterRepositoryError
from app.repositories.creator_draft_repo import CreatorDraftRepositoryError
from app.schemas.character_blueprint import (
    CharacterCreate,
    CharacterListResponse,
    CharacterResponse,
    CharacterUpdate,
)
from app.services.character_creator_service import (
    CharacterCreatorDraftCreate,
    CharacterCreatorDraftListResponse,
    CharacterCreatorDraftResponse,
    CharacterCreatorDraftUpdate,
    CharacterCreatorService,
    CreatorDraftNotFoundError,
    DraftMomentCaptureRequest,
    DraftValidationResponse,
    DraftPreviewRequest,
    DraftPreviewResponse,
    CharacterCreatorDraft,
    PersistedDraftMomentCaptureRequest,
    PersistedDraftPreviewRequest,
)
from app.services.character_service import CharacterNotFoundError, CharacterService
from app.services.moment_capture_service import MomentCaptureResponse

router = APIRouter(prefix="/api/characters", tags=["characters"])


def get_character_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> CharacterService:
    return CharacterService.from_settings(settings)


def get_creator_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> CharacterCreatorService:
    return CharacterCreatorService.from_settings(settings)


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


def _draft_repository_exception(exc: CreatorDraftRepositoryError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "error": exc.user_message,
            "code": "creator_draft_store_unavailable",
        },
    )


def _draft_not_found_exception(exc: CreatorDraftNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": str(exc),
            "code": "creator_draft_not_found",
            "draft_id": exc.draft_id,
        },
    )


@router.post("/creator/validate", response_model=DraftValidationResponse)
def validate_creator_draft(request: CharacterCreatorDraft) -> DraftValidationResponse:
    """Validate and map an unsaved creator draft into a CharacterBlueprint."""

    return CharacterCreatorService().validate_draft(request)


@router.post(
    "/creator/drafts",
    response_model=CharacterCreatorDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_creator_draft(
    request: CharacterCreatorDraftCreate,
    service: Annotated[CharacterCreatorService, Depends(get_creator_service)],
) -> CharacterCreatorDraftResponse:
    """Create and persist a creator draft without finalizing a character."""

    try:
        return service.create_draft(request)
    except CreatorDraftRepositoryError as exc:
        raise _draft_repository_exception(exc) from exc


@router.get("/creator/drafts", response_model=CharacterCreatorDraftListResponse)
def list_creator_drafts(
    service: Annotated[CharacterCreatorService, Depends(get_creator_service)],
) -> CharacterCreatorDraftListResponse:
    try:
        return service.list_drafts()
    except CreatorDraftRepositoryError as exc:
        raise _draft_repository_exception(exc) from exc


@router.get("/creator/drafts/{draft_id}", response_model=CharacterCreatorDraftResponse)
def get_creator_draft(
    draft_id: str,
    service: Annotated[CharacterCreatorService, Depends(get_creator_service)],
) -> CharacterCreatorDraftResponse:
    try:
        return service.load_draft(draft_id)
    except CreatorDraftNotFoundError as exc:
        raise _draft_not_found_exception(exc) from exc
    except CreatorDraftRepositoryError as exc:
        raise _draft_repository_exception(exc) from exc


@router.patch(
    "/creator/drafts/{draft_id}", response_model=CharacterCreatorDraftResponse
)
def update_creator_draft(
    draft_id: str,
    request: CharacterCreatorDraftUpdate,
    service: Annotated[CharacterCreatorService, Depends(get_creator_service)],
) -> CharacterCreatorDraftResponse:
    try:
        return service.update_draft(draft_id, request)
    except CreatorDraftNotFoundError as exc:
        raise _draft_not_found_exception(exc) from exc
    except CreatorDraftRepositoryError as exc:
        raise _draft_repository_exception(exc) from exc


@router.post(
    "/creator/drafts/{draft_id}/validate",
    response_model=DraftValidationResponse,
)
def validate_persisted_creator_draft(
    draft_id: str,
    service: Annotated[CharacterCreatorService, Depends(get_creator_service)],
) -> DraftValidationResponse:
    try:
        return service.validate_persisted_draft(draft_id)
    except CreatorDraftNotFoundError as exc:
        raise _draft_not_found_exception(exc) from exc
    except CreatorDraftRepositoryError as exc:
        raise _draft_repository_exception(exc) from exc


@router.delete(
    "/creator/drafts/{draft_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def delete_creator_draft(
    draft_id: str,
    service: Annotated[CharacterCreatorService, Depends(get_creator_service)],
) -> None:
    try:
        if not service.delete_draft(draft_id):
            raise CreatorDraftNotFoundError(draft_id)
    except CreatorDraftNotFoundError as exc:
        raise _draft_not_found_exception(exc) from exc
    except CreatorDraftRepositoryError as exc:
        raise _draft_repository_exception(exc) from exc


@router.post("/creator/greeting-preview", response_model=DraftPreviewResponse)
def create_creator_greeting_preview(
    request: DraftPreviewRequest,
) -> DraftPreviewResponse:
    """Generate a non-persisted first-message preview from an unsaved draft."""

    return CharacterCreatorService().generate_greeting_preview(
        request.draft, include_prompt_context=request.include_prompt_context
    )


@router.post("/creator/example-dialogue-previews", response_model=DraftPreviewResponse)
def create_creator_example_dialogue_previews(
    request: DraftPreviewRequest,
) -> DraftPreviewResponse:
    """Generate non-persisted example dialogue previews from an unsaved draft."""

    return CharacterCreatorService().generate_example_dialogue_previews(
        request.draft, include_prompt_context=request.include_prompt_context
    )


@router.post(
    "/creator/drafts/{draft_id}/greeting-preview", response_model=DraftPreviewResponse
)
def create_persisted_creator_greeting_preview(
    draft_id: str,
    request: PersistedDraftPreviewRequest,
    service: Annotated[CharacterCreatorService, Depends(get_creator_service)],
) -> DraftPreviewResponse:
    """Generate a first-message preview from a persisted draft without saving it."""

    try:
        return service.generate_persisted_greeting_preview(draft_id, request)
    except CreatorDraftNotFoundError as exc:
        raise _draft_not_found_exception(exc) from exc
    except CreatorDraftRepositoryError as exc:
        raise _draft_repository_exception(exc) from exc


@router.post(
    "/creator/drafts/{draft_id}/example-dialogue-previews",
    response_model=DraftPreviewResponse,
)
def create_persisted_creator_example_dialogue_previews(
    draft_id: str,
    request: PersistedDraftPreviewRequest,
    service: Annotated[CharacterCreatorService, Depends(get_creator_service)],
) -> DraftPreviewResponse:
    """Generate example dialogue previews from a persisted draft without saving them."""

    try:
        return service.generate_persisted_example_dialogue_previews(draft_id, request)
    except CreatorDraftNotFoundError as exc:
        raise _draft_not_found_exception(exc) from exc
    except CreatorDraftRepositoryError as exc:
        raise _draft_repository_exception(exc) from exc


@router.post(
    "/creator/drafts/{draft_id}/first-portrait",
    response_model=MomentCaptureResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_persisted_creator_first_portrait(
    draft_id: str,
    request: PersistedDraftMomentCaptureRequest,
    service: Annotated[CharacterCreatorService, Depends(get_creator_service)],
) -> MomentCaptureResponse:
    """Queue first-portrait Moment Capture from a persisted draft."""

    try:
        return await service.capture_persisted_first_portrait(draft_id, request)
    except CreatorDraftNotFoundError as exc:
        raise _draft_not_found_exception(exc) from exc
    except CreatorDraftRepositoryError as exc:
        raise _draft_repository_exception(exc) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "creator_draft_invalid",
                    "message": str(exc),
                    "retryable": False,
                }
            },
        ) from exc


@router.post(
    "/creator/first-portrait",
    response_model=MomentCaptureResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_creator_first_portrait(
    request: DraftMomentCaptureRequest,
) -> MomentCaptureResponse:
    """Queue draft first-portrait Moment Capture without saving the character."""

    try:
        return await CharacterCreatorService().capture_first_portrait(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "creator_draft_invalid",
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
