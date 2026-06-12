"""Extension registry, command bus, and character import routes."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import Settings, get_settings
from app.core.extensions import CharacterImportService, ExtensionEventBus, ExtensionRegistry
from app.models.extensions import (
    CharacterImportProfile,
    CharacterImportRequest,
    ExtensionCommandRequest,
    ExtensionCommandResult,
    ExtensionEvent,
    ExtensionEventScope,
    ExtensionRegistryResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/extensions", tags=["extensions"])
_registry_cache: ExtensionRegistry | None = None
_bus_cache: ExtensionEventBus | None = None


def get_extension_registry(settings: Annotated[Settings, Depends(get_settings)]) -> ExtensionRegistry:
    global _registry_cache
    if _registry_cache is None:
        _registry_cache = ExtensionRegistry(settings)
    return _registry_cache


def get_extension_event_bus(
    registry: Annotated[ExtensionRegistry, Depends(get_extension_registry)],
) -> ExtensionEventBus:
    global _bus_cache
    if _bus_cache is None:
        _bus_cache = ExtensionEventBus(registry)
    return _bus_cache


def get_character_import_service() -> CharacterImportService:
    return CharacterImportService()


@router.get("", response_model=ExtensionRegistryResponse)
def list_extensions(
    registry: Annotated[ExtensionRegistry, Depends(get_extension_registry)],
) -> ExtensionRegistryResponse:
    """Return declarative extension contracts available to the app."""

    return registry.load()


@router.post("/commands/dispatch", response_model=ExtensionCommandResult)
def dispatch_extension_command(
    request: ExtensionCommandRequest,
    bus: Annotated[ExtensionEventBus, Depends(get_extension_event_bus)],
) -> ExtensionCommandResult:
    """Validate and publish an extension command as a typed local event."""

    result = bus.dispatch(request)
    if not result.accepted:
        logger.warning(
            "Extension command rejected",
            extra={"extension_id": request.source_extension_id, "command_id": request.command_id},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": result.error.model_dump(mode="json") if result.error else None},
        )
    return result


@router.get("/events", response_model=list[ExtensionEvent])
def recent_extension_events(
    bus: Annotated[ExtensionEventBus, Depends(get_extension_event_bus)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ExtensionEvent]:
    """Return recent extension bus events for diagnostics and UI hydration."""

    return bus.recent(limit=limit)


@router.post("/events/core", response_model=ExtensionEvent)
def publish_core_event_for_diagnostics(
    bus: Annotated[ExtensionEventBus, Depends(get_extension_event_bus)],
) -> ExtensionEvent:
    """Publish a harmless core heartbeat used by tests and extension diagnostics."""

    return bus.publish_core_event("core.heartbeat", ExtensionEventScope.CORE, {"ok": True})


@router.post("/character-import/preview", response_model=CharacterImportProfile)
def preview_character_import(
    request: CharacterImportRequest,
    service: Annotated[CharacterImportService, Depends(get_character_import_service)],
) -> CharacterImportProfile:
    """Normalize SillyTavern/card JSON before any durable character write occurs."""

    return service.preview(request)
