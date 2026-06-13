"""SQLite repository for versioned character blueprints."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from pydantic import ValidationError

from app.schemas.character_blueprint import CharacterBlueprint, CharacterSummary

T = TypeVar("T")


class CharacterRepositoryError(RuntimeError):
    """Raised when Reverie cannot safely read or write local companion data."""

    user_message = (
        "Your companion library needs a gentle moment before it can save or load that. "
        "Nothing about your bond was changed—please try again, and I’ll stay close. 💕"
    )

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.user_message)


class CharacterRepository:
    """Persist CharacterBlueprint aggregates without leaking SQLite to services."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        def operation() -> None:
            with self._connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS character_blueprints (
                        character_id TEXT PRIMARY KEY,
                        schema_version INTEGER NOT NULL,
                        display_name TEXT NOT NULL,
                        pronouns TEXT NOT NULL,
                        adult_age_range TEXT NOT NULL,
                        species_or_type TEXT NOT NULL,
                        relationship_phase TEXT NOT NULL,
                        relationship_dynamic TEXT NOT NULL,
                        relationship_pacing TEXT NOT NULL,
                        default_intimacy_level TEXT NOT NULL,
                        memory_scope TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        blueprint_json TEXT NOT NULL,
                        CHECK (length(character_id) > 0),
                        CHECK (length(display_name) > 0),
                        CHECK (json_valid(blueprint_json))
                    )
                    """)
                self._ensure_runtime_columns(conn)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_character_blueprints_character_id
                        ON character_blueprints(character_id)
                    """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_character_blueprints_display_name
                        ON character_blueprints(display_name COLLATE NOCASE)
                    """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_character_blueprints_relationship_phase
                        ON character_blueprints(relationship_phase)
                    """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_character_blueprints_updated_at
                        ON character_blueprints(updated_at)
                    """)

        self._guard(operation)

    def _ensure_runtime_columns(self, conn: sqlite3.Connection) -> None:
        existing = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(character_blueprints)")
        }
        migrations = {
            "relationship_phase": "TEXT NOT NULL DEFAULT 'newly_met'",
            "relationship_pacing": "TEXT NOT NULL DEFAULT 'natural'",
            "default_intimacy_level": "TEXT NOT NULL DEFAULT 'romantic'",
            "memory_scope": "TEXT NOT NULL DEFAULT 'character_private'",
            "created_at": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in migrations.items():
            if column not in existing:
                conn.execute(
                    f"ALTER TABLE character_blueprints ADD COLUMN {column} {definition}"
                )

    def upsert(self, blueprint: CharacterBlueprint) -> CharacterBlueprint:
        def operation() -> CharacterBlueprint:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO character_blueprints (
                        character_id, schema_version, display_name, pronouns,
                        adult_age_range, species_or_type, relationship_phase,
                        relationship_dynamic, relationship_pacing, default_intimacy_level,
                        memory_scope, created_at, updated_at, blueprint_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(character_id) DO UPDATE SET
                        schema_version=excluded.schema_version,
                        display_name=excluded.display_name,
                        pronouns=excluded.pronouns,
                        adult_age_range=excluded.adult_age_range,
                        species_or_type=excluded.species_or_type,
                        relationship_phase=excluded.relationship_phase,
                        relationship_dynamic=excluded.relationship_dynamic,
                        relationship_pacing=excluded.relationship_pacing,
                        default_intimacy_level=excluded.default_intimacy_level,
                        memory_scope=excluded.memory_scope,
                        created_at=excluded.created_at,
                        updated_at=excluded.updated_at,
                        blueprint_json=excluded.blueprint_json
                    """,
                    self._to_row(blueprint),
                )
            return blueprint

        return self._guard(operation)

    def get(self, character_id: str) -> CharacterBlueprint | None:
        def operation() -> CharacterBlueprint | None:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT blueprint_json FROM character_blueprints WHERE character_id = ?",
                    (character_id,),
                ).fetchone()
            if row is None:
                return None
            return CharacterBlueprint.model_validate(json.loads(row["blueprint_json"]))

        return self._guard(operation)

    def list(self) -> list[CharacterSummary]:
        def operation() -> list[CharacterSummary]:
            with self._connect() as conn:
                rows = conn.execute("""
                    SELECT blueprint_json
                    FROM character_blueprints
                    ORDER BY display_name COLLATE NOCASE ASC, character_id ASC
                    """).fetchall()
            summaries: list[CharacterSummary] = []
            for row in rows:
                blueprint = CharacterBlueprint.model_validate(
                    json.loads(row["blueprint_json"])
                )
                summaries.append(
                    CharacterSummary(
                        character_id=blueprint.character_id,
                        display_name=blueprint.identity.display_name,
                        pronouns=blueprint.identity.pronouns,
                        adult_age_range=blueprint.identity.adult_age_range,
                        species_or_type=blueprint.identity.species_or_type,
                        relationship_dynamic=blueprint.relationship.relationship_dynamic,
                        core_traits=blueprint.personality.core_traits,
                        updated_at=blueprint.updated_at,
                    )
                )
            return summaries

        return self._guard(operation)

    def delete(self, character_id: str) -> bool:
        def operation() -> bool:
            with self._connect() as conn:
                cursor = conn.execute(
                    "DELETE FROM character_blueprints WHERE character_id = ?",
                    (character_id,),
                )
                return cursor.rowcount > 0

        return self._guard(operation)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _to_row(self, blueprint: CharacterBlueprint) -> tuple[Any, ...]:
        relationship = blueprint.relationship
        return (
            blueprint.character_id,
            blueprint.schema_version,
            blueprint.identity.display_name,
            blueprint.identity.pronouns,
            blueprint.identity.adult_age_range.value,
            blueprint.identity.species_or_type,
            (
                relationship.current_relationship_phase
                or relationship.starting_relationship_phase
            ).value,
            relationship.relationship_dynamic,
            relationship.relationship_pacing.value,
            relationship.default_intimacy_level.value,
            blueprint.memory_policy.scope.value,
            blueprint.created_at,
            blueprint.updated_at,
            blueprint.model_dump_json(),
        )

    def _guard(self, operation: Callable[[], T]) -> T:
        try:
            return operation()
        except (
            sqlite3.DatabaseError,
            OSError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise CharacterRepositoryError() from exc
