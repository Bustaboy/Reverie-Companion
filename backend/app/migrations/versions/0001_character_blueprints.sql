-- M4-01 migration stub: character runtime foundation.
-- Alembic-ready shape for the future migration runner; safe to apply manually
-- against REVERIE_CHARACTER_DB_PATH while the lightweight SQLite bootstrap remains.

-- revision: 0001_character_blueprints
-- down_revision: null
-- creates: durable, versioned, character-scoped blueprint storage

CREATE TABLE IF NOT EXISTS character_blueprints (
    character_id TEXT NOT NULL PRIMARY KEY,
    schema_version INTEGER NOT NULL DEFAULT 1,
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
    blueprint_json TEXT NOT NULL,
    CHECK (schema_version >= 1),
    CHECK (length(character_id) > 0),
    CHECK (length(display_name) > 0),
    CHECK (length(relationship_dynamic) > 0)
);

CREATE INDEX IF NOT EXISTS idx_character_blueprints_character_id
    ON character_blueprints(character_id);

CREATE INDEX IF NOT EXISTS idx_character_blueprints_display_name
    ON character_blueprints(display_name COLLATE NOCASE);

CREATE INDEX IF NOT EXISTS idx_character_blueprints_relationship
    ON character_blueprints(current_relationship_phase, default_intimacy_level);

CREATE INDEX IF NOT EXISTS idx_character_blueprints_updated_at
    ON character_blueprints(updated_at);
