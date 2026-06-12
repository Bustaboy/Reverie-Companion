"""Tests for extension registry and enhanced character import contracts."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.services.extension_registry import CharacterImportService, ExtensionRegistry


class ExtensionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_registry_exposes_builtin_manifest(self) -> None:
        response = self.client.get("/extensions")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["api_version"], "2026.06.v1")
        self.assertTrue(any(item["manifest"]["id"] == "reverie.core.extensibility" for item in body["extensions"]))

    def test_command_dispatch_is_typed_and_records_event(self) -> None:
        response = self.client.post(
            "/extensions/commands",
            json={"command_id": "preview", "target": "image", "payload": {"prompt": "soft candlelight"}},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual(body["event"]["target"], "image")
        self.assertEqual(body["event"]["payload"]["command_id"], "preview")

    def test_character_import_preview_extracts_lore_assets_voice_growth_and_styles(self) -> None:
        card = {
            "spec": "chara_card_v2",
            "data": {
                "name": "Mira",
                "description": "Warm stargazer.",
                "personality": "Curious, devoted.",
                "scenario": "A quiet observatory.",
                "first_mes": "Come look at this constellation with me.",
                "tags": ["romance", "stars"],
                "character_book": {
                    "entries": [
                        {
                            "id": 7,
                            "keys": ["observatory", "telescope"],
                            "content": "Mira inherited an old brass telescope.",
                            "comment": "Core lore",
                            "constant": True,
                        }
                    ]
                },
                "extensions": {
                    "voice": {"voice_id": "mira_soft", "description": "Soft, close, breathy warmth", "tags": ["soft"]},
                    "sprites": [{"id": "smile", "kind": "sprite", "path": "sprites/smile.png", "expression": "happy"}],
                    "growth": {"baseline_mood": "hopeful", "boundaries": ["go slow"], "growth_notes": ["trust builds through consistency"]},
                    "image_style": {"id": "stars", "prompt": "soft anime portrait, observatory, stars", "negative_prompt": "blurry"},
                },
            },
        }
        response = self.client.post("/extensions/character-import/preview", json={"source_format": "auto", "card": card})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["source_format"], "character_card_v2")
        self.assertEqual(body["name"], "Mira")
        self.assertEqual(body["lorebook_entries"][0]["keys"], ["observatory", "telescope"])
        self.assertEqual(body["visual_assets"][0]["kind"], "sprite")
        self.assertEqual(body["voice_hints"][0]["voice_id"], "mira_soft")
        self.assertEqual(body["mood_growth_preferences"]["baseline_mood"], "hopeful")
        self.assertEqual(body["image_style_references"][0]["id"], "stars")


class CharacterImportServiceTests(unittest.TestCase):
    def test_importer_adds_warning_when_lorebook_missing(self) -> None:
        preview = CharacterImportService().preview(
            request=type("Request", (), {"source_format": "auto", "card": {"data": {"name": "No Lore"}}, "embedded_assets": [], "file_name": None})()
        )
        self.assertIn("No lorebook/world-info entries were found in the card.", preview.warnings)


class ExtensionRegistryTests(unittest.TestCase):
    def test_bad_command_payload_does_not_crash_registry(self) -> None:
        registry = ExtensionRegistry()
        events_before = len(registry.recent_events())
        self.assertGreaterEqual(events_before, 0)


if __name__ == "__main__":
    unittest.main()
