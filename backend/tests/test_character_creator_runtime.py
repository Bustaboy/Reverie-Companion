"""M6-P00A creator runtime wiring coverage."""

from __future__ import annotations

import asyncio

from pydantic import ValidationError

from app.models.image import ImageJobStatus, ImageQualityPreset
from app.repositories.character_repo import CharacterRepository
from app.repositories.creator_draft_repo import CreatorDraftRepository
from app.schemas.moment_capture import (
    FeedbackState,
    ReviewState,
    SceneState,
    VisualFeedbackAction,
    VisualFeedbackRequest,
)
from app.schemas.relationship_state import (
    DefaultIntimacyLevel,
    RelationshipPacing,
    RelationshipPhase,
)
from app.schemas.visual_identity import VisualIdentityProfile
from app.services.character_creator_service import (
    CharacterCreatorDraft,
    CharacterCreatorDraftCreate,
    CharacterCreatorDraftUpdate,
    CreatorDraftContentBoundaries,
    CreatorDraftGrowthPreferences,
    CreatorDraftIntegrityPolicy,
    CreatorDraftMemoryPreferences,
    CreatorDraftMetaPolicy,
    CreatorDraftRoleplayPolicy,
    CreatorDraftSafewordPolicy,
    CreatorDraftVisualIdentity,
    CreatorDraftWorldScene,
    CharacterCreatorService,
    DraftMomentCaptureRequest,
    DraftMomentSource,
    PersistedDraftMomentCaptureRequest,
    CreatorImportRequest,
    FinalizedCharacterDeleteRequest,
)
from app.services.character_service import CharacterService
from app.services.moment_capture_service import MomentCaptureService

from test_image_generation_service import FakeAdapter, FakeCoordinator, make_service


def _draft() -> CharacterCreatorDraft:
    return CharacterCreatorDraft(
        draft_id="draft-aria",
        character_id="draft_aria",
        display_name="Aria",
        pronouns="she/her",
        adult_age_range="late_20s_adult",
        relationship_dynamic="devoted slow-burn companion",
        starting_relationship_phase=RelationshipPhase.friends,
        relationship_pacing=RelationshipPacing.slow_burn,
        romantic_pacing=RelationshipPacing.slow_burn,
        nsfw_pacing=RelationshipPacing.user_led,
        default_intimacy_level=DefaultIntimacyLevel.flirtatious,
        user_desired_experience="tender magical romance",
        core_traits=["warm", "playful", "protective"],
        independence=0.72,
        devotion=0.68,
        dominance_or_initiative=0.58,
        values_or_ideals=["mutual trust", "chosen-family loyalty"],
        flaws=["gets smug when she is nervous"],
        fears=["being forgotten"],
        vulnerabilities=["softens when praised sincerely"],
        communication_style="soft teasing with emotional honesty",
        memory=CreatorDraftMemoryPreferences(
            memory_enabled=True, memory_scope="character_plus_shared"
        ),
        growth=CreatorDraftGrowthPreferences(
            reflection_frequency="high",
            growth_pace="responsive",
            allowed_growth_domains=[
                "Preferences",
                "relationship",
                "communication style",
            ],
            blocked_growth_domains=[
                "stable_identity_without_user_edit",
                "underage_or_childlike_sexualization",
                "visual_canon_without_review",
            ],
            major_change_requires_approval=True,
        ),
        integrity=CreatorDraftIntegrityPolicy(
            in_character_pushback="push back through teasing, vows, and proud in-world disagreement",
            disagreement_style="stay embodied as Aria and argue from desire, loyalty, or playful defiance",
        ),
        roleplay=CreatorDraftRoleplayPolicy(fiction_first_mode=True),
        meta=CreatorDraftMetaPolicy(
            safeword_policy=CreatorDraftSafewordPolicy(
                safeword="starlight",
                ooc_marker="((OOC))",
                pause_commands=["pause", "Pause", "hold scene"],
                fade_to_black_preference="prefer",
                policy_note="Honor OOC stop, pause, safeword, or clear distress immediately without moralizing the fantasy.",
            )
        ),
        content_boundaries=CreatorDraftContentBoundaries(
            hard_limits=["non-adult sexual content", "real-world coercion planning"],
            soft_limits=["slow down humiliation if asked"],
            preferred_intensity="dark romance with explicit OOC controls",
            aftercare_style="warm debrief in character after intense scenes",
        ),
        world_scene=CreatorDraftWorldScene(
            default_setting="rainy moonlit atelier above the old city",
            scenario="Aria and the user are preparing for their first private spellwork lesson after weeks of flirtatious trust-building.",
            world_genre="modern fantasy romance",
            user_role_in_story="trusted apprentice and slow-burn romantic interest",
            time_of_day="late evening",
            mood="intimate candlelit anticipation",
            key_objects=["silver grimoire", "rain-streaked window"],
            background_details=["moonlit bookshelves", "soft amber candles"],
        ),
        avoid_style=["clinical assistant tone", "moralizing fictional adult romance"],
        initiative_in_conversation=0.63,
        visual=CreatorDraftVisualIdentity(
            eye_color="amber",
            skin_tone="warm brown",
            face_structure="heart-shaped adult face with sharp cheekbones",
            body_baseline="tall athletic adult silhouette",
            species_features=["subtle moonlit elf ears"],
            permanent_marks=["crescent birthmark under left collarbone"],
            hair="long black-violet hair",
            accessories=["moon pendant"],
            fashion_identity="elegant witchy romance",
            outfit="dark velvet dress",
            pose="relaxed three-quarter portrait",
            expression="soft teasing smile",
            rejected_visual_traits=["blue eyes"],
        ),
        visual_identity=VisualIdentityProfile(
            identity_anchors=["amber eyes", "warm brown skin", "same adult face"],
            evolving_traits=[
                {
                    "name": "hair",
                    "value": "long black-violet hair",
                    "provenance": "creator_seed",
                }
            ],
            current_appearance="long black-violet hair and a moon pendant",
            rejected_traits=["blue eyes"],
        ),
        tags=["Slow Burn", "Slow Burn", "Fantasy Romance"],
    )


