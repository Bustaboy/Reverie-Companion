"""Extension and character import API routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.extensions import (
    CharacterImportPreview,
    CharacterImportRequest,
    ExtensionCommandRequest,
    ExtensionCommandResult,
    ExtensionEventEnvelope,
    ExtensionRegistryResponse,
)
from app.services.extension_registry import (
    CharacterImportService,
    ExtensionRegistry,
    ExtensionRegistryError,
    get_character_import_service,
    get_extension_registry,
)

router = APIRouter(prefix="/extensions", tags=["extensions"])


@router.get("", response_model=ExtensionRegistryResponse)
async def list_extensions(
    registry: Annotated[ExtensionRegistry, Depends(get_extension_registry)],
) -> ExtensionRegistryResponse:
    """Return registered extension manifests and safe UI contracts."""

    return registry.list_extensions()


@router.post("/commands", response_model=ExtensionCommandResult)
async def dispatch_extension_command(
    request: ExtensionCommandRequest,
    registry: Annotated[ExtensionRegistry, Depends(get_extension_registry)],
) -> ExtensionCommandResult:
    """Dispatch a typed command envelope onto the local extension event bus."""

    result = registry.dispatch(request)
    if not result.accepted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error)
    return result


@router.get("/events", response_model=list[ExtensionEventEnvelope])
async def recent_extension_events(
    registry: Annotated[ExtensionRegistry, Depends(get_extension_registry)],
) -> list[ExtensionEventEnvelope]:
    """Return recent command/event envelopes for diagnostics and tests."""

    return registry.recent_events()


@router.post("/character-import/preview", response_model=CharacterImportPreview)
async def preview_character_import(
    request: CharacterImportRequest,
    importer: Annotated[CharacterImportService, Depends(get_character_import_service)],
) -> CharacterImportPreview:
    """Normalize SillyTavern/character-card data before committing it."""

    try:
        return importer.preview(request)
    except ExtensionRegistryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": exc.code, "message": exc.message}) from exc
    except Exception as exc:  # pragma: no cover - defensive isolation.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "character_import_failed", "message": "The character card could not be parsed safely."},
        ) from exc
