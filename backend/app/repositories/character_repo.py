"""SQLite repository for durable character blueprints."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

from app.schemas.character_blueprint import CharacterBlueprint, CharacterRecord, utc_now


class CharacterRepositoryError(Exception):
    """Base exception for character repository failures."""


class CharacterNotFoundError(CharacterRepositoryError):
    """Raised when a character cannot be found."""


class CharacterRepository:
    """Small SQLite persistence boundary for CharacterBlueprint records."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path).expanduser().resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ensure_schema()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def ensure_schema(self) -> None:
        """Create the v1 character table and a lightweight migration ledger."""

        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL,
                    notes TEXT NOT NULL
                )
                """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    character_id TEXT PRIMARY KEY,
                    blueprint_json TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    display_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    deleted_at TEXT
                )
                """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_characters_active_name
                ON characters(deleted_at, display_name)
                """)
            conn.execute(
                """
                INSERT OR IGNORE INTO schema_migrations(version, applied_at, notes)
                VALUES (?, ?, ?)
                """,
                (
                    "20260613_0001_character_blueprints",
                    utc_now().isoformat(),
                    "M4-01: create durable CharacterBlueprint v1 table; future migrations should transform blueprint_json by schema_version before prompt/runtime use.",
                ),
            )

    def create(
        self, character_id: str, blueprint: CharacterBlueprint
    ) -> CharacterRecord:
        now = utc_now()
        payload = self._dump_blueprint(blueprint)
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO characters(
                        character_id, blueprint_json, schema_version, display_name,
                        created_at, updated_at, deleted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        character_id,
                        payload,
                        blueprint.schema_version,
                        blueprint.identity.display_name,
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise CharacterRepositoryError(
                "A companion with that identity already lives here. Choose another id or update the existing character."
            ) from exc
        return CharacterRecord(
            character_id=character_id,
            blueprint=blueprint,
            created_at=now,
            updated_at=now,
        )

    def get(
        self, character_id: str, *, include_deleted: bool = False
    ) -> CharacterRecord:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM characters WHERE character_id = ?", (character_id,)
            ).fetchone()
        if row is None or (row["deleted_at"] and not include_deleted):
            raise CharacterNotFoundError(character_id)
        return self._row_to_record(row)

    def list(self, *, include_deleted: bool = False) -> list[CharacterRecord]:
        sql = "SELECT * FROM characters"
        if not include_deleted:
            sql += " WHERE deleted_at IS NULL"
        sql += " ORDER BY display_name COLLATE NOCASE ASC"
        with self._connect() as conn:
            rows: Iterable[sqlite3.Row] = conn.execute(sql).fetchall()
        return [self._row_to_record(row) for row in rows]

    def update(
        self, character_id: str, blueprint: CharacterBlueprint
    ) -> CharacterRecord:
        existing = self.get(character_id)
        now = utc_now()
        with self._connect() as conn:
            result = conn.execute(
                """
                UPDATE characters
                SET blueprint_json = ?, schema_version = ?, display_name = ?, updated_at = ?
                WHERE character_id = ? AND deleted_at IS NULL
                """,
                (
                    self._dump_blueprint(blueprint),
                    blueprint.schema_version,
                    blueprint.identity.display_name,
                    now.isoformat(),
                    character_id,
                ),
            )
        if result.rowcount == 0:
            raise CharacterNotFoundError(character_id)
        return CharacterRecord(
            character_id=character_id,
            blueprint=blueprint,
            created_at=existing.created_at,
            updated_at=now,
        )

    def delete(self, character_id: str) -> bool:
        now = utc_now()
        with self._connect() as conn:
            result = conn.execute(
                "UPDATE characters SET deleted_at = ?, updated_at = ? WHERE character_id = ? AND deleted_at IS NULL",
                (now.isoformat(), now.isoformat(), character_id),
            )
        return result.rowcount > 0

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _dump_blueprint(self, blueprint: CharacterBlueprint) -> str:
        return blueprint.model_dump_json()

    def _row_to_record(self, row: sqlite3.Row) -> CharacterRecord:
        blueprint = CharacterBlueprint.model_validate(json.loads(row["blueprint_json"]))
        return CharacterRecord(
            character_id=str(row["character_id"]),
            blueprint=blueprint,
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            deleted_at=(
                datetime.fromisoformat(str(row["deleted_at"]))
                if row["deleted_at"]
                else None
            ),
        )