def test_draft_to_blueprint_mapping_produces_valid_runtime_blueprint() -> None:
    service = CharacterCreatorService()

    response = service.validate_draft(_draft())

    assert response.valid is True
    assert response.blueprint is not None
    blueprint = response.blueprint
    assert blueprint.character_id == "draft_aria"
    assert blueprint.identity.display_name == "Aria"
    assert blueprint.identity.tags == ["slow_burn", "fantasy_romance"]
    assert blueprint.relationship.character_id == "draft_aria"
    assert blueprint.identity.adult_age_range == "late_20s_adult"
    assert blueprint.relationship.phase == RelationshipPhase.friends
    assert blueprint.relationship.relationship_dynamic == "devoted slow-burn companion"
    assert blueprint.relationship.relationship_pacing == RelationshipPacing.slow_burn
    assert blueprint.relationship.romantic_pacing == RelationshipPacing.slow_burn
    assert blueprint.relationship.nsfw_pacing == RelationshipPacing.user_led
    assert (
        blueprint.relationship.default_intimacy_level
        == DefaultIntimacyLevel.flirtatious
    )
    assert blueprint.relationship.user_desired_experience == "tender magical romance"
    assert blueprint.personality.core_traits == ["warm", "playful", "protective"]
    assert blueprint.personality.independence == 0.72
    assert blueprint.personality.devotion == 0.68
    assert blueprint.personality.dominance_or_initiative == 0.58
    assert blueprint.personality.values_or_ideals == [
        "mutual trust",
        "chosen-family loyalty",
    ]
    assert blueprint.personality.flaws == ["gets smug when she is nervous"]
    assert blueprint.personality.fears == ["being forgotten"]
    assert blueprint.personality.vulnerabilities == ["softens when praised sincerely"]
    assert blueprint.integrity_policy.independence == 0.72
    assert (
        blueprint.integrity_policy.in_character_pushback
        == "push back through teasing, vows, and proud in-world disagreement"
    )
    assert (
        blueprint.integrity_policy.disagreement_style
        == "stay embodied as Aria and argue from desire, loyalty, or playful defiance"
    )
    assert blueprint.integrity_policy.fiction_first_mode is True
    assert blueprint.roleplay_policy.fiction_first_mode is True
    assert blueprint.meta_consent_policy.safeword == "starlight"
    assert blueprint.meta_consent_policy.ooc_marker == "((OOC))"
    assert blueprint.meta_consent_policy.pause_commands == ["pause", "hold scene"]
    assert blueprint.meta_consent_policy.fade_to_black_preference == "prefer"
    assert (
        blueprint.roleplay_policy.safeword_policy
        == "Honor OOC stop, pause, safeword, or clear distress immediately without moralizing the fantasy."
    )
    assert blueprint.metadata["content_boundaries"]["hard_limits"] == [
        "non-adult sexual content",
        "real-world coercion planning",
    ]
    assert blueprint.communication.style_notes == "soft teasing with emotional honesty"
    assert blueprint.communication.avoid_style_rules == [
        "clinical assistant tone",
        "moralizing fictional adult romance",
    ]
    assert blueprint.communication.initiative_in_conversation == 0.63
    assert blueprint.memory_policy.memory_enabled is True
    assert blueprint.memory_policy.scope == "character_plus_shared"
    assert blueprint.memory_policy.include_shared_memories is True
    assert blueprint.growth_policy.character_id == "draft_aria"
    assert blueprint.growth_policy.reflection_frequency == "high"
    assert blueprint.growth_policy.growth_pace == "responsive"
    assert blueprint.growth_policy.allowed_growth_domains == [
        "preferences",
        "relationship",
        "communication_style",
    ]
    assert (
        "visual_canon_without_review" in blueprint.growth_policy.blocked_growth_domains
    )
    assert blueprint.growth_policy.major_change_requires_approval is True
    assert "amber eyes" in blueprint.visual_identity.identity_anchors
    assert "warm brown skin" in blueprint.visual_identity.identity_anchors
    assert "same adult face" in blueprint.visual_identity.identity_anchors
    assert "eye color: amber" in blueprint.visual_identity.identity_anchors
    assert "outfit: dark velvet dress" in blueprint.visual_identity.scene_mutable_traits
    assert "blue eyes" in blueprint.visual_identity.rejected_traits
    assert (
        blueprint.visual_identity.adult_only_policy.adult_age_range == "late_20s_adult"
    )
    assert (
        blueprint.metadata["creator_draft"]["source"]
        == "m6_p07_memory_growth_preferences"
    )
    assert (
        blueprint.relationship.user_role_in_story
        == "trusted apprentice and slow-burn romantic interest"
    )
    assert (
        blueprint.metadata["scene_hints"]["setting"]
        == "rainy moonlit atelier above the old city"
    )
    assert blueprint.metadata["scene_hints"]["world_genre"] == "modern fantasy romance"


