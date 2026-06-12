# Reverie Extension Foundations

Reverie extensions are intentionally lightweight in Milestone 3 Task 5C. They are **declarative manifests plus typed events/commands**, not arbitrary imported Python or browser code. This keeps the local-first app safe, predictable, and friendly to 8GB machines while leaving a clean seam for richer plugin runtimes later.

## Contract version

Current schema: `extension.v1`.

Manifests live as JSON files in `./extensions` by default and may declare:

- custom panels (`custom_panel` capability), rendered only by trusted frontend component keys;
- commands (`commands` capability), validated before they enter the event bus;
- settings sections (`settings` capability), rendered from declarative fields;
- TTS voice contracts (`tts_voice` capability);
- image workflow contracts (`image_workflow` capability);
- growth modifiers (`growth_modifier` capability), which should require user review by default;
- character import helpers (`character_import` capability);
- scoped access requests for VN, memory, TTS, image, growth, and settings systems.

## Minimal manifest example

```json
{
  "schema_version": "extension.v1",
  "extension_id": "example.soft-vn-panel",
  "name": "Soft VN Panel Example",
  "version": "0.1.0",
  "description": "Example declarative extension manifest.",
  "enabled_by_default": false,
  "capabilities": ["custom_panel", "settings", "commands", "vn_state"],
  "commands": [
    {
      "command_id": "vn.soft_focus",
      "title": "Soft focus VN scene",
      "description": "Ask the VN system to prefer soft lighting metadata.",
      "scope": "vn",
      "required_capabilities": ["vn_state"],
      "payload_schema": {"mood": "string"}
    }
  ],
  "settings_sections": [
    {
      "section_id": "soft-vn",
      "title": "Soft VN controls",
      "description": "Small local settings rendered by the Settings page.",
      "fields": [
        {
          "key": "prefer_soft_lighting",
          "label": "Prefer soft lighting",
          "description": "Bias VN scene metadata toward gentle lighting.",
          "kind": "boolean",
          "default": true
        }
      ]
    }
  ]
}
```

## Error isolation

- Invalid manifests are skipped and reported in `/api/extensions`.
- Commands are rejected unless the source extension is enabled, declares `commands`, and declares the specific command.
- Event payloads are bounded before storage.
- The frontend event bus catches listener failures and logs them without crashing the UI.

## Character import preview

`POST /api/extensions/character-import/preview` accepts SillyTavern/character-card JSON and returns a normalized preview containing character text, lorebook/world-info entries, visual assets, voice hints, mood/growth preferences, image-generation style references, preserved unknown fields, and review warnings. The preview does not write durable character state; future import flows can show it for user approval first.
