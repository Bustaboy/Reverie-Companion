"""Character CRUD routes for Reverie's local runtime blueprints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.config import Settings, get_settings
from app.repositories.character_repo import (
    CharacterNotFoundError,
    CharacterRepositoryError,
)
from app.schemas.character_blueprint import (
    CharacterCreate,
    CharacterRecord,
    CharacterUpdate,
)
from app.services.character_service import CharacterService, build_character_service

router = APIRouter(prefix="/characters", tags=["characters"])


def get_character_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> CharacterService:
    """Provide a lightweight SQLite-backed character service."""

    return build_character_service(settings.character_db_path)


@router.post("", response_model=CharacterRecord, status_code=status.HTTP_201_CREATED)
def create_character(
    payload: CharacterCreate,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterRecord:
    """Create a persistent companion blueprint."""

    try:
        return service.create_character(
            payload.blueprint, character_id=payload.character_id
        )
    except CharacterRepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "character_already_exists",
                "message": str(exc),
                "retryable": False,
            },
        ) from exc


@router.get("", response_model=list[CharacterRecord])
def list_characters(
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> list[CharacterRecord]:
    """List active local companions."""

    return service.list_characters()


@router.get("/{character_id}", response_model=CharacterRecord)
def get_character(
    character_id: str,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterRecord:
    """Load one companion blueprint by id."""

    try:
        return service.load_by_id(character_id)
    except CharacterNotFoundError as exc:
        raise _not_found(character_id) from exc


@router.put("/{character_id}", response_model=CharacterRecord)
def update_character(
    character_id: str,
    payload: CharacterUpdate,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterRecord:
    """Replace a companion blueprint while preserving scoped ids."""

    try:
        return service.update_character(character_id, payload.blueprint)
    except CharacterNotFoundError as exc:
        raise _not_found(character_id) from exc


@router.delete(
    "/{character_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def delete_character(
    character_id: str,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> Response:
    """Soft-delete a companion so old scoped artifacts keep provenance."""

    if not service.delete_character(character_id):
        raise _not_found(character_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _not_found(character_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "character_not_found",
            "message": "That companion is not in your local library yet.",
            "details": {"character_id": character_id},
            "retryable": False,
        },
    )
