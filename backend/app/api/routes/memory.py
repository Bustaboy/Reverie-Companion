"""User-visible memory browser controls for long-term recall."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.memory import MemoryError, MemoryManager, get_memory_manager

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryUpdateRequest(BaseModel):
    """Patchable fields for an existing long-term memory."""

    text: str | None = Field(default=None, min_length=1, max_length=8_000)
    metadata: dict[str, Any] | None = None


class MemoryBulkDeleteRequest(BaseModel):
    """Bulk deletion controls for explicit selection or old-memory pruning."""

    ids: list[str] = Field(default_factory=list, max_length=200)
    older_than: str | None = None
    query: str | None = Field(default=None, max_length=500)
    character: str | None = Field(default=None, max_length=120)
    theme: str | None = Field(default=None, max_length=120)
    memory_type: str | None = Field(default=None, max_length=120)
    max_delete: int = Field(default=100, ge=1, le=500)


def get_manager() -> MemoryManager:
    """Provide the process-local memory manager."""

    return get_memory_manager()


@router.get("")
async def list_memories(
    manager: Annotated[MemoryManager, Depends(get_manager)],
    query: str = Query(default="", max_length=500),
    character: str = Query(default="", max_length=120),
    theme: str = Query(default="", max_length=120),
    memory_type: str = Query(default="", max_length=120),
    start_date: str = Query(default="", max_length=40),
    end_date: str = Query(default="", max_length=40),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
) -> dict[str, Any]:
    """Return paginated, filterable long-term memories without prompt injection."""

    try:
        return manager.list_memories(
            query=query,
            character=character,
            theme=theme,
            memory_type=memory_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except MemoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


@router.patch("/{memory_id}")
async def update_memory(
    memory_id: str,
    update: MemoryUpdateRequest,
    manager: Annotated[MemoryManager, Depends(get_manager)],
) -> dict[str, Any]:
    """Update memory text or metadata and refresh its local embedding."""

    try:
        return {
            "memory": manager.update_memory(
                memory_id, text=update.text, metadata=update.metadata
            )
        }
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except MemoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    manager: Annotated[MemoryManager, Depends(get_manager)],
) -> dict[str, Any]:
    """Delete one memory from the durable local browser store."""

    try:
        return {"deleted": manager.delete_memory(memory_id), "memory_id": memory_id}
    except MemoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


@router.post("/bulk-delete")
async def bulk_delete_memories(
    request: MemoryBulkDeleteRequest,
    manager: Annotated[MemoryManager, Depends(get_manager)],
) -> dict[str, Any]:
    """Bulk-delete selected memories or prune memories matching conservative filters."""

    try:
        return manager.bulk_delete_memories(
            ids=request.ids,
            older_than=request.older_than,
            query=request.query,
            character=request.character,
            theme=request.theme,
            memory_type=request.memory_type,
            max_delete=request.max_delete,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except MemoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