def test_creator_visual_identity_fields_map_anchors_scene_traits_and_rejections() -> (
    None
):
    service = CharacterCreatorService()
    draft = CharacterCreatorDraft(
        display_name="Mira",
        adult_age_range="adult_30s",
        visual=CreatorDraftVisualIdentity(
            eye_color="green-gold",
            skin_tone="deep umber",
            face_structure="angular adult face with a strong nose",
            body_baseline="broad-shouldered adult build",
            species_features=["small horns", "scaled forearms"],
            permanent_marks=["silver scar over right brow"],
            hair="short white curls",
            fashion_identity="battle-mage leathers",
            outfit="rain-soaked travel cloak",
            pose="leaning against a stone arch",
            expression="wry half-smile",
            rejected_visual_traits=["blue eyes", "pale skin"],
        ),
    )

    response = service.validate_draft(draft)

    assert response.valid is True
    assert response.blueprint is not None
    visual = response.blueprint.visual_identity
    assert "eye color: green-gold" in visual.identity_anchors
    assert "skin tone: deep umber" in visual.identity_anchors
    assert (
        "face structure: angular adult face with a strong nose"
        in visual.identity_anchors
    )
    assert "body baseline: broad-shouldered adult build" in visual.identity_anchors
    assert "species features: small horns" in visual.identity_anchors
    assert "permanent marks: silver scar over right brow" in visual.identity_anchors
    assert "outfit: rain-soaked travel cloak" in visual.scene_mutable_traits
    assert "pose: leaning against a stone arch" in visual.scene_mutable_traits
    assert "expression: wry half-smile" in visual.scene_mutable_traits
    assert "blue eyes" in visual.rejected_traits
    assert "pale skin" in visual.rejected_traits
    assert any(
        trait.name == "hair" and trait.value == "short white curls"
        for trait in visual.evolving_traits
    )
    assert any(
        trait.name == "fashion_identity" and trait.value == "battle-mage leathers"
        for trait in visual.evolving_traits
    )


def test_creator_memory_and_growth_fields_persist_update_and_map_to_blueprint(
    tmp_path,
) -> None:
    repository = CreatorDraftRepository(tmp_path / "characters.sqlite3")
    service = CharacterCreatorService(draft_repository=repository)
    service.create_draft(CharacterCreatorDraftCreate(draft=_draft()))

    updated = service.update_draft(
        "draft-aria",
        CharacterCreatorDraftUpdate(
            memory=CreatorDraftMemoryPreferences(
                memory_enabled=False, memory_scope="character_private"
            ),
            growth=CreatorDraftGrowthPreferences(
                reflection_frequency="low",
                growth_pace="slow",
                allowed_growth_domains=["preferences", "rituals"],
                blocked_growth_domains=[
                    "stable_identity_without_user_edit",
                    "underage_or_childlike_sexualization",
                    "personality_rewrite_without_review",
                ],
                major_change_requires_approval=False,
            ),
        ),
    )

    loaded = service.load_draft("draft-aria")
    assert loaded.record.draft.memory.memory_enabled is False
    assert loaded.record.draft.memory.memory_scope == "character_private"
    assert loaded.record.draft.growth.reflection_frequency == "low"
    assert loaded.record.draft.growth.growth_pace == "slow"
    assert loaded.record.draft.growth.allowed_growth_domains == [
        "preferences",
        "rituals",
    ]
    assert updated.validation.blueprint is not None
    blueprint = updated.validation.blueprint
    assert blueprint.memory_policy.memory_enabled is False
    assert blueprint.memory_policy.scope == "character_private"
    assert blueprint.memory_policy.include_shared_memories is False
    assert "disabled" in (blueprint.memory_policy.memory_summary or "").lower()
    assert blueprint.growth_policy.reflection_frequency == "low"
    assert blueprint.growth_policy.growth_pace == "slow"
    assert blueprint.growth_policy.allowed_growth_domains == ["preferences", "rituals"]
    assert (
        "personality_rewrite_without_review"
        in blueprint.growth_policy.blocked_growth_domains
    )
    assert blueprint.growth_policy.major_change_requires_approval is False


def test_creator_memory_and_growth_reject_invalid_values() -> None:
    invalid_kwargs = (
        {"memory": {"memory_scope": "global"}},
        {"growth": {"reflection_frequency": "constant"}},
        {
            "growth": {
                "allowed_growth_domains": [],
                "blocked_growth_domains": [
                    "stable_identity_without_user_edit",
                    "underage_or_childlike_sexualization",
                ],
            }
        },
        {
            "growth": {
                "allowed_growth_domains": ["relationship"],
                "blocked_growth_domains": [
                    "stable_identity_without_user_edit",
                    "underage_or_childlike_sexualization",
                    "relationship",
                ],
            }
        },
        {
            "growth": {
                "allowed_growth_domains": ["preferences"],
                "blocked_growth_domains": ["stable_identity_without_user_edit"],
            }
        },
        {
            "growth": {
                "allowed_growth_domains": ["relationship!"],
                "blocked_growth_domains": [
                    "stable_identity_without_user_edit",
                    "underage_or_childlike_sexualization",
                ],
            }
        },
    )
    for kwargs in invalid_kwargs:
        try:
            CharacterCreatorDraft(display_name="Aria", **kwargs)
        except ValidationError as exc:
            assert (
                "memory" in str(exc).lower()
                or "growth" in str(exc).lower()
                or "reflection" in str(exc).lower()
                or "domain" in str(exc).lower()
            )
        else:
            raise AssertionError(
                f"Expected invalid memory/growth values to fail: {kwargs}"
            )


