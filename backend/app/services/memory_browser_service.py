"""User-facing Memory Browser service layer.

This module intentionally keeps inspection/edit/delete workflows separate from
chat retrieval and prompt-context assembly. Chat should continue to call the
narrow RAG methods on ``MemoryManager`` (`search_memories` and
`get_relevant_context`), while routes for the Memory Browser go through this
service so audit/control behavior can evolve without changing chat orchestration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.memory import MemoryManager, MemorySearchResult, get_memory_manager


class MemoryBrowserService:
    """Coordinate paginated memory review and editable controls."""

    def __init__(self, memory_manager: MemoryManager | None = None) -> None:
        self._memory_manager = memory_manager or get_memory_manager()

    def list_memories(
        self,
        *,
        query: str = "",
        character: str = "",
        theme: str = "",
        source: str = "",
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Return a lightweight, paginated audit view of memories."""

        return self._memory_manager.list_memories(
            query=query,
            character=character,
            theme=theme,
            source=source,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )

    def get_memory(self, memory_id: str) -> MemorySearchResult | None:
        """Return one memory with provenance metadata for review."""

        return self._memory_manager.get_memory(memory_id)

    def update_memory(
        self,
        memory_id: str,
        *,
        text: str,
        tags: list[str] | None = None,
        importance: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemorySearchResult:
        """Apply a user edit while preserving provenance and refreshing embeddings."""

        return self._memory_manager.update_memory(
            memory_id,
            text=text,
            tags=tags,
            importance=importance,
            metadata=metadata,
        )

    def delete_memory(self, memory_id: str) -> bool:
        """Permanently remove one memory from the recall table."""

        return self._memory_manager.delete_memory(memory_id)

    def bulk_delete_memories(
        self, *, ids: list[str] | None = None, older_than: datetime | None = None
    ) -> int:
        """Delete selected memories and/or prune memories before a date."""

        return self._memory_manager.bulk_delete_memories(ids=ids, older_than=older_than)


_memory_browser_service: MemoryBrowserService | None = None


def get_memory_browser_service() -> MemoryBrowserService:
    """Return the process-local Memory Browser service singleton."""

    global _memory_browser_service
    if _memory_browser_service is None:
        _memory_browser_service = MemoryBrowserService()
    return _memory_browser_service


__all__ = ["MemoryBrowserService", "get_memory_browser_service"]
