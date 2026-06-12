"""Memory Browser API routes for inspecting and editing long-term memories."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, field_validator

from app.core.memory import MemoryError, MemoryManager, get_memory_manager

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryUpdateRequest(BaseModel):
    """Editable fields exposed by the local Memory Browser."""

    text: str = Field(..., min_length=1, max_length=8_000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    importance: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            clean = " ".join(str(tag).strip().lower().split())
            if clean and clean not in seen:
                normalized.append(clean[:48])
                seen.add(clean)
        return normalized


class MemoryBulkDeleteRequest(BaseModel):
    """Bulk delete request for selected or older memories."""

    ids: list[str] = Field(default_factory=list, max_length=250)
    older_than: datetime | None = None


class MemoryBulkDeleteResponse(BaseModel):
    """Count of memories removed by a bulk delete/prune operation."""

    deleted_count: int


def get_memory_browser_manager() -> MemoryManager:
    """Provide the process-local memory manager for Memory Browser routes."""

    return get_memory_manager()


@router.get("/memories")
async def list_memories(
    memory_manager: Annotated[MemoryManager, Depends(get_memory_browser_manager)],
    q: Annotated[str, Query(max_length=200)] = "",
    character: Annotated[str, Query(max_length=120)] = "",
    theme: Annotated[str, Query(max_length=80)] = "",
    source: Annotated[str, Query(max_length=80)] = "",
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=5, le=50)] = 20,
) -> dict[str, Any]:
    """Return a paginated, filterable list of editable long-term memories."""

    try:
        result = memory_manager.list_memories(
            query=q,
            character=character,
            theme=theme,
            source=source,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
    except MemoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Reverie's memory library could not be opened right now.",
                "details": str(exc),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Invalid memory browser request.", "details": str(exc)},
        ) from exc
    return result


@router.get("/memories/{memory_id}")
async def get_memory(
    memory_id: str,
    memory_manager: Annotated[MemoryManager, Depends(get_memory_browser_manager)],
) -> dict[str, Any]:
    """Return one memory with full provenance metadata."""

    memory = memory_manager.get_memory(memory_id)
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "That memory could not be found."},
        )
    return {"memory": memory}


@router.patch("/memories/{memory_id}")
async def update_memory(
    memory_id: str,
    request: MemoryUpdateRequest,
    memory_manager: Annotated[MemoryManager, Depends(get_memory_browser_manager)],
) -> dict[str, Any]:
    """Update editable memory text, tags, importance, and review metadata."""

    try:
        memory = memory_manager.update_memory(
            memory_id,
            text=request.text,
            tags=request.tags,
            importance=request.importance,
            metadata=request.metadata,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "That memory could not be found."},
        ) from exc
    except MemoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "The memory could not be updated.", "details": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Invalid memory update.", "details": str(exc)},
        ) from exc
    return {"memory": memory}


@router.delete(
    "/memories/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_memory(
    memory_id: str,
    memory_manager: Annotated[MemoryManager, Depends(get_memory_browser_manager)],
) -> Response:
    """Permanently delete one memory so it can no longer be retrieved."""

    try:
        deleted = memory_manager.delete_memory(memory_id)
    except MemoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "The memory could not be deleted.", "details": str(exc)},
        ) from exc
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "That memory could not be found."},
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/memories/bulk-delete")
async def bulk_delete_memories(
    request: MemoryBulkDeleteRequest,
    memory_manager: Annotated[MemoryManager, Depends(get_memory_browser_manager)],
) -> MemoryBulkDeleteResponse:
    """Delete selected memories or prune older memories after UI confirmation."""

    if not request.ids and request.older_than is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Choose memories or an older-than date before pruning."},
        )
    try:
        deleted_count = memory_manager.bulk_delete_memories(
            ids=request.ids,
            older_than=request.older_than,
        )
    except MemoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "The selected memories could not be deleted.", "details": str(exc)},
        ) from exc
    return MemoryBulkDeleteResponse(deleted_count=deleted_count)
