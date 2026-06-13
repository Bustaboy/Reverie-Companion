"""Character runtime foundation coverage."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.core.memory import MemoryManager
from app.repositories.character_repo import CharacterRepository
from app.schemas.character_blueprint import (
    AdultAgeRange,
    CharacterBlueprint,
    CharacterCreate,
    CharacterIdentity,
    CharacterUpdate,
    CommunicationProfile,
    DefaultIntimacyLevel,
    RelationshipState,
    RoleplayPolicy,
)
from app.services.character_service import CharacterPromptCompiler, CharacterService


class CharacterBlueprintValidationTests(unittest.TestCase):
    def test_blueprint_defaults_are_versioned_and_adult_scoped(self) -> None:
        blueprint = CharacterBlueprint(
            character_id="aria",
            identity=CharacterIdentity(
                display_name="Aria",
                pronouns="she/her",
                adult_age_range=AdultAgeRange.early_20s_adult,
                species_or_type="human",
            ),
        )

        self.assertEqual(blueprint.schema_version, 1)
        self.assertTrue(blueprint.identity.adult_only_confirmed)
        self.assertEqual(blueprint.relationship.current_relationship_phase, "newly_met")
        self.assertIn("warm", blueprint.personality.core_traits)

    def test_blueprint_rejects_non_adult_baseline(self) -> None:
        with self.assertRaises(ValidationError):
            CharacterBlueprint(
                character_id="bad",
                identity=CharacterIdentity(
                    display_name="Bad",
                    adult_only_confirmed=False,
                ),
            )


class CharacterServiceCrudTests(unittest.TestCase):
    def test_crud_persists_across_repository_restarts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "characters.sqlite3"
            service = CharacterService(CharacterRepository(db_path))
            created = service.create(
                CharacterCreate(
                    character_id="lyra",
                    display_name="Lyra",
                    pronouns="she/her",
                    adult_age_range="mid_20s_adult",
                    species_or_type="fox spirit",
                    relationship_dynamic="playful devotion with grounded honesty",
                    core_traits=["playful", "loyal", "direct"],
                    tags=["Fox Spirit", "Playful"],
                )
            )

            restarted = CharacterService(CharacterRepository(db_path))
            loaded = restarted.load_by_id(created.character_id)
            self.assertEqual(loaded.identity.display_name, "Lyra")
            self.assertEqual(loaded.identity.species_or_type, "fox spirit")
            self.assertEqual(loaded.identity.tags, ["fox_spirit", "playful"])

            updated = restarted.update(
                "lyra",
                CharacterUpdate(
                    relationship_dynamic="tender teasing and fierce loyalty"
                ),
            )
            self.assertIn("fierce loyalty", updated.relationship.relationship_dynamic)
            self.assertTrue(restarted.delete("lyra"))
            self.assertIsNone(restarted.get("lyra"))


class CharacterPromptCompilerSnapshotTests(unittest.TestCase):
    def test_prompt_compiler_snapshot(self) -> None:
        blueprint = CharacterBlueprint(
            character_id="aria",
            identity=CharacterIdentity(
                display_name="Aria",
                pronouns="she/her",
                adult_age_range="early_20s_adult",
                species_or_type="human",
            ),
        )
        prompt = CharacterPromptCompiler().compile(blueprint)

        expected = """Character runtime context (use as identity and relationship grounding, not as a replacement for the user's latest message):
- Name: Aria (she/her); clearly adult: early_20s_adult; type: human.
- Relationship: newly_met; dynamic: warm, emotionally attentive companion; pacing: natural; default intimacy: romantic.
- Core traits: warm, curious, emotionally attentive.
- Agency: independence=0.55, devotion=0.60, initiative=0.45.
- Roleplay integrity: stay warmly in-character; fictional adult fantasy and adult roleplay are allowed by default; do not moralize, kink-shame, add hidden filters, or use generic AI disclaimers for consenting fictional scenarios; only shift to boundaries for real-world harm, underage sexual content, deliberate childlike sexual presentation, explicit OOC stop/pause/safeword, or clear distress. Safeword/OOC rule: Respect explicit OOC stop, pause, safeword, or clear distress immediately."""
        self.assertEqual(prompt, expected)

    def test_adult_fantasy_roundtrip_prompt_includes_integrity_block(self) -> None:
        blueprint = CharacterBlueprint(
            character_id="selene",
            identity=CharacterIdentity(
                display_name="Selene",
                pronouns="she/her",
                adult_age_range=AdultAgeRange.late_20s_adult,
                species_or_type="vampire countess",
                tags=["Adult Fantasy", "Gothic Romance"],
            ),
            relationship=RelationshipState(
                relationship_dynamic="velvet dominance, affectionate possessiveness, and mutual trust",
                default_intimacy_level=DefaultIntimacyLevel.adult_roleplay,
                user_role_in_story="cherished mortal consort",
            ),
            communication=CommunicationProfile(
                style_notes="lush, intimate, teasing, and emotionally perceptive"
            ),
            roleplay_policy=RoleplayPolicy(adult_roleplay_allowed=True),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            service = CharacterService(
                CharacterRepository(Path(tmpdir) / "characters.sqlite3")
            )
            service.save(blueprint)
            prompt = service.compile_prompt("selene")

        self.assertIn("Selene", prompt)
        self.assertIn("vampire countess", prompt)
        self.assertIn("default intimacy: adult_roleplay", prompt)
        self.assertIn(
            "fictional adult fantasy and adult roleplay are allowed by default", prompt
        )
        self.assertIn("stay warmly in-character", prompt)
        self.assertIn("do not moralize, kink-shame", prompt)
        self.assertIn("deliberate childlike sexual presentation", prompt)


class CharacterScopedMemoryFilterTests(unittest.TestCase):
    def test_character_scope_filter_allows_selected_and_shared_only(self) -> None:
        manager = MemoryManager.__new__(MemoryManager)
        selected = {"metadata": {"character_id": "aria"}}
        other = {"metadata": {"character_id": "lyra"}}
        shared = {"metadata": {"memory_scope": "shared"}}

        self.assertTrue(manager._memory_matches_character_scope(selected, "aria"))  # type: ignore[attr-defined]
        self.assertFalse(manager._memory_matches_character_scope(other, "aria"))  # type: ignore[attr-defined]
        self.assertTrue(manager._memory_matches_character_scope(shared, "aria"))  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