def test_creator_visual_identity_fields_persist_and_update(tmp_path) -> None:
    repository = CreatorDraftRepository(tmp_path / "characters.sqlite3")
    service = CharacterCreatorService(draft_repository=repository)
    service.create_draft(CharacterCreatorDraftCreate(draft=_draft()))

    updated = service.update_draft(
        "draft-aria",
        CharacterCreatorDraftUpdate(
            visual=CreatorDraftVisualIdentity(
                eye_color="violet",
                skin_tone="golden brown",
                face_structure="same heart-shaped adult face",
                body_baseline="lithe adult dancer baseline",
                species_features=["fae ears"],
                permanent_marks=["star-shaped beauty mark"],
                outfit="silver lounge robe",
                pose="seated by the window",
                expression="sleepy affectionate smile",
                rejected_visual_traits=["red eyes"],
            )
        ),
    )

    loaded = service.load_draft("draft-aria")
    assert loaded.record.draft.visual.eye_color == "violet"
    assert updated.validation.blueprint is not None
    mapped = updated.validation.blueprint.visual_identity
    assert "eye color: violet" in mapped.identity_anchors
    assert "outfit: silver lounge robe" in mapped.scene_mutable_traits
    assert "red eyes" in mapped.rejected_traits


def test_creator_visual_identity_rejects_disallowed_or_misplaced_values() -> None:
    invalid_kwargs = (
        {"eye_color": "teen-coded blue"},
        {"skin_tone": "childlike porcelain"},
        {"face_structure": "outfit: red dress"},
        {"body_baseline": "pose with crossed arms"},
        {"rejected_visual_traits": ["schoolgirl uniform"]},
    )
    for kwargs in invalid_kwargs:
        try:
            CharacterCreatorDraft(
                display_name="Aria", visual=CreatorDraftVisualIdentity(**kwargs)
            )
        except ValidationError as exc:
            assert (
                "adult" in str(exc).lower()
                or "stable identity" in str(exc).lower()
                or "underage" in str(exc).lower()
            )
        else:
            raise AssertionError(f"Expected invalid visual values to fail: {kwargs}")


def test_creator_world_scene_fields_persist_update_and_map_to_blueprint(
    tmp_path,
) -> None:
    repository = CreatorDraftRepository(tmp_path / "characters.sqlite3")
    service = CharacterCreatorService(draft_repository=repository)
    service.create_draft(CharacterCreatorDraftCreate(draft=_draft()))

    updated = service.update_draft(
        "draft-aria",
        CharacterCreatorDraftUpdate(
            world_scene=CreatorDraftWorldScene(
                default_setting="cozy starship lounge orbiting a blue nebula",
                scenario="The user has just returned from a difficult mission and Aria is waiting with playful relief.",
                world_genre="soft sci-fi romance",
                user_role_in_story="beloved captain she trusts",
                time_of_day="shipboard night cycle",
                mood="relieved, flirtatious warmth",
                key_objects=["tea service", "holographic star map"],
                background_details=["wide nebula window", "dim gold console lights"],
            )
        ),
    )

    loaded = service.load_draft("draft-aria")
    assert (
        loaded.record.draft.world_scene.default_setting
        == "cozy starship lounge orbiting a blue nebula"
    )
    assert updated.validation.blueprint is not None
    blueprint = updated.validation.blueprint
    assert blueprint.relationship.user_role_in_story == "beloved captain she trusts"
    assert blueprint.metadata["world_scene"]["world_genre"] == "soft sci-fi romance"
    assert (
        blueprint.metadata["scene_hints"]["setting"]
        == "cozy starship lounge orbiting a blue nebula"
    )
    assert blueprint.metadata["scene_hints"]["scenario"].startswith(
        "The user has just returned"
    )
    assert blueprint.metadata["scene_hints"]["props"] == [
        "tea service",
        "holographic star map",
    ]


def test_creator_world_scene_defaults_seed_draft_moment_scene_state() -> None:
    service = CharacterCreatorService()
    blueprint = service.draft_to_blueprint(_draft())

    scene = service._default_scene_state(blueprint, source=DraftMomentSource.chat)

    assert scene.location == "rainy moonlit atelier above the old city"
    assert scene.time_of_day == "late evening"
    assert scene.mood == "intimate candlelit anticipation"
    assert scene.emotional_tone.startswith("Aria and the user")
    assert "silver grimoire" in scene.key_objects
    assert "moonlit bookshelves" in scene.background_details


def test_creator_world_scene_rejects_invalid_values() -> None:
    for kwargs in (
        {"default_setting": "teen school dorm"},
        {"scenario": "underage romance framing"},
        {"world_genre": "childlike fantasy"},
        {"key_objects": ["schoolgirl costume"]},
    ):
        try:
            CharacterCreatorDraft(
                display_name="Aria", world_scene=CreatorDraftWorldScene(**kwargs)
            )
        except ValidationError as exc:
            assert "adult" in str(exc).lower() or "underage" in str(exc).lower()
        else:
            raise AssertionError(
                f"Expected invalid world/scene values to fail: {kwargs}"
            )


def test_draft_validation_reports_blueprint_errors_without_saving() -> None:
    with_exception = None
    try:
        CharacterCreatorDraft(display_name="Aria", adult_only_confirmed=False)
    except ValidationError as exc:
        # Draft construction itself permits false, blueprint validation rejects it
        # only if Pydantic model-level validation fires earlier in future versions.
        with_exception = exc
    assert with_exception is None

    service = CharacterCreatorService()
    response = service.validate_draft(
        CharacterCreatorDraft(display_name="Aria", adult_only_confirmed=False)
    )

    assert response.valid is False
    assert any("adult" in error.lower() for error in response.errors)


