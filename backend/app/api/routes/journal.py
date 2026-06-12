"""Journal API routes for character self-reflection entries."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.reflection import ReflectionJournalError, ReflectionManager, get_reflection_manager

router = APIRouter(prefix="/journal", tags=["journal"])


class JournalReflectionMessage(BaseModel):
    """Bounded chat turn accepted by the manual reflection endpoint."""

    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=8_000)


class JournalReflectionRequest(BaseModel):
    """Manual reflection request from the local journal UI."""

    messages: list[JournalReflectionMessage] = Field(min_length=1, max_length=20)


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


@router.post("/reflections")
async def trigger_journal_reflection(
    request: JournalReflectionRequest,
    reflection_manager: Annotated[ReflectionManager, Depends(get_journal_manager)],
) -> dict[str, Any]:
    """Manually write a bounded self-reflection from recent conversation turns."""

    try:
        entry = reflection_manager.trigger_reflection(
            [message.model_dump() for message in request.messages]
        )
    except ReflectionJournalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Reverie's journal could not save a new reflection right now.",
                "details": str(exc),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Invalid reflection request.", "details": str(exc)},
        ) from exc

    return {"entry": entry}
