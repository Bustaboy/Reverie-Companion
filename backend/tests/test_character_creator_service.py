"""M6 creator draft runtime wiring tests."""

from __future__ import annotations

import asyncio

from app.models.image import ImageJobStatus
from app.schemas.character_blueprint import AdultAgeRange
from app.schemas.moment_capture import (
    SceneState,
    VisualFeedbackAction,
    VisualFeedbackRequest,
)
from app.services.character_creator_service import (
    CharacterCreatorDraft,
    CharacterCreatorService,
    CreatorMomentCaptureRequest,
)
from app.services.moment_capture_service import MomentCaptureService

from test_image_generation_service import FakeAdapter, FakeCoordinator, make_service
from test_moment_capture_service import FakeCharacterService


def _draft() -> CharacterCreatorDraft:
    return CharacterCreatorDraft(
        draft_id="draft-aria",
        character_id="draft_aria",
        display_name="Aria",
        pronouns="she/her",
        adult_age_range=AdultAgeRange.late_20s_adult,
        species_or_type="moonlit human muse",
        relationship_dynamic="playful slow-burn companion",
        core_traits=["playful", "tender", "independent"],
        communication_style="soft teasing with direct emotional honesty",
        identity_anchors=["amber eyes", "warm brown skin", "same elegant face"],
        current_appearance="long black-violet hair and a silver moon pendant",
        scene_mutable_traits=["outfit", "expression", "lighting"],
        tags=["slow burn", "muse"],
    )


def _service(tmp_path) -> tuple[CharacterCreatorService, MomentCaptureService, object]:
    image_service = make_service(
        tmp_path, FakeCoordinator(free_vram_mb=7000), FakeAdapter()
    )
    moment_service = MomentCaptureService(
        character_service=FakeCharacterService(
            None
        ),  # draft path should not load persisted character
        image_service=image_service,
        records_path=tmp_path / "moment_captures.json",
    )
    return (
        CharacterCreatorService(moment_capture_service=moment_service),
        moment_service,
        image_service,
    )


def test_draft_to_blueprint_mapping_produces_valid_character_blueprint(
    tmp_path,
) -> None:
    service, _, _ = _service(tmp_path)

    response = service.validate_draft(_draft())

    assert response.valid is True
    assert response.blueprint is not None
    assert response.blueprint.character_id == "draft_aria"
    assert response.blueprint.identity.display_name == "Aria"
    assert response.blueprint.identity.adult_only_confirmed is True
    assert (
        response.blueprint.relationship.relationship_dynamic
        == "playful slow-burn companion"
    )
    assert response.blueprint.personality.core_traits == [
        "playful",
        "tender",
        "independent",
    ]
    assert (
        response.blueprint.visual_identity.adult_only_policy.adult_age_range
        == "late_20s_adult"
    )
    assert "amber eyes" in response.blueprint.visual_identity.identity_anchors
    assert response.blueprint.metadata["creator_draft"] is True


def test_draft_validation_reports_adult_baseline_error(tmp_path) -> None:
    service, _, _ = _service(tmp_path)
    draft = _draft().model_copy(update={"adult_only_confirmed": False})

    response = service.validate_draft(draft)

    assert response.valid is False
    assert response.blueprint is None
    assert "clearly adult" in response.errors[0]


def test_creator_draft_triggers_non_blocking_chat_moment_capture(tmp_path) -> None:
    async def run_test() -> None:
        service, moment_service, image_service = _service(tmp_path)

        response = await service.capture_first_portrait(
            CreatorMomentCaptureRequest(
                draft=_draft(),
                source_context="chat",
                conversation_id="conv-chat",
                session_id="session-chat",
                source_message_id="msg-chat-1",
                source_turn_index=1,
            )
        )

        job = image_service._jobs[response.job.job_id]
        assert response.job.status == ImageJobStatus.queued
        assert response.record.character_id == "draft_aria"
        assert response.record.conversation_id == "conv-chat"
        assert response.record.metadata["creator_draft"] is True
        assert response.record.metadata["source_context"] == "chat"
        assert response.record.metadata["non_blocking"] is True
        assert job.source == "moment_capture"
        assert (
            job.context["moment_capture"]["moment_capture_id"]
            == response.record.capture_id
        )
        assert job.context["moment_capture"]["source_context"] == "chat"
        assert moment_service.get_record(response.record.capture_id) == response.record

    asyncio.run(run_test())


def test_creator_draft_triggers_visual_novel_moment_capture_with_scene(
    tmp_path,
) -> None:
    async def run_test() -> None:
        service, _, image_service = _service(tmp_path)

        response = await service.capture_first_portrait(
            CreatorMomentCaptureRequest(
                draft=_draft(),
                source_context="visual_novel",
                conversation_id="vn-conv",
                session_id="vn-session",
                source_message_id="vn-scene-2",
                source_turn_index=2,
                scene_state=SceneState(
                    location="moonlit VN stage",
                    mood="inviting",
                    pose="half-turn toward the camera",
                    background_details=["soft blue light"],
                ),
            )
        )

        job = image_service._jobs[response.job.job_id]
        assert response.record.metadata["source_context"] == "visual_novel"
        assert response.record.scene_state.location == "moonlit VN stage"
        assert job.context["moment_capture"]["source_context"] == "visual_novel"
        assert (
            job.context["moment_capture"]["scene_state"]["location"]
            == "moonlit VN stage"
        )

    asyncio.run(run_test())


def test_draft_feedback_creates_reviewable_event_without_canon_mutation(
    tmp_path,
) -> None:
    async def run_test() -> None:
        service, moment_service, _ = _service(tmp_path)
        response = await service.capture_first_portrait(
            CreatorMomentCaptureRequest(draft=_draft(), source_context="chat")
        )

        feedback = moment_service.submit_feedback(
            response.record.capture_id,
            VisualFeedbackRequest(
                character_id="draft_aria",
                action=VisualFeedbackAction.wrong_appearance,
                changed_trait="eye color",
                proposed_value="blue eyes",
                note="The portrait lost her amber eyes.",
            ),
        )

        assert feedback.visual_change_event is not None
        assert feedback.visual_change_event.character_id == "draft_aria"
        assert feedback.visual_change_event.capture_id == response.record.capture_id
        assert feedback.visual_change_event.rollback_id is not None
        assert feedback.visual_change_event.canon_status.value == "proposed"
        assert feedback.record.review_state == response.record.review_state

    asyncio.run(run_test())
