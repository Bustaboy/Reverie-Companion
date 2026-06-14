"""SQLite persistence for character creator drafts.

Drafts intentionally live in their own table so incomplete creator work cannot be
mistaken for finalized ``CharacterBlueprint`` records. The table stores the full
versioned draft JSON losslessly, plus lightweight indexed metadata for list/load
operations and later migrations.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeVar

from pydantic import ValidationError

from app.services.character_creator_service import CharacterCreatorDraftRecord

T = TypeVar("T")


class CreatorDraftRepositoryError(RuntimeError):
    """Raised when draft persistence cannot safely read or write local data."""

    user_message = (
        "Your character draft needs a gentle moment before it can save or load. "
        "Nothing was finalized or published—try again in a moment."
    )

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.user_message)


class CreatorDraftRepository:
    """Persist creator drafts separately from finalized character blueprints."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        def operation() -> None:
            with self._connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS character_creator_drafts (
                        draft_id TEXT PRIMARY KEY,
                        schema_version INTEGER NOT NULL,
                        lifecycle_state TEXT NOT NULL,
                        display_name TEXT NOT NULL,
                        character_id TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        draft_json TEXT NOT NULL,
                        CHECK (length(draft_id) > 0),
                        CHECK (length(display_name) > 0),
                        CHECK (json_valid(draft_json))
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_character_creator_drafts_updated_at
                        ON character_creator_drafts(updated_at)
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_character_creator_drafts_display_name
                        ON character_creator_drafts(display_name COLLATE NOCASE)
                    """
                )

        self._guard(operation)

    def upsert(self, record: CharacterCreatorDraftRecord) -> CharacterCreatorDraftRecord:
        def operation() -> CharacterCreatorDraftRecord:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO character_creator_drafts (
                        draft_id, schema_version, lifecycle_state, display_name,
                        character_id, created_at, updated_at, draft_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(draft_id) DO UPDATE SET
                        schema_version=excluded.schema_version,
                        lifecycle_state=excluded.lifecycle_state,
                        display_name=excluded.display_name,
                        character_id=excluded.character_id,
                        created_at=excluded.created_at,
                        updated_at=excluded.updated_at,
                        draft_json=excluded.draft_json
                    """,
                    self._to_row(record),
                )
            return record

        return self._guard(operation)

    def get(self, draft_id: str) -> CharacterCreatorDraftRecord | None:
        def operation() -> CharacterCreatorDraftRecord | None:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT draft_json FROM character_creator_drafts WHERE draft_id = ?",
                    (draft_id,),
                ).fetchone()
            if row is None:
                return None
            return CharacterCreatorDraftRecord.model_validate(json.loads(row["draft_json"]))

        return self._guard(operation)

    def delete(self, draft_id: str) -> bool:
        def operation() -> bool:
            with self._connect() as conn:
                cursor = conn.execute(
                    "DELETE FROM character_creator_drafts WHERE draft_id = ?",
                    (draft_id,),
                )
                return cursor.rowcount > 0

        return self._guard(operation)

    def list(self) -> list[CharacterCreatorDraftRecord]:
        def operation() -> list[CharacterCreatorDraftRecord]:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT draft_json FROM character_creator_drafts
                    ORDER BY updated_at DESC, display_name COLLATE NOCASE ASC
                    """
                ).fetchall()
            return [
                CharacterCreatorDraftRecord.model_validate(json.loads(row["draft_json"]))
                for row in rows
            ]

        return self._guard(operation)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _to_row(self, record: CharacterCreatorDraftRecord) -> tuple[Any, ...]:
        return (
            record.draft_id,
            record.schema_version,
            record.lifecycle_state,
            record.draft.display_name,
            record.draft.character_id,
            record.created_at,
            record.updated_at,
            record.model_dump_json(),
        )

    def _guard(self, operation: Callable[[], T]) -> T:
        try:
            return operation()
        except (sqlite3.DatabaseError, OSError, json.JSONDecodeError, ValidationError) as exc:
            raise CreatorDraftRepositoryError() from exc
