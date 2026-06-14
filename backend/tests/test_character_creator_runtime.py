"""M6-P00A creator runtime wiring coverage."""

from __future__ import annotations

import asyncio

from pydantic import ValidationError

from app.models.image import ImageJobStatus, ImageQualityPreset
from app.schemas.moment_capture import (
    FeedbackState,
    ReviewState,
    SceneState,
    VisualFeedbackAction,
    VisualFeedbackRequest,
)
from app.schemas.relationship_state import RelationshipPhase
from app.schemas.visual_identity import VisualIdentityProfile
from app.services.character_creator_service import (
    CharacterCreatorDraft,
    CharacterCreatorService,
    DraftMomentCaptureRequest,
    DraftMomentSource,
)
from app.services.moment_capture_service import MomentCaptureService

from test_image_generation_service import FakeAdapter, FakeCoordinator, make_service


def _draft() -> CharacterCreatorDraft:
    return CharacterCreatorDraft(
        draft_id="draft-aria",
        character_id="draft_aria",
        display_name="Aria",
        pronouns="she/her",
        relationship_dynamic="devoted slow-burn companion",
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
    assert blueprint.relationship.phase == RelationshipPhase.newly_met
    assert (
        blueprint.relationship.relationship_dynamic == "devoted slow-burn companion"
    )
    assert blueprint.personality.core_traits == ["warm", "playful", "protective"]
    assert blueprint.communication.style_notes == "soft teasing with emotional honesty"
    assert blueprint.visual_identity.identity_anchors == [
        "amber eyes",
        "warm brown skin",
        "same adult face",
    ]
    assert (
        blueprint.visual_identity.adult_only_policy.adult_age_range == "mid_20s_adult"
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


def test_creator_draft_can_queue_chat_and_vn_first_portrait_captures(tmp_path) -> None:
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
        assert vn_response.record.metadata["creator_runtime_source"] == "visual_novel"
        assert chat_response.record.metadata["creator_draft"] is True
        assert chat_response.record.metadata["draft_id"] == "draft-aria"
        assert chat_response.record.metadata["source_context"] == "chat"
        assert (
            chat_response.record.metadata["capture_intent"]
            == "first portrait from creator draft"
        )
        assert "evidence-only" in chat_response.record.metadata["rollback_note"]
        assert chat_response.record.metadata["canonical_mutation_allowed"] is False
        assert (
            chat_response.record.metadata["provenance"]
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
            ]["creator_draft"]
            is True
        )
        assert (
            image_service._jobs[chat_response.job.job_id].context["moment_capture"][
                "scene_state"
            ]["metadata"]["source_context"]
            == "chat"
        )
        assert (
            "first portrait validation"
            in vn_response.record.scene_state.continuity_notes
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
        assert feedback.visual_change_event.metadata["creator_draft"] is True
        assert feedback.visual_change_event.metadata["draft_id"] == "draft-aria"
        assert feedback.visual_change_event.metadata["source_context"] == "chat"
        assert "evidence-only" in feedback.visual_change_event.metadata["rollback_note"]

    asyncio.run(run_test())
