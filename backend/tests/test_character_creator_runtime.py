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
    CharacterCreatorService,
    DraftMomentCaptureRequest,
    DraftMomentSource,
    PersistedDraftMomentCaptureRequest,
)
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
        communication_style="soft teasing with emotional honesty",
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
    assert (
        blueprint.relationship.relationship_dynamic == "devoted slow-burn companion"
    )
    assert blueprint.relationship.relationship_pacing == RelationshipPacing.slow_burn
    assert blueprint.relationship.romantic_pacing == RelationshipPacing.slow_burn
    assert blueprint.relationship.nsfw_pacing == RelationshipPacing.user_led
    assert blueprint.relationship.default_intimacy_level == DefaultIntimacyLevel.flirtatious
    assert blueprint.relationship.user_desired_experience == "tender magical romance"
    assert blueprint.personality.core_traits == ["warm", "playful", "protective"]
    assert blueprint.communication.style_notes == "soft teasing with emotional honesty"
    assert blueprint.visual_identity.identity_anchors == [
        "amber eyes",
        "warm brown skin",
        "same adult face",
    ]
    assert (
        blueprint.visual_identity.adult_only_policy.adult_age_range == "late_20s_adult"
    )
    assert blueprint.metadata["creator_draft"]["source"] == "m6_p00a_runtime_draft"


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


def test_creator_draft_update_validates_premise_and_relationship_frame(tmp_path) -> None:
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


def test_drafts_persist_separately_from_finalized_character_blueprints(tmp_path) -> None:
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
        assert chat_response.record.metadata["draft_canonical_mutation_allowed"] is False
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
        assert "evidence-only" in feedback.visual_change_event.metadata["draft_rollback_note"]

    asyncio.run(run_test())
