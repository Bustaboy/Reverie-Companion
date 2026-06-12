from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.extensions import CharacterImportService, ExtensionEventBus, ExtensionRegistry
from app.models.extensions import CharacterImportRequest, ExtensionCommandRequest, ExtensionEventScope


class ExtensionFoundationTests(unittest.TestCase):
    def test_registry_loads_core_and_isolates_bad_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "bad.json").write_text('{"schema_version":"extension.v1"', encoding="utf-8")
            settings = Settings(extension_manifest_dirs=[tmp])
            registry = ExtensionRegistry(settings)

            snapshot = registry.load()

            self.assertTrue(any(item.manifest.extension_id == "reverie.core" for item in snapshot.extensions))
            self.assertEqual(snapshot.errors[0].code, "extension_manifest_invalid")

    def test_command_bus_rejects_undeclared_commands(self) -> None:
        registry = ExtensionRegistry(Settings(extension_manifest_dirs=[]))
        bus = ExtensionEventBus(registry)

        result = bus.dispatch(
            ExtensionCommandRequest(
                command_id="missing.command",
                source_extension_id="reverie.core",
                scope=ExtensionEventScope.CORE,
                payload={"oversized": "x" * 3000},
            )
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.error.code, "extension_command_not_declared")

    def test_character_import_extracts_lore_assets_voice_and_style(self) -> None:
        service = CharacterImportService()
        profile = service.preview(
            CharacterImportRequest(
                payload={
                    "data": {
                        "name": "Tara",
                        "description": "Warm companion",
                        "personality": "Playful, protective",
                        "character_book": {
                            "entries": [
                                {
                                    "comment": "Moon Court",
                                    "keys": ["Moon Court", "silver oath"],
                                    "content": "The Moon Court enforces oaths through ritual. It never mind-controls citizens.",
                                    "priority": 82,
                                }
                            ]
                        },
                        "extensions": {
                            "sprites": [{"name": "smile", "path": "sprites/smile.png"}],
                            "voice_profile": {"tone": "warm alto"},
                            "mood_preferences": {"default": "soft"},
                            "growth": {"pacing": "slow_burn"},
                            "image_generation": {"style": "warm anime portrait"},
                        },
                    }
                }
            )
        )

        self.assertEqual(profile.name, "Tara")
        self.assertEqual(profile.lorebook_entries[0].title, "Moon Court")
        self.assertEqual(profile.visual_assets[0].kind, "sprite")
        self.assertEqual(profile.voice_hints["voice_profile"]["tone"], "warm alto")
        self.assertEqual(profile.mood_preferences["default"], "soft")
        self.assertEqual(profile.growth_preferences["pacing"], "slow_burn")
        self.assertEqual(profile.image_style_references["style"], "warm anime portrait")


class ExtensionApiTests(unittest.TestCase):
    def test_extensions_route_lists_core_contract(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/extensions")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(any(item["manifest"]["extension_id"] == "reverie.core" for item in body["extensions"]))


if __name__ == "__main__":
    unittest.main()
