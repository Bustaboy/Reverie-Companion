"""SQLite repository for creator draft persistence."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeVar

from pydantic import ValidationError

from app.services.character_creator_service import CharacterCreatorDraft

T = TypeVar("T")


class CharacterCreatorDraftRepositoryError(RuntimeError):
    """Raised when creator draft persistence cannot be read or written safely."""

    user_message = (
        "Your character draft library needs a moment before it can save or load that. "
        "The finalized character library was not changed."
    )

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.user_message)


class CharacterCreatorDraftRepository:
    """Persist creator drafts separately from finalized CharacterBlueprint rows."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        def operation() -> None:
            with self._connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS character_creator_drafts (
                        draft_id TEXT PRIMARY KEY,
                        schema_version INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        display_name TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        draft_json TEXT NOT NULL,
                        CHECK (length(draft_id) > 0),
                        CHECK (length(display_name) > 0),
                        CHECK (json_valid(draft_json))
                    )
                    """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_character_creator_drafts_status
                        ON character_creator_drafts(status)
                    """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_character_creator_drafts_updated_at
                        ON character_creator_drafts(updated_at)
                    """)

        self._guard(operation)

    def upsert(self, draft: CharacterCreatorDraft) -> CharacterCreatorDraft:
        def operation() -> CharacterCreatorDraft:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO character_creator_drafts (
                        draft_id, schema_version, status, display_name,
                        created_at, updated_at, draft_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(draft_id) DO UPDATE SET
                        schema_version=excluded.schema_version,
                        status=excluded.status,
                        display_name=excluded.display_name,
                        updated_at=excluded.updated_at,
                        draft_json=excluded.draft_json
                    """,
                    (
                        draft.draft_id,
                        draft.schema_version,
                        draft.status,
                        draft.display_name,
                        draft.created_at,
                        draft.updated_at,
                        draft.model_dump_json(),
                    ),
                )
            return draft

        return self._guard(operation)

    def get(self, draft_id: str) -> CharacterCreatorDraft | None:
        def operation() -> CharacterCreatorDraft | None:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT draft_json FROM character_creator_drafts
                    WHERE draft_id = ? AND status != 'deleted'
                    """,
                    (draft_id,),
                ).fetchone()
            if row is None:
                return None
            return CharacterCreatorDraft.model_validate(json.loads(row["draft_json"]))

        return self._guard(operation)

    def list(self) -> list[CharacterCreatorDraft]:
        def operation() -> list[CharacterCreatorDraft]:
            with self._connect() as conn:
                rows = conn.execute("""
                    SELECT draft_json FROM character_creator_drafts
                    WHERE status != 'deleted'
                    ORDER BY updated_at DESC, draft_id ASC
                    """).fetchall()
            return [
                CharacterCreatorDraft.model_validate(json.loads(row["draft_json"]))
                for row in rows
            ]

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

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _guard(self, operation: Callable[[], T]) -> T:
        try:
            return operation()
        except (
            sqlite3.DatabaseError,
            OSError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise CharacterCreatorDraftRepositoryError() from exc
