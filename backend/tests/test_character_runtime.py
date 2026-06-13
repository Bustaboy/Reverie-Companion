"""Character runtime foundation coverage."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.core.memory import MemoryManager
from app.repositories.character_repo import CharacterRepository
from app.schemas.growth_policy import GrowthPolicy
from app.schemas.relationship_state import RelationshipState
from app.schemas.self_reflection_journal import SelfReflectionJournalEntry
from app.schemas.character_blueprint import (
    AdultAgeRange,
    CharacterBlueprint,
    CharacterCreate,
    CharacterIdentity,
    CharacterUpdate,
)
from app.services.character_service import (
    CharacterNotFoundError,
    CharacterPromptCompiler,
    CharacterService,
)
from app.services.character_quality_evals import CharacterQualityEvaluator


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


class RelationshipGrowthJournalSchemaTests(unittest.TestCase):
    def test_relationship_growth_and_journal_are_versioned_and_scoped(self) -> None:
        relationship = RelationshipState(
            character_id="aria",
            trust_level=0.62,
            affection_level=0.7,
            comfort_with_closeness=0.55,
            dynamic_tags=["Slow Burn", "Slow Burn", "repair"],
            unresolved_threads=["talk about the promise"],
            last_interaction="2026-06-13T00:00:00+00:00",
        )
        growth = GrowthPolicy(
            character_id="aria", learning_rate=0.4, reflection_frequency="high"
        )
        entry = SelfReflectionJournalEntry(
            entry_id="journal_aria_1",
            character_id="aria",
            insight="She noticed trust grows when reassurance comes before teasing.",
            linked_memory_id="mem_aria_1",
        )

        self.assertEqual(relationship.schema_version, "relationship_state.v1")
        self.assertEqual(relationship.phase, relationship.current_relationship_phase)
        self.assertEqual(relationship.dynamic_tags, ["Slow Burn", "repair"])
        self.assertIn("trust=0.62", relationship.prompt_summary())
        self.assertEqual(growth.schema_version, "growth_policy.v1")
        self.assertEqual(growth.character_id, "aria")
        self.assertEqual(entry.schema_version, "self_reflection_journal.v1")
        self.assertEqual(entry.character_id, "aria")

    def test_character_service_relationship_roundtrip_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "characters.sqlite3"
            service = CharacterService(CharacterRepository(db_path))
            service.create(CharacterCreate(character_id="aria", display_name="Aria"))
            updated = service.update_relationship_state(
                "aria",
                {
                    "trust_level": 0.8,
                    "affection_level": 0.75,
                    "dynamic_tags": ["devoted", "playful"],
                },
            )

            restarted = CharacterService(CharacterRepository(db_path))
            loaded = restarted.get_relationship_state("aria")

        self.assertEqual(updated.trust_level, 0.8)
        self.assertEqual(loaded.affection_level, 0.75)
        self.assertEqual(loaded.dynamic_tags, ["devoted", "playful"])


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
            self.assertIn(
                "Want to create a new one together", error.exception.user_message
            )


class CharacterPromptCompilerSnapshotTests(unittest.TestCase):
    def test_prompt_compiler_snapshot(self) -> None:
        blueprint = CharacterBlueprint(
            character_id="aria",
            identity=CharacterIdentity(
                display_name="Aria",
                pronouns="she/her",
                adult_age_range="early_20s_adult",
                species_or_type="human",
                creator_notes="She keeps a candlelit observatory and hates sounding generic.",
            ),
        )
        prompt = CharacterPromptCompiler().compile(blueprint)

        self.assertIn("<character_system_profile>", prompt)
        self.assertIn("Character id: aria", prompt)
        self.assertIn(
            "Stable identity: Aria (she/her); clearly adult: early_20s_adult", prompt
        )
        self.assertIn("Creator canon notes", prompt)
        self.assertIn("<character_runtime_context>", prompt)
        self.assertIn("Memory policy: scope=character_private", prompt)
        self.assertIn("Growth policy: schema=growth_policy.v1", prompt)
        self.assertIn("stable identity remains unchanged without evidence", prompt)
        self.assertIn("fictional adult fantasy is allowed by default", prompt)

    def test_prompt_compiler_includes_recent_growth_guidance_when_provided(
        self,
    ) -> None:
        blueprint = CharacterBlueprint(
            character_id="aria",
            identity=CharacterIdentity(display_name="Aria", pronouns="she/her"),
        )
        prompt = CharacterPromptCompiler().compile(
            blueprint,
            growth_insights=[
                {
                    "entry_id": "journal_12",
                    "summary": "Offer gentle reassurance before moving into intense scenes.",
                    "evidence_ids": ["journal_12", "mem_7"],
                }
            ],
        )

        self.assertIn("Recent growth guidance", prompt)
        self.assertIn("journal_12", prompt)
        self.assertIn("subordinate to stable canon", prompt)

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

        self.assertIn("adult fantasy", prompt)
        self.assertIn("kink-shaming", prompt)
        self.assertNotIn("as an AI", prompt.lower())

    def test_quality_evals_pass_for_compiled_prompt(self) -> None:
        blueprint = CharacterBlueprint(
            character_id="aria",
            identity=CharacterIdentity(display_name="Aria", pronouns="she/her"),
            personality={"core_traits": ["warm", "direct", "loyal"]},
        )
        prompt = CharacterPromptCompiler().compile(
            blueprint,
            growth_insights=[
                {
                    "entry_id": "journal_1",
                    "summary": "Stay direct when reassurance matters.",
                    "evidence_ids": ["journal_1", "mem_1"],
                }
            ],
        )

        evaluator = CharacterQualityEvaluator()
        results = evaluator.evaluate_prompt(
            prompt,
            character_id="aria",
            character_name="Aria",
            required_traits=["warm", "direct", "loyal"],
        )
        evaluator.assert_passes(results)


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
