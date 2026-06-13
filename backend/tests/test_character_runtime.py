"""Character runtime foundation coverage."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.core.memory import MemoryManager
from app.repositories.character_repo import CharacterRepository
from app.schemas.growth_policy import GrowthPolicy
from app.schemas.relationship_state import RelationshipPhase, RelationshipState
from app.schemas.self_reflection_journal import SelfReflectionJournalEntry
from app.schemas.character_blueprint import (
    AdultAgeRange,
    CharacterBlueprint,
    CharacterCreate,
    CharacterIdentity,
    CharacterUpdate,
    CommunicationProfile,
    PersonalityProfile,
)
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
    def test_prompt_compiler_includes_full_runtime_fields_without_private_notes(
        self,
    ) -> None:
        blueprint = CharacterBlueprint(
            character_id="aria",
            identity=CharacterIdentity(
                display_name="Aria",
                pronouns="she/her",
                adult_age_range="early_20s_adult",
                species_or_type="human",
                origin_archetype="moonlit confidante",
                tags=["Slow Burn"],
                creator_notes="private backstory draft that should not be injected",
            ),
            relationship=RelationshipState(
                character_id="aria",
                relationship_dynamic="warm, emotionally attentive companion",
                user_desired_experience="soft sanctuary after hard days",
                user_role_in_story="beloved co-conspirator",
                dynamic_tags=["slow_burn", "repair"],
                promises=["ask before sharp teasing"],
                rituals=["goodnight forehead kiss"],
            ),
        )
        prompt = CharacterPromptCompiler().compile(blueprint)

        self.assertIn("<character_system_prompt>", prompt)
        self.assertIn("## Stable identity", prompt)
        self.assertIn("Name: Aria.", prompt)
        self.assertIn("Adult baseline: clearly adult early_20s_adult", prompt)
        self.assertIn("Species/type: human.", prompt)
        self.assertIn("Origin/archetype: moonlit confidante.", prompt)
        self.assertIn("Key dynamics: slow_burn, repair.", prompt)
        self.assertIn("Promises: ask before sharp teasing.", prompt)
        self.assertIn("Rituals: goodnight forehead kiss.", prompt)
        self.assertIn(
            "User desired experience: soft sanctuary after hard days.", prompt
        )
        self.assertIn("Memory scope: character_private", prompt)
        self.assertIn("Character-scoped growth: True", prompt)
        self.assertNotIn("private backstory draft", prompt)

    def test_prompt_compiler_includes_recent_growth_and_journal_guidance_when_provided(
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
            journal_entries=[
                SelfReflectionJournalEntry(
                    entry_id="journal_13",
                    character_id="aria",
                    insight="Aria noticed that playful confidence works best after reassurance.",
                )
            ],
        )

        self.assertIn("## Growth insights", prompt)
        self.assertIn("Approved growth insights", prompt)
        self.assertIn("journal_12", prompt)
        self.assertIn("Recent journal context", prompt)
        self.assertIn("journal_13", prompt)

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

        self.assertIn("Fictional adult fantasy is allowed by default", prompt)
        self.assertIn("Treat fictional adult fantasy as fictional", prompt)
        self.assertIn("Do not moralize or break character", prompt)
        self.assertIn("kink-shaming", prompt)
        self.assertNotIn("as an AI", prompt.lower())

    def test_prompt_compiler_includes_required_sections_style_and_exact_roleplay_rule(
        self,
    ) -> None:
        blueprint = CharacterBlueprint(
            character_id="mira",
            identity=CharacterIdentity(display_name="Mira", pronouns="she/they"),
            communication=CommunicationProfile(
                style_notes="velvet-soft voice with mischievous confidence",
                avoid_style_rules=[
                    "do not sound clinical",
                    "avoid generic helper phrasing",
                ],
            ),
            personality=PersonalityProfile(
                core_traits=["playful", "protective", "bold"]
            ),
        )

        prompt = CharacterPromptCompiler().compile(blueprint)

        for section in [
            "## Stable identity",
            "## Communication style / voice",
            "## Personality and behavior rules",
            "## Avoid-style rules",
            "## Relationship premise / current phase / dynamic",
            "## Roleplay-first fantasy policy",
            "## Memory usage rules",
            "## Visual / scene hints",
        ]:
            self.assertIn(section, prompt)
        self.assertIn("Name: Mira", prompt)
        self.assertIn("velvet-soft voice", prompt)
        self.assertIn(CharacterPromptCompiler.ROLEPLAY_FIRST_RULE, prompt)
        self.assertNotIn("as an AI", prompt.lower())

    def test_prompt_compiler_bounds_long_fields_without_raw_json_or_private_notes(
        self,
    ) -> None:
        long_style = " ".join(["luminous" for _ in range(80)])
        blueprint = CharacterBlueprint(
            character_id="bounded",
            identity=CharacterIdentity(
                display_name="Bounded",
                creator_notes="SECRET PRIVATE CREATOR NOTE",
            ),
            communication=CommunicationProfile.model_construct(
                style_notes=long_style,
                avoid_style_rules=[],
                initiative_in_conversation=0.5,
            ),
            metadata={"private_notes": "SECRET METADATA NOTE"},
        )

        prompt = CharacterPromptCompiler().compile(blueprint)

        self.assertIn("luminous", prompt)
        self.assertIn("…", prompt)
        self.assertNotIn("SECRET PRIVATE CREATOR NOTE", prompt)
        self.assertNotIn("SECRET METADATA NOTE", prompt)
        self.assertNotIn("creator_notes", prompt)
        self.assertNotIn("{'", prompt)

    def test_prompt_compiler_relationship_phase_key_dynamics_and_roundtrip_structure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "characters.sqlite3"
            service = CharacterService(CharacterRepository(db_path))
            blueprint = service.create(
                CharacterCreate(
                    character_id="nova",
                    display_name="Nova",
                    relationship_dynamic="rivals-to-lovers spark with loyal aftercare",
                )
            )
            service.update_relationship_state(
                blueprint.character_id,
                {
                    "phase": RelationshipPhase.romantic,
                    "dynamic_tags": ["rivals_to_lovers", "protective_teasing"],
                    "unresolved_threads": ["the almost-confession after the duel"],
                },
            )

            prompt = service.compile_prompt("nova")

        self.assertIn("<character_system_prompt>", prompt)
        self.assertIn("<character_runtime_context>", prompt)
        self.assertIn("Phase: romantic", prompt)
        self.assertIn("Key dynamics: rivals_to_lovers, protective_teasing", prompt)
        self.assertIn("the almost-confession after the duel", prompt)

    def test_quality_eval_trait_adherence_and_growth_coherence(self) -> None:
        aria = CharacterBlueprint(
            character_id="aria",
            identity=CharacterIdentity(display_name="Aria", pronouns="she/her"),
            relationship=RelationshipState(character_id="aria", trust_level=0.82),
        )
        lyra = CharacterBlueprint(
            character_id="lyra",
            identity=CharacterIdentity(
                display_name="Lyra", pronouns="she/her", species_or_type="fox spirit"
            ),
            relationship=RelationshipState(character_id="lyra", trust_level=0.2),
        )
        compiler = CharacterPromptCompiler()
        aria_prompt = compiler.compile(
            aria,
            growth_insights=[
                {"entry_id": "j1", "summary": "Keep slow-burn reassurance visible."}
            ],
        )
        lyra_prompt = compiler.compile(lyra)

        self.assertNotEqual(aria_prompt, lyra_prompt)
        self.assertIn("Aria", aria_prompt)
        self.assertIn("trust=0.82", aria_prompt)
        self.assertIn("Keep slow-burn reassurance visible", aria_prompt)
        self.assertIn("Lyra", lyra_prompt)
        self.assertIn("fox spirit", lyra_prompt)
        self.assertNotIn("Aria", lyra_prompt)


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
