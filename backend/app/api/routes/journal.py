"""Reflection journal API routes for local, inspectable character growth."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.reflection import (
    ReflectionJournalError,
    ReflectionManager,
    get_reflection_manager,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["journal"])


def get_journal_manager() -> ReflectionManager:
    """Provide the reflection manager that owns journal persistence."""

    return get_reflection_manager()


@router.get("/journal")
async def recent_journal_entries(
    reflection_manager: Annotated[ReflectionManager, Depends(get_journal_manager)],
    limit: Annotated[int, Query(ge=1, le=50)] = 25,
) -> dict[str, list[dict[str, Any]]]:
    """Return recent active self-reflection journal entries, newest first.

    The endpoint intentionally returns bounded full entries rather than raw log
    files.  That keeps the renderer simple, preserves structured metadata for
    transparent review, and avoids any heavyweight retrieval or model work while
    the user is chatting.
    """

    try:
        entries = reflection_manager.get_recent_journal_entries(limit=limit)
    except ReflectionJournalError as exc:
        logger.warning("Unable to read reflection journal", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "The reflection journal could not be opened right now."},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": str(exc)},
        ) from exc

    return {"entries": [dict(entry) for entry in entries]}
