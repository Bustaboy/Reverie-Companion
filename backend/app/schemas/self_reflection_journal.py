"""Basic versioned schemas for character-scoped self-reflection journal entries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SELF_REFLECTION_JOURNAL_SCHEMA_VERSION = "self_reflection_journal.v1"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class SelfReflectionJournalEntry(BaseModel):
    schema_version: str = SELF_REFLECTION_JOURNAL_SCHEMA_VERSION
    entry_id: str = Field(..., min_length=1, max_length=120)
    character_id: str = Field(..., min_length=1, max_length=80)
    user_id: str = Field(default="local_user", min_length=1, max_length=80)
    timestamp: str = Field(default_factory=utc_now_iso)
    insight: str = Field(..., min_length=1, max_length=1200)
    linked_memory_id: str | None = Field(default=None, max_length=120)
    linked_journal_id: str | None = Field(default=None, max_length=120)
    status: Literal["active", "archived", "deleted"] = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SelfReflectionJournal(BaseModel):
    schema_version: str = SELF_REFLECTION_JOURNAL_SCHEMA_VERSION
    character_id: str = Field(..., min_length=1, max_length=80)
    entries: list[SelfReflectionJournalEntry] = Field(default_factory=list)