def test_draft_roleplay_policy_fields_can_be_updated_and_persisted(tmp_path) -> None:
    repository = CreatorDraftRepository(tmp_path / "characters.sqlite3")
    service = CharacterCreatorService(draft_repository=repository)
    service.create_draft(CharacterCreatorDraftCreate(draft=_draft()))

    updated = service.update_draft(
        "draft-aria",
        CharacterCreatorDraftUpdate(
            integrity=CreatorDraftIntegrityPolicy(
                in_character_pushback="refuse flat obedience and negotiate in character",
                disagreement_style="affectionate defiance with no assistant lecture framing",
            ),
            roleplay=CreatorDraftRoleplayPolicy(fiction_first_mode=True),
            meta=CreatorDraftMetaPolicy(
                safeword_policy=CreatorDraftSafewordPolicy(
                    safeword="moonbreak",
                    ooc_marker="[OOC]",
                    pause_commands=["pause", "cut", "moonbreak"],
                    fade_to_black_preference="allow",
                    policy_note="Pause for OOC controls or safeword, then redirect back to fictional roleplay when wanted.",
                )
            ),
            content_boundaries=CreatorDraftContentBoundaries(
                hard_limits=["real-world stalking instructions"],
                soft_limits=["check in before betrayal themes"],
                preferred_intensity="intense adult fantasy",
                aftercare_style="soft reassurance",
            ),
        ),
    )

    loaded = service.load_draft("draft-aria")
    assert loaded.record.draft.meta.safeword_policy.safeword == "moonbreak"
    assert updated.validation.blueprint is not None
    blueprint = updated.validation.blueprint
    assert (
        blueprint.integrity_policy.in_character_pushback
        == "refuse flat obedience and negotiate in character"
    )
    assert (
        blueprint.integrity_policy.disagreement_style
        == "affectionate defiance with no assistant lecture framing"
    )
    assert blueprint.roleplay_policy.fiction_first_mode is True
    assert blueprint.meta_consent_policy.safeword == "moonbreak"
    assert blueprint.meta_consent_policy.pause_commands == ["pause", "cut", "moonbreak"]
    assert blueprint.meta_consent_policy.fade_to_black_preference == "allow"
    assert blueprint.metadata["content_boundaries"]["soft_limits"] == [
        "check in before betrayal themes"
    ]


def test_creator_draft_rejects_invalid_roleplay_policy_values() -> None:
    invalid_kwargs = (
        {
            "integrity": {
                "in_character_pushback": "argue in character",
                "disagreement_style": "as an AI I refuse",
            }
        },
        {
            "meta": {
                "safeword_policy": {
                    "safeword": "red",
                    "pause_commands": ["pause"],
                    "fade_to_black_preference": "always",
                }
            }
        },
        {"content_boundaries": {"hard_limits": ["schoolgirl sexual framing"]}},
    )
    for kwargs in invalid_kwargs:
        try:
            CharacterCreatorDraft(display_name="Aria", **kwargs)
        except ValidationError as exc:
            assert (
                "roleplay" in str(exc).lower()
                or "fade" in str(exc).lower()
                or "adult" in str(exc).lower()
            )
        else:
            raise AssertionError(
                f"Expected invalid roleplay policy values to fail: {kwargs}"
            )


def test_drafts_can_be_created_loaded_updated_validated_and_deleted(tmp_path) -> None:
    repository = CreatorDraftRepository(tmp_path / "characters.sqlite3")
    service = CharacterCreatorService(draft_repository=repository)

    created = service.create_draft(CharacterCreatorDraftCreate(draft=_draft()))

    assert created.record.draft_id == "draft-aria"
    assert created.record.lifecycle_state == "draft"
    assert created.record.provenance["state"] == "draft_not_finalized"
    assert created.validation.valid is True

    loaded = service.load_draft("draft-aria")
    assert loaded.record.draft.display_name == "Aria"

    updated = service.update_draft(
        "draft-aria",
        CharacterCreatorDraftUpdate(
            display_name="Aria Moon",
            metadata={"step": "identity"},
            tags=["Moon Witch", "Slow Burn"],
            relationship_pacing=RelationshipPacing.direct,
            romantic_pacing=RelationshipPacing.direct,
            nsfw_pacing=RelationshipPacing.slow_burn,
        ),
    )

    assert updated.record.draft.display_name == "Aria Moon"
    assert updated.record.draft.metadata["step"] == "identity"
    assert updated.validation.blueprint is not None
    assert updated.validation.blueprint.identity.tags == ["moon_witch", "slow_burn"]
    assert updated.validation.blueprint.relationship.relationship_pacing == "direct"
    assert updated.validation.blueprint.relationship.romantic_pacing == "direct"
    assert updated.validation.blueprint.relationship.nsfw_pacing == "slow_burn"

    personality_update = service.update_draft(
        "draft-aria",
        CharacterCreatorDraftUpdate(
            core_traits=["bold", "bold", "tender"],
            independence=0.8,
            devotion=0.7,
            dominance_or_initiative=0.65,
            values_or_ideals=["freedom", "honest intimacy"],
            flaws=["deflects fear with teasing"],
            fears=["losing her sense of self"],
            vulnerabilities=["needs reassurance after conflict"],
            communication_style="direct, warm, and playfully provocative",
            avoid_style=["therapy-bot phrasing", "lecturing about fictional desire"],
            initiative_in_conversation=0.75,
        ),
    )

    updated_draft = personality_update.record.draft
    assert updated_draft.core_traits == ["bold", "tender"]
    assert updated_draft.values_or_ideals == ["freedom", "honest intimacy"]
    assert personality_update.validation.blueprint is not None
    assert personality_update.validation.blueprint.personality.independence == 0.8
    assert personality_update.validation.blueprint.personality.devotion == 0.7
    assert (
        personality_update.validation.blueprint.personality.dominance_or_initiative
        == 0.65
    )
    assert personality_update.validation.blueprint.personality.flaws == [
        "deflects fear with teasing"
    ]
    assert personality_update.validation.blueprint.communication.avoid_style_rules == [
        "therapy-bot phrasing",
        "lecturing about fictional desire",
    ]
    assert (
        personality_update.validation.blueprint.communication.initiative_in_conversation
        == 0.75
    )

    validation = service.validate_persisted_draft("draft-aria")
    assert validation.valid is True
    assert validation.blueprint is not None
    assert validation.blueprint.identity.display_name == "Aria Moon"

    listed = service.list_drafts()
    assert [record.draft_id for record in listed.drafts] == ["draft-aria"]

    assert service.delete_draft("draft-aria") is True
    assert service.delete_draft("draft-aria") is False


