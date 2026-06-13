-- M4-01 migration stub: character runtime foundation.
-- Alembic-style metadata for the future runner:
-- revision: 0001_character_blueprints
-- down_revision: null
-- created: 2026-06-13
--
-- Apply with the future Alembic runner or manually against REVERIE_CHARACTER_DB_PATH.
-- The table keeps queryable relationship fields beside the versioned JSON blueprint so
-- list views, memory filters, and future growth jobs can stay character-scoped without
-- hydrating every companion payload.

BEGIN;

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
);

-- Explicit character id index mirrors the query path even though character_id is the
-- primary key; keeping it named makes migration intent clear for future Alembic diffs.
CREATE INDEX IF NOT EXISTS idx_character_blueprints_character_id
    ON character_blueprints(character_id);
CREATE INDEX IF NOT EXISTS idx_character_blueprints_display_name
    ON character_blueprints(display_name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_character_blueprints_relationship_phase
    ON character_blueprints(relationship_phase);
CREATE INDEX IF NOT EXISTS idx_character_blueprints_updated_at
    ON character_blueprints(updated_at);

-- Character-scoped runtime lookups are hot paths on 8GB-class systems; keep
-- relationship, reflection, and growth reads index-friendly as those tables land.
CREATE INDEX IF NOT EXISTS idx_relationship_state_character_id
    ON relationship_state(character_id);
CREATE INDEX IF NOT EXISTS idx_self_reflection_journal_character_id
    ON self_reflection_journal(character_id);
CREATE INDEX IF NOT EXISTS idx_growth_policy_character_id
    ON growth_policy(character_id);

COMMIT;
