"""Journal API routes for character self-reflection entries."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.reflection import ReflectionJournalError, ReflectionManager, get_reflection_manager

router = APIRouter(prefix="/journal", tags=["journal"])


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