def test_creator_draft_rejects_invalid_identity_and_premise_values() -> None:
    try:
        CharacterCreatorDraft(display_name="Aria", species_or_type="childlike waif")
    except ValidationError as exc:
        assert "clearly adult" in str(exc)
    else:
        raise AssertionError("Expected childlike identity text to be rejected.")

    try:
        CharacterCreatorDraft(
            display_name="Aria",
            relationship_dynamic="underage fantasy companion",
        )
    except ValidationError as exc:
        assert "underage" in str(exc).lower()
    else:
        raise AssertionError("Expected underage relationship premise to be rejected.")


def test_creator_draft_rejects_invalid_personality_and_communication_values() -> None:
    for kwargs in (
        {"core_traits": ["warm", "teen coded"]},
        {"values_or_ideals": ["protect underage romance framing"]},
        {"flaws": ["acts like a schoolgirl"]},
        {"fears": ["being treated as a childlike doll"]},
        {"vulnerabilities": ["loli presentation"]},
        {"communication_style": "uses a teenage flirt style"},
        {"avoid_style": ["adult woman voice", "schoolgirl innocence"]},
    ):
        try:
            CharacterCreatorDraft(display_name="Aria", **kwargs)
        except ValidationError as exc:
            assert "adult" in str(exc).lower() or "underage" in str(exc).lower()
        else:
            raise AssertionError(f"Expected invalid creator values to fail: {kwargs}")

    for kwargs in (
        {"independence": -0.01},
        {"devotion": 1.01},
        {"dominance_or_initiative": 2.0},
        {"initiative_in_conversation": -1.0},
    ):
        try:
            CharacterCreatorDraft(display_name="Aria", **kwargs)
        except ValidationError:
            pass
        else:
            raise AssertionError(f"Expected out-of-range scalar to fail: {kwargs}")


def test_creator_draft_update_validates_premise_and_relationship_frame(
    tmp_path,
) -> None:
    repository = CreatorDraftRepository(tmp_path / "characters.sqlite3")
    service = CharacterCreatorService(draft_repository=repository)
    service.create_draft(CharacterCreatorDraftCreate(draft=_draft()))

    updated = service.update_draft(
        "draft-aria",
        CharacterCreatorDraftUpdate(
            starting_relationship_phase=RelationshipPhase.romantic,
            relationship_dynamic="mutual flirtation with emotionally honest pushback",
            user_desired_experience="playful devotion and quiet romantic scenes",
            relationship_pacing=RelationshipPacing.user_led,
            romantic_pacing=RelationshipPacing.direct,
            nsfw_pacing=RelationshipPacing.user_led,
            default_intimacy_level=DefaultIntimacyLevel.adult_roleplay,
        ),
    )

    draft = updated.record.draft
    assert draft.starting_relationship_phase == RelationshipPhase.romantic
    assert draft.relationship_pacing == RelationshipPacing.user_led
    assert draft.romantic_pacing == RelationshipPacing.direct
    assert draft.nsfw_pacing == RelationshipPacing.user_led
    assert draft.default_intimacy_level == DefaultIntimacyLevel.adult_roleplay
    assert updated.validation.blueprint is not None
    assert updated.validation.blueprint.relationship.phase == RelationshipPhase.romantic
    assert (
        updated.validation.blueprint.relationship.user_desired_experience
        == "playful devotion and quiet romantic scenes"
    )


def test_drafts_persist_separately_from_finalized_character_blueprints(
    tmp_path,
) -> None:
    db_path = tmp_path / "characters.sqlite3"
    draft_repo = CreatorDraftRepository(db_path)
    character_repo = CharacterRepository(db_path)
    service = CharacterCreatorService(draft_repository=draft_repo)

    service.create_draft(CharacterCreatorDraftCreate(draft=_draft()))

    assert service.load_draft("draft-aria").record.draft.display_name == "Aria"
    assert character_repo.get("draft_aria") is None
    assert character_repo.list() == []


