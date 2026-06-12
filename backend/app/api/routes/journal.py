"""Journal API routes for character self-reflection entries."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.reflection import ReflectionJournalError, ReflectionManager, get_reflection_manager

router = APIRouter(prefix="/journal", tags=["journal"])


class JournalReflectionMessage(BaseModel):
    """Bounded message evidence used for a manual diary reflection."""

    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=8_000)


class JournalReflectionRequest(BaseModel):
    """Manual reflection request from the Journal view."""

    messages: list[JournalReflectionMessage] = Field(..., min_length=1, max_length=50)


def get_journal_manager() -> ReflectionManager:
    """Provide the process-local reflection manager for journal reads."""

    return get_reflection_manager()


@router.get("/entries")
async def recent_journal_entries(
    reflection_manager: Annotated[ReflectionManager, Depends(get_journal_manager)],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=50,
            description="Maximum number of recent active journal entries to return.",
        ),
    ] = 20,
) -> dict[str, Any]:
    """Return recent active self-reflection journal entries, newest first."""

    try:
        entries = reflection_manager.get_recent_journal_entries(limit=limit)
    except ReflectionJournalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Reverie's journal could not be opened right now.",
                "details": str(exc),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Invalid journal request.", "details": str(exc)},
        ) from exc

    return {"entries": entries, "count": len(entries)}


@router.post("/reflect", status_code=status.HTTP_201_CREATED)
async def manual_journal_reflection(
    request: JournalReflectionRequest,
    reflection_manager: Annotated[ReflectionManager, Depends(get_journal_manager)],
) -> dict[str, Any]:
    """Create a new local journal entry from bounded conversation evidence."""

    history = [message.model_dump() for message in request.messages]
    try:
        entry = reflection_manager.trigger_reflection(history)
    except ReflectionJournalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Reverie could not write the reflection right now.",
                "details": str(exc),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Invalid reflection request.", "details": str(exc)},
        ) from exc

    return {"entry": entry}
