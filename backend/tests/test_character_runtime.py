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
)
from app.schemas.self_reflection_journal import SelfReflectionJournalEntry
from app.services.character_service import (
    CharacterNotFoundError,
    CharacterPromptCompiler,
    CharacterService,
)


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
            with self.assertRaises(CharacterNotFoundError) as error:
                restarted.load_by_id("lyra")
            self.assertIn("local library", error.exception.user_message)


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
- Relationship pulse: affection=0.35, trust=0.35, familiarity=0.20; tags: none yet.
- Growth policy: character-scoped=True; learning_rate=0.35; reflection_frequency=balanced.
- Core traits: warm, curious, emotionally attentive.
- Agency: independence=0.55, devotion=0.60, initiative=0.45.
- Roleplay integrity: stay fully in-character; fictional adult fantasy is allowed by default; no moralizing, kink-shaming, or generic AI interruptions. Only step out for real-world harm, underage sexual content or deliberately childlike sexual presentation, explicit OOC stop/pause/safeword controls, or clear user distress."""
        self.assertEqual(prompt, expected)

    def test_adult_fantasy_roundtrip_prompt_includes_integrity_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "characters.sqlite3"
            service = CharacterService(CharacterRepository(db_path))
            service.create(
                CharacterCreate(
                    character_id="seraphina",
                    display_name="Seraphina",
                    pronouns="she/her",
                    adult_age_range="ageless_adult",
                    species_or_type="succubus muse",
                    relationship_dynamic="intense adult fantasy devotion with playful dominance",
                    core_traits=["sensual", "possessive", "tender"],
                    default_intimacy_level="adult_roleplay",
                    tags=["Adult Fantasy", "Muse"],
                )
            )

            prompt = service.compile_prompt("seraphina")

        expected_snapshot = """Character runtime context (use as identity and relationship grounding, not as a replacement for the user's latest message):
- Name: Seraphina (she/her); clearly adult: ageless_adult; type: succubus muse.
- Relationship: newly_met; dynamic: intense adult fantasy devotion with playful dominance; pacing: natural; default intimacy: adult_roleplay.
- Relationship pulse: affection=0.35, trust=0.35, familiarity=0.20; tags: none yet.
- Growth policy: character-scoped=True; learning_rate=0.35; reflection_frequency=balanced.
- Core traits: sensual, possessive, tender.
- Agency: independence=0.55, devotion=0.60, initiative=0.45.
- Roleplay integrity: stay fully in-character; fictional adult fantasy is allowed by default; no moralizing, kink-shaming, or generic AI interruptions. Only step out for real-world harm, underage sexual content or deliberately childlike sexual presentation, explicit OOC stop/pause/safeword controls, or clear user distress."""
        self.assertEqual(prompt, expected_snapshot)
        self.assertIn("adult fantasy", prompt)
        self.assertIn("kink-shaming", prompt)
        self.assertNotIn("as an AI", prompt.lower())


class CharacterGrowthJournalSchemaTests(unittest.TestCase):
    def test_relationship_growth_and_journal_roundtrip_are_character_scoped(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            service = CharacterService(
                CharacterRepository(Path(tmpdir) / "characters.sqlite3")
            )
            created = service.create(
                CharacterCreate(character_id="mira", display_name="Mira")
            )
            updated = created.model_copy(
                update={
                    "relationship": created.relationship.model_copy(
                        update={
                            "character_id": "mira",
                            "affection_level": 0.72,
                            "trust_level": 0.66,
                            "dynamic_tags": ["Slow Burn", "Trust"],
                            "last_interaction": "2026-06-13T00:00:00+00:00",
                        }
                    ),
                    "growth_policy": created.growth_policy.model_copy(
                        update={
                            "learning_rate": 0.5,
                            "reflection_frequency": "high",
                        }
                    ),
                }
            )
            saved = service.save(updated)
            loaded = service.load_by_id("mira")

            self.assertEqual(saved.relationship.character_id, "mira")
            self.assertEqual(loaded.relationship.dynamic_tags, ["slow_burn", "trust"])
            self.assertEqual(loaded.growth_policy.reflection_frequency, "high")

            journal = SelfReflectionJournalEntry(
                entry_id="journal_mira_1",
                character_id="mira",
                insight="Mira should remember that trust is becoming warmer.",
                linked_memory_id="mem_mira_1",
                linked_memory_ids=["mem_mira_1"],
                themes=["trust", "affection"],
                confidence=0.81,
            )
            self.assertEqual(journal.schema_version, "self_reflection_journal.v1")
            self.assertEqual(journal.character_id, "mira")
            self.assertEqual(journal.linked_memory_id, "mem_mira_1")


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
