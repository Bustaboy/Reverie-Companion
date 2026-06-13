-- M4-01 migration stub: character runtime foundation.
-- Apply with the future Alembic runner or manually against REVERIE_CHARACTER_DB_PATH.
CREATE TABLE IF NOT EXISTS character_blueprints (
    character_id TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    display_name TEXT NOT NULL,
    pronouns TEXT NOT NULL,
    adult_age_range TEXT NOT NULL,
    species_or_type TEXT NOT NULL,
    relationship_dynamic TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    blueprint_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_character_blueprints_display_name ON character_blueprints(display_name);
CREATE INDEX IF NOT EXISTS idx_character_blueprints_updated_at ON character_blueprints(updated_at);
