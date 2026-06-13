"""SQLite repository for versioned character blueprints."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.schemas.character_blueprint import CharacterBlueprint, CharacterSummary


class CharacterRepositoryError(RuntimeError):
    """Raised when the local character library cannot be read or written safely."""


class CharacterRepository:
    """Persist CharacterBlueprint aggregates without leaking SQLite to services."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        try:
            with self._connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS character_blueprints (
                        character_id TEXT PRIMARY KEY,
                        schema_version INTEGER NOT NULL,
                        display_name TEXT NOT NULL,
                        pronouns TEXT NOT NULL,
                        adult_age_range TEXT NOT NULL,
                        species_or_type TEXT NOT NULL,
                        starting_relationship_phase TEXT NOT NULL,
                        current_relationship_phase TEXT NOT NULL,
                        relationship_dynamic TEXT NOT NULL,
                        relationship_pacing TEXT NOT NULL,
                        default_intimacy_level TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        blueprint_json TEXT NOT NULL
                    )
                    """)
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_character_blueprints_character_id ON character_blueprints(character_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_character_blueprints_display_name ON character_blueprints(display_name)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_character_blueprints_relationship ON character_blueprints(current_relationship_phase, default_intimacy_level)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_character_blueprints_updated_at ON character_blueprints(updated_at)"
                )
        except sqlite3.Error as exc:
            raise CharacterRepositoryError(
                "Reverie's local companion library could not be prepared right now. Your companions are still safe; please try again in a moment."
            ) from exc

    def upsert(self, blueprint: CharacterBlueprint) -> CharacterBlueprint:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                INSERT INTO character_blueprints (
                    character_id, schema_version, display_name, pronouns,
                    adult_age_range, species_or_type, starting_relationship_phase,
                    current_relationship_phase, relationship_dynamic, relationship_pacing,
                    default_intimacy_level, created_at, updated_at, blueprint_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(character_id) DO UPDATE SET
                    schema_version=excluded.schema_version,
                    display_name=excluded.display_name,
                    pronouns=excluded.pronouns,
                    adult_age_range=excluded.adult_age_range,
                    species_or_type=excluded.species_or_type,
                    starting_relationship_phase=excluded.starting_relationship_phase,
                    current_relationship_phase=excluded.current_relationship_phase,
                    relationship_dynamic=excluded.relationship_dynamic,
                    relationship_pacing=excluded.relationship_pacing,
                    default_intimacy_level=excluded.default_intimacy_level,
                    updated_at=excluded.updated_at,
                    blueprint_json=excluded.blueprint_json
                """,
                    self._to_row(blueprint),
                )
        except sqlite3.Error as exc:
            raise CharacterRepositoryError(
                "Reverie couldn't save this companion just now. Nothing about them was lost—please try again in a moment."
            ) from exc
        return blueprint

    def get(self, character_id: str) -> CharacterBlueprint | None:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT blueprint_json FROM character_blueprints WHERE character_id = ?",
                    (character_id,),
                ).fetchone()
            if row is None:
                return None
            return CharacterBlueprint.model_validate(json.loads(row["blueprint_json"]))
        except (sqlite3.Error, json.JSONDecodeError, ValidationError) as exc:
            raise CharacterRepositoryError(
                "Reverie couldn't open this companion's card cleanly. Please try again; if it keeps happening, your local library may need a gentle repair."
            ) from exc

    def list(self) -> list[CharacterSummary]:
        try:
            with self._connect() as conn:
                rows = conn.execute("""
                SELECT character_id, display_name, pronouns, adult_age_range,
                       species_or_type, relationship_dynamic, updated_at, blueprint_json
                FROM character_blueprints
                ORDER BY display_name COLLATE NOCASE ASC, character_id ASC
                """).fetchall()
        except sqlite3.Error as exc:
            raise CharacterRepositoryError(
                "Reverie's companion library couldn't be opened right now. Please try again in a moment."
            ) from exc
        summaries: list[CharacterSummary] = []
        for row in rows:
            try:
                blueprint = CharacterBlueprint.model_validate(
                    json.loads(row["blueprint_json"])
                )
            except (json.JSONDecodeError, ValidationError) as exc:
                raise CharacterRepositoryError(
                    "One companion card needs a gentle repair before Reverie can show the full library."
                ) from exc
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

    def delete(self, character_id: str) -> bool:
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "DELETE FROM character_blueprints WHERE character_id = ?",
                    (character_id,),
                )
                return cursor.rowcount > 0
        except sqlite3.Error as exc:
            raise CharacterRepositoryError(
                "Reverie couldn't update the companion library just now. Please try again in a moment."
            ) from exc

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _to_row(self, blueprint: CharacterBlueprint) -> tuple[Any, ...]:
        return (
            blueprint.character_id,
            blueprint.schema_version,
            blueprint.identity.display_name,
            blueprint.identity.pronouns,
            blueprint.identity.adult_age_range.value,
            blueprint.identity.species_or_type,
            blueprint.relationship.starting_relationship_phase.value,
            (
                blueprint.relationship.current_relationship_phase.value
                if blueprint.relationship.current_relationship_phase
                else blueprint.relationship.starting_relationship_phase.value
            ),
            blueprint.relationship.relationship_dynamic,
            blueprint.relationship.relationship_pacing.value,
            blueprint.relationship.default_intimacy_level.value,
            blueprint.created_at,
            blueprint.updated_at,
            blueprint.model_dump_json(),
        )
