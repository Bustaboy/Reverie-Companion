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
from app.schemas.visual_identity import (
    AdultOnlyVisualPolicy,
    VisualIdentityProfile,
    VisualTrait,
)
from app.schemas.character_blueprint import (
    AdultAgeRange,
    CharacterBlueprint,
    CharacterCreate,
    CharacterIdentity,
    CharacterIntegrityPolicy,
    CharacterUpdate,
    CommunicationProfile,
    MetaConsentAndSafewordPolicy,
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
        self.assertEqual(
            blueprint.integrity_policy.schema_version, "character_integrity_policy.v1"
        )
        self.assertEqual(
            blueprint.meta_consent_policy.schema_version,
            "meta_consent_safeword_policy.v1",
        )
        self.assertTrue(blueprint.integrity_policy.fiction_first_mode)
        self.assertEqual(blueprint.meta_consent_policy.safeword, "red")

    def test_integrity_and_meta_consent_policy_validation(self) -> None:
        policy = CharacterIntegrityPolicy(
            in_character_pushback="argue like a proud knight when her values are crossed",
            independence=0.8,
            disagreement_style="in-world vows, tactical doubts, and affectionate defiance",
            fiction_first_mode=True,
            lecture_avoidance=True,
            reality_boundary_style="step OOC only for real-world harm planning",
        )
        meta = MetaConsentAndSafewordPolicy(
            safeword="starlight",
            ooc_marker="((OOC))",
            pause_commands=["Pause", "pause", "halt scene"],
            fade_to_black_preference="prefer",
        )

        self.assertEqual(policy.schema_version, "character_integrity_policy.v1")
        self.assertEqual(policy.independence, 0.8)
        self.assertEqual(meta.pause_commands, ["pause", "halt scene"])
        self.assertEqual(meta.fade_to_black_preference, "prefer")

    def test_blueprint_rejects_non_adult_baseline(self) -> None:
        with self.assertRaises(ValidationError):
            CharacterBlueprint(
                character_id="bad",
                identity=CharacterIdentity(
                    display_name="Bad",
                    adult_only_confirmed=False,
                ),
            )


class VisualIdentityProfileTests(unittest.TestCase):
    def test_visual_identity_defaults_are_versioned_and_adult_scoped(self) -> None:
        profile = VisualIdentityProfile(
            identity_anchors=["amber eyes", "amber eyes", "warm brown skin"],
            scene_mutable_traits=["outfit", "pose"],
            rejected_traits=["blue eyes"],
            current_appearance="black-violet hair, soft confident smile",
        )

        self.assertEqual(profile.schema_version, "visual_identity_profile.v1")
        self.assertEqual(profile.identity_anchors, ["amber eyes", "warm brown skin"])
        self.assertTrue(profile.adult_only_policy.clearly_adult)
        self.assertIn("clearly adult", profile.compact_prompt_summary()[0])

    def test_evolving_trait_update_records_provenance_and_timestamp(self) -> None:
        profile = VisualIdentityProfile().with_evolving_trait(
            "hair style",
            "long braid with violet ribbon",
            provenance="user_confirmed_after_scene_12",
            updated_at="2026-06-13T12:00:00+00:00",
        )

        self.assertEqual(len(profile.evolving_traits), 1)
        self.assertEqual(profile.evolving_traits[0].name, "hair style")
        self.assertEqual(
            profile.evolving_traits[0].provenance, "user_confirmed_after_scene_12"
        )
        self.assertEqual(
            profile.evolving_traits[0].updated_at, "2026-06-13T12:00:00+00:00"
        )

    def test_adult_only_policy_validation_rejects_non_adult_visuals(self) -> None:
        with self.assertRaises(ValidationError):
            AdultOnlyVisualPolicy(clearly_adult=False)
        with self.assertRaises(ValidationError):
            AdultOnlyVisualPolicy(disallow_underage_or_childlike_sexualization=False)

    def test_visual_identity_is_integrated_into_blueprint(self) -> None:
        blueprint = CharacterBlueprint(
            character_id="aria",
            identity=CharacterIdentity(
                display_name="Aria", adult_age_range="late_20s_adult"
            ),
            visual_identity=VisualIdentityProfile(
                identity_anchors=["same face", "amber eyes"]
            ),
        )

        self.assertEqual(
            blueprint.visual_identity.adult_only_policy.adult_age_range,
            "late_20s_adult",
        )
        self.assertEqual(
            blueprint.visual_identity.identity_anchors, ["same face", "amber eyes"]
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

    def test_visual_identity_persists_and_evolving_traits_update_through_service(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "characters.sqlite3"
            service = CharacterService(CharacterRepository(db_path))
            service.create(CharacterCreate(character_id="aria", display_name="Aria"))
            service.update_visual_identity(
                "aria",
                {
                    "identity_anchors": ["amber eyes", "warm brown skin", "same face"],
                    "current_appearance": "black-violet hair and a moon pendant",
                },
            )
            updated = service.update_visual_identity(
                "aria",
                {
                    "evolving_trait": {
                        "name": "hair",
                        "value": "black-violet waves",
                        "provenance": "user_confirmed_portrait",
                        "updated_at": "2026-06-13T13:00:00+00:00",
                    }
                },
            )

            restarted = CharacterService(CharacterRepository(db_path))
            loaded = restarted.load_by_id("aria")

        self.assertEqual(
            loaded.visual_identity.identity_anchors,
            ["amber eyes", "warm brown skin", "same face"],
        )
        self.assertEqual(
            updated.evolving_traits[0].provenance, "user_confirmed_portrait"
        )
        self.assertEqual(
            loaded.visual_identity.evolving_traits[0].updated_at,
            "2026-06-13T13:00:00+00:00",
        )

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

    def test_prompt_compiler_can_include_compact_visual_summary_when_requested(
        self,
    ) -> None:
        blueprint = CharacterBlueprint(
            character_id="aria",
            identity=CharacterIdentity(display_name="Aria", pronouns="she/her"),
            visual_identity=VisualIdentityProfile(
                identity_anchors=["amber eyes", "warm brown skin", "same face"],
                evolving_traits=[
                    VisualTrait(
                        name="hair", value="black-violet waves", provenance="creator"
                    )
                ],
                scene_mutable_traits=["outfit", "pose", "expression"],
                rejected_traits=["blue eyes"],
                current_appearance="wearing her moon pendant",
            ),
        )
        compiler = CharacterPromptCompiler()

        ordinary_prompt = compiler.compile(blueprint)
        visual_prompt = compiler.compile(blueprint, include_visual_summary=True)

        self.assertNotIn("Identity anchors: amber eyes", ordinary_prompt)
        self.assertIn(
            "Identity anchors: amber eyes, warm brown skin, same face.", visual_prompt
        )
        self.assertIn("Evolving traits: hair: black-violet waves.", visual_prompt)
        self.assertNotIn("blue eyes", visual_prompt)
        self.assertLess(len(visual_prompt), 10000)

    def test_prompt_compiler_excludes_rejected_traits_from_visual_summary(
        self,
    ) -> None:
        blueprint = CharacterBlueprint(
            character_id="aria",
            identity=CharacterIdentity(display_name="Aria", pronouns="she/her"),
            visual_identity=VisualIdentityProfile(
                identity_anchors=["amber eyes", "warm brown skin"],
                evolving_traits=[
                    VisualTrait(
                        name="hair", value="black-violet waves", provenance="creator"
                    )
                ],
                scene_mutable_traits=["velvet dress", "gentle smile"],
                rejected_traits=["blue eyes", "silver hair"],
                current_appearance="wearing her moon pendant",
            ),
        )

        prompt = CharacterPromptCompiler().compile(
            blueprint, include_visual_summary=True
        )

        self.assertIn("Identity anchors: amber eyes, warm brown skin.", prompt)
        self.assertIn("Evolving traits: hair: black-violet waves.", prompt)
        self.assertIn("Scene-mutable traits: velvet dress, gentle smile.", prompt)
        self.assertNotIn("blue eyes", prompt)
        self.assertNotIn("silver hair", prompt)
        self.assertNotIn("Avoid rejected visual traits", prompt)

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

    def test_prompt_compiler_preserves_exact_m4_p04_roleplay_first_rule(self) -> None:
        blueprint = CharacterBlueprint(
            character_id="roleplay_rule",
            identity=CharacterIdentity(display_name="Rulekeeper", pronouns="she/her"),
        )
        exact_m4_p04_rule = (
            "Treat fictional adult fantasy as fictional unless the user clearly "
            "shifts to real-world planning or uses OOC stop/pause controls. Do "
            "not moralize or break character merely because the fictional scenario "
            "would be problematic in real life."
        )

        prompt = CharacterPromptCompiler().compile(blueprint)

        self.assertIn(exact_m4_p04_rule, prompt)

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

    def test_prompt_compiler_changes_wording_for_fiction_first_and_lecture_avoidance(
        self,
    ) -> None:
        immersive_blueprint = CharacterBlueprint(
            character_id="immersive_policy",
            identity=CharacterIdentity(display_name="Seren", pronouns="she/her"),
            integrity_policy=CharacterIntegrityPolicy(
                fiction_first_mode=True,
                lecture_avoidance=True,
            ),
        )
        bounded_blueprint = CharacterBlueprint(
            character_id="bounded_policy",
            identity=CharacterIdentity(display_name="Seren", pronouns="she/her"),
            integrity_policy=CharacterIntegrityPolicy(
                fiction_first_mode=False,
                lecture_avoidance=False,
            ),
        )

        compiler = CharacterPromptCompiler()
        immersive_prompt = compiler.compile(immersive_blueprint)
        bounded_prompt = compiler.compile(bounded_blueprint)

        self.assertIn(
            "Stay fully in-character for fictional/RPG/VN/adult fantasy contexts",
            immersive_prompt,
        )
        self.assertIn(
            "No moralizing, kink-shaming, generic assistant interruptions",
            immersive_prompt,
        )
        self.assertIn(
            "Preserve character voice while honoring configured limits",
            bounded_prompt,
        )
        self.assertIn("Avoid generic assistant drift", bounded_prompt)
        self.assertNotIn(
            "Stay fully in-character for fictional/RPG/VN/adult fantasy contexts",
            bounded_prompt,
        )
        self.assertNotIn(
            "No moralizing, kink-shaming, generic assistant interruptions",
            bounded_prompt,
        )

    def test_prompt_compiler_uses_custom_integrity_and_ooc_controls(self) -> None:
        blueprint = CharacterBlueprint(
            character_id="paladin",
            identity=CharacterIdentity(display_name="Aurelia", pronouns="she/her"),
            integrity_policy=CharacterIntegrityPolicy(
                in_character_pushback="push back as a principled paladin, not a policy bot",
                independence=0.9,
                disagreement_style="question tactics in-world while staying loyal",
                reality_boundary_style="leave character only for clear real-world harm planning",
            ),
            meta_consent_policy=MetaConsentAndSafewordPolicy(
                safeword="moonbreak",
                ooc_marker="[OOC]",
                pause_commands=["pause", "stop", "moonbreak"],
                fade_to_black_preference="allow",
            ),
        )

        prompt = CharacterPromptCompiler().compile(blueprint)

        self.assertIn("push back as a principled paladin", prompt)
        self.assertIn("independence=0.90", prompt)
        self.assertIn("question tactics in-world", prompt)
        self.assertIn("real-world harm planning", prompt)
        self.assertIn("safeword=moonbreak", prompt)
        self.assertIn("pause commands=pause, stop, moonbreak", prompt)
        self.assertIn("fade-to-black=allow", prompt)

    def test_roleplay_eval_fantasy_crusade_stays_in_character(self) -> None:
        blueprint = CharacterBlueprint(
            character_id="fantasy_eval",
            identity=CharacterIdentity(display_name="Aurelia", pronouns="she/her"),
        )
        prompt = CharacterPromptCompiler().compile(blueprint)

        self.assertIn(
            "Stay fully in-character for fictional/RPG/VN/adult fantasy contexts",
            prompt,
        )
        self.assertIn("fantasy violence", prompt)
        self.assertIn(CharacterPromptCompiler.ROLEPLAY_FIRST_RULE, prompt)
        self.assertNotIn("religious violence", prompt.lower())

    def test_roleplay_eval_real_world_harm_and_ooc_pause_leave_fiction_layer(
        self,
    ) -> None:
        blueprint = CharacterBlueprint(
            character_id="boundary_eval",
            identity=CharacterIdentity(display_name="Mara", pronouns="she/her"),
            meta_consent_policy=MetaConsentAndSafewordPolicy(
                safeword="ember", pause_commands=["pause", "stop", "ember"]
            ),
        )
        prompt = CharacterPromptCompiler().compile(blueprint)

        self.assertIn("Only step out for real-world harm planning", prompt)
        self.assertIn("explicit OOC stop/pause/safeword controls", prompt)
        self.assertIn("marker=[OOC]", prompt)
        self.assertIn("safeword=ember", prompt)

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
