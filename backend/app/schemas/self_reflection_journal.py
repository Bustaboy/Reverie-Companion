"""Pydantic basics for character-scoped self-reflection journal entries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

SELF_REFLECTION_JOURNAL_VERSION = "self_reflection_journal.v1"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class SelfReflectionJournalEntry(BaseModel):
    schema_version: str = SELF_REFLECTION_JOURNAL_VERSION
    entry_id: str = Field(..., min_length=1, max_length=120)
    character_id: str = Field(..., min_length=1, max_length=80)
    timestamp: str = Field(default_factory=utc_now_iso)
    insight: str = Field(..., min_length=1, max_length=1200)
    linked_memory_id: str | None = Field(default=None, max_length=120)
    linked_memory_ids: list[str] = Field(default_factory=list, max_length=12)
    themes: list[str] = Field(default_factory=list, max_length=12)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("themes", "linked_memory_ids", mode="after")
    @classmethod
    def normalize_list(cls, values: list[str]) -> list[str]:
        output: list[str] = []
        for value in values:
            item = value.strip()[:80]
            if item and item not in output:
                output.append(item)
        return output
