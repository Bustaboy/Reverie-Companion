# Reverie Extension Developer Guide

Reverie extensions are **metadata-first** and local-first. The current foundation loads typed manifests, settings schemas, command definitions, and import enrichments. It does **not** execute arbitrary extension code in the backend or frontend hot path.

## API version

Current extension API: `2026.06.v1`.

Extensions should declare the API version they target. Future breaking changes should add a new API version rather than mutating existing contracts.

## Safe capabilities

Extensions can declare these capabilities:

- `custom_panel` — future lightweight UI panels rendered through registered slots.
- `command` — typed command definitions sent through the command bus.
- `tts_voice` — voice/profile hints, not direct model loading.
- `image_workflow` — image prompt/workflow hints, always queued by core services.
- `growth_modifier` — suggested growth modifiers requiring core validation.
- `settings_section` — schema-rendered settings sections.
- `character_importer` — import normalization/enrichment metadata.
- `event_subscriber` — future subscriptions to typed event envelopes.

## Error isolation

A malformed extension must not crash Reverie:

- backend routes validate manifests and command envelopes with Pydantic;
- frontend settings are rendered from data schemas inside `svelte:boundary`;
- command dispatch returns typed `{ accepted, error }` responses;
- imported character data is normalized into bounded preview models before any durable write.

## Settings sections

Settings are data-only schemas. A section contains small fields (`text`, `textarea`, `boolean`, `number`, `select`) and is persisted locally by the frontend under `reverie.extensionSettings.v1`.

## Command bus

Commands use the envelope:

```json
{
  "command_id": "preview",
  "source": "my.extension",
  "target": "image",
  "payload": { "prompt": "warm candlelight" }
}
```

Core systems remain responsible for actioning commands. Extensions should treat dispatch as a request, not a guarantee that a heavy job will run.

## Character card import enrichment

The import preview endpoint accepts SillyTavern / Character Card v2 JSON and extracts:

- base card fields;
- lorebooks / world info;
- sprite, avatar, expression, and reference asset hints;
- voice profile hints;
- mood and growth preferences;
- image generation style references.

No import preview writes memory, growth state, voice profiles, or media files by itself.