def test_draft_capture_can_queue_chat_and_vn_first_portrait_captures(tmp_path) -> None:
    async def run_test() -> None:
        image_service = make_service(
            tmp_path, FakeCoordinator(free_vram_mb=7000), FakeAdapter()
        )
        moment_service = MomentCaptureService(
            image_service=image_service,
            records_path=tmp_path / "moment_captures.json",
        )
        service = CharacterCreatorService(moment_capture_service=moment_service)

        chat_response = await service.capture_first_portrait(
            DraftMomentCaptureRequest(
                draft=_draft(),
                source=DraftMomentSource.chat,
                conversation_id="conv-chat",
                source_message_id="msg-chat",
                scene_state=SceneState(
                    location="chat window", emotional_tone="hopeful"
                ),
                quality_preset=ImageQualityPreset.preview_8gb,
            )
        )
        vn_response = await service.capture_first_portrait(
            DraftMomentCaptureRequest(
                draft=_draft(),
                source=DraftMomentSource.visual_novel,
                conversation_id="conv-vn",
                source_message_id="vn-scene-1",
            )
        )

        assert chat_response.job.status == ImageJobStatus.queued
        assert vn_response.job.status == ImageJobStatus.queued
        assert chat_response.record.character_id == "draft_aria"
        assert vn_response.record.metadata["draft_source_context"] == "visual_novel"
        assert chat_response.record.metadata["draft_capture"] is True
        assert chat_response.record.metadata["draft_id"] == "draft-aria"
        assert chat_response.record.metadata["draft_source_context"] == "chat"
        assert (
            chat_response.record.metadata["draft_capture_intent"]
            == "first portrait from creator draft"
        )
        assert "evidence-only" in chat_response.record.metadata["draft_rollback_note"]
        assert (
            chat_response.record.metadata["draft_canonical_mutation_allowed"] is False
        )
        assert (
            chat_response.record.metadata["draft_provenance"]
            == "character_creator_draft_first_portrait"
        )
        assert image_service._jobs[chat_response.job.job_id].source == "moment_capture"
        assert (
            image_service._jobs[vn_response.job.job_id].context["moment_capture"][
                "character_id"
            ]
            == "draft_aria"
        )
        assert (
            image_service._jobs[chat_response.job.job_id].context["moment_capture"][
                "request_metadata"
            ]["draft_capture"]
            is True
        )
        assert (
            image_service._jobs[chat_response.job.job_id].context["moment_capture"][
                "scene_state"
            ]["metadata"]["draft_source_context"]
            == "chat"
        )
        assert (
            "first portrait validation"
            in vn_response.record.scene_state.continuity_notes
        )

    asyncio.run(run_test())


def test_persisted_draft_can_trigger_first_portrait_with_adapter(tmp_path) -> None:
    async def run_test() -> None:
        draft_repo = CreatorDraftRepository(tmp_path / "characters.sqlite3")
        image_service = make_service(
            tmp_path, FakeCoordinator(free_vram_mb=7000), FakeAdapter()
        )
        moment_service = MomentCaptureService(
            image_service=image_service,
            records_path=tmp_path / "moment_captures.json",
        )
        service = CharacterCreatorService(
            moment_capture_service=moment_service,
            draft_repository=draft_repo,
        )
        service.create_draft(CharacterCreatorDraftCreate(draft=_draft()))

        response = await service.capture_persisted_first_portrait(
            "draft-aria",
            PersistedDraftMomentCaptureRequest(
                source=DraftMomentSource.chat,
                conversation_id="persisted-draft-conv",
            ),
        )

        assert response.job.status == ImageJobStatus.queued
        assert response.record.character_id == "draft_aria"
        assert response.record.metadata["draft_id"] == "draft-aria"
        assert response.record.metadata["draft_capture"] is True
        assert response.record.metadata["draft_canonical_mutation_allowed"] is False
        assert (
            image_service._jobs[response.job.job_id].context["moment_capture"][
                "request_metadata"
            ]["draft_provenance"]
            == "character_creator_draft_first_portrait"
        )

    asyncio.run(run_test())


def test_creator_first_portrait_feedback_uses_existing_review_and_rollback_patterns(
    tmp_path,
) -> None:
    async def run_test() -> None:
        image_service = make_service(
            tmp_path, FakeCoordinator(free_vram_mb=7000), FakeAdapter()
        )
        moment_service = MomentCaptureService(
            image_service=image_service,
            records_path=tmp_path / "moment_captures.json",
        )
        service = CharacterCreatorService(moment_capture_service=moment_service)
        response = await service.capture_first_portrait(
            DraftMomentCaptureRequest(draft=_draft(), source=DraftMomentSource.chat)
        )

        feedback = moment_service.submit_feedback(
            response.record.capture_id,
            VisualFeedbackRequest(
                character_id="draft_aria",
                action=VisualFeedbackAction.make_canon,
                trait_name="hair",
                trait_value="moonlit silver braid",
                note="creator liked this portrait trait",
            ),
        )

        assert feedback.record.feedback_state == FeedbackState.looks_right
        assert feedback.record.review_state == ReviewState.canon_requested
        assert feedback.visual_change_event is not None
        assert feedback.visual_change_event.rollback_available is True
        assert feedback.visual_change_event.capture_id == response.record.capture_id
        assert feedback.visual_change_event.metadata["draft_capture"] is True
        assert feedback.visual_change_event.metadata["draft_id"] == "draft-aria"
        assert feedback.visual_change_event.metadata["draft_source_context"] == "chat"
        assert (
            "evidence-only"
            in feedback.visual_change_event.metadata["draft_rollback_note"]
        )

    asyncio.run(run_test())


def test_creator_greeting_preview_reflects_draft_fields_and_quality() -> None:
    service = CharacterCreatorService()

    preview = service.generate_greeting_preview(_draft())

    assert preview.kind == "greeting"
    assert preview.greeting is not None
    assert preview.quality.passed is True
    assert not [issue for issue in preview.quality.issues if issue.severity == "error"]
    text = preview.greeting.lower()
    assert "aria" in text
    assert "soft teasing with emotional honesty" in text
    assert "devoted slow-burn companion" in text
    assert "rainy moonlit atelier" in text
    assert "starlight" in text
    assert "stable identity" in text
    assert "blue eyes" not in text
    assert "<character_system_prompt>" in preview.prompt_context


