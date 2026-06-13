-- M4-01 Character Runtime Foundation migration stub.
-- This mirrors CharacterRepository.ensure_schema() for the local-first SQLite store.
-- Future blueprint migrations should:
-- 1. add a new schema_migrations row,
-- 2. read characters.blueprint_json by schema_version,
-- 3. transform JSON into the next CharacterBlueprint schema,
-- 4. keep character_id stable so chat, memory, journal, growth, and gallery links remain scoped.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS characters (
    character_id TEXT PRIMARY KEY,
    blueprint_json TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_characters_active_name
ON characters(deleted_at, display_name);