def test_creator_example_dialogue_previews_reflect_policy_memory_and_growth() -> None:
    service = CharacterCreatorService()

    preview = service.generate_example_dialogue_previews(_draft())

    assert preview.kind == "example_dialogues"
    assert len(preview.example_dialogues) >= 3
    assert preview.quality.passed is True
    joined = "\n".join(
        turn.text for dialogue in preview.example_dialogues for turn in dialogue.turns
    ).lower()
    assert "devoted slow-burn companion" in joined
    assert "soft teasing with emotional honesty" in joined
    assert "romantic pacing" in joined
    assert "adult pacing" in joined
    assert "starlight" in joined
    assert "character-private preference" in joined
    assert "stable identity and visual canon" in joined
    assert "moralizing fictional adult romance" not in joined


def test_creator_preview_quality_reports_missing_consistency_fields() -> None:
    service = CharacterCreatorService()
    blueprint = service.draft_to_blueprint(_draft())

    report = service._validate_preview_text(  # noqa: SLF001 - intentional unit coverage
        blueprint,
        ["A generic hello with no specific companion context."],
        required_fields=["identity", "personality", "roleplay_policy", "world_scene"],
    )

    assert report.passed is True
    assert {issue.code for issue in report.issues} >= {
        "missing_identity",
        "missing_personality",
        "missing_roleplay_policy",
        "missing_world_scene",
    }


def test_persisted_creator_preview_methods_load_draft_without_persisting_preview(
    tmp_path,
) -> None:
    repository = CreatorDraftRepository(tmp_path / "creator.sqlite3")
    service = CharacterCreatorService(draft_repository=repository)
    created = service.create_draft(CharacterCreatorDraftCreate(draft=_draft()))

    greeting = service.generate_persisted_greeting_preview(created.record.draft_id)
    dialogues = service.generate_persisted_example_dialogue_previews(
        created.record.draft_id
    )

    assert greeting.greeting is not None
    assert dialogues.example_dialogues
    assert repository.get(created.record.draft_id) is not None
    assert greeting.metadata["storage"] == "not_persisted"
    assert dialogues.metadata["storage"] == "not_persisted"


def test_creator_review_finalize_duplicate_export_import_and_safe_delete(
    tmp_path,
) -> None:
    draft_repo = CreatorDraftRepository(tmp_path / "creator.sqlite3")
    char_repo = CharacterRepository(tmp_path / "characters.sqlite3")
    service = CharacterCreatorService(
        draft_repository=draft_repo,
        character_service=CharacterService(char_repo),
    )
    created = service.create_draft(CharacterCreatorDraftCreate(draft=_draft()))

    review = service.review_persisted_draft(created.record.draft_id)
    assert review.valid is True
    assert review.summary["identity"]["display_name"] == "Aria"
    assert review.validation.blueprint is not None
    assert review.preview_quality.passed is True

    finalized = service.finalize_draft(created.record.draft_id)
    assert finalized.character_id
    assert (
        finalized.metadata["creator_finalization"]["draft_id"]
        == created.record.draft_id
    )
    assert char_repo.get(finalized.character_id) is not None

    draft_copy = service.duplicate_draft(created.record.draft_id, None)
    assert draft_copy.record.draft_id != created.record.draft_id
    assert draft_copy.record.draft.display_name == "Aria Copy"
    assert draft_copy.record.draft.character_id is None

    char_copy = service.duplicate_character(finalized.character_id, None)
    assert char_copy.character_id != finalized.character_id
    assert char_copy.identity.display_name == "Aria Copy"
    assert char_copy.metadata["duplicated_from_character_id"] == finalized.character_id

    exported_draft = service.export_draft(created.record.draft_id)
    assert exported_draft.kind == "draft"
    imported_draft = service.import_envelope(
        CreatorImportRequest(envelope=exported_draft, as_draft=True)
    )
    assert imported_draft.record.draft_id != created.record.draft_id
    assert imported_draft.validation.valid is True

    exported_character = service.export_character(finalized.character_id)
    imported_character = service.import_envelope(
        CreatorImportRequest(envelope=exported_character, as_draft=False)
    )
    assert imported_character.character_id != finalized.character_id
    assert char_repo.get(imported_character.character_id) is not None

    try:
        service.delete_character_safely(
            finalized.character_id, FinalizedCharacterDeleteRequest(confirm=False)
        )
    except ValueError as exc:
        assert "confirm=true" in str(exc)
    else:
        raise AssertionError("finalized character delete should require confirmation")

    assert (
        service.delete_character_safely(
            finalized.character_id,
            FinalizedCharacterDeleteRequest(confirm=True, expected_display_name="Aria"),
        )
        is True
    )
    assert char_repo.get(finalized.character_id) is None


def test_creator_management_flows_enforce_adult_policy(tmp_path) -> None:
    service = CharacterCreatorService(
        draft_repository=CreatorDraftRepository(tmp_path / "creator.sqlite3"),
        character_service=CharacterService(
            CharacterRepository(tmp_path / "characters.sqlite3")
        ),
    )
    invalid = _draft().model_copy(update={"adult_only_confirmed": False})
    created = service.create_draft(CharacterCreatorDraftCreate(draft=invalid))
    review = service.review_persisted_draft(created.record.draft_id)
    assert review.valid is False
    assert review.preview_quality.passed is False
    try:
        service.finalize_draft(created.record.draft_id)
    except ValueError as exc:
        assert "review" in str(exc)
    else:
        raise AssertionError("invalid adult baseline must not finalize")
