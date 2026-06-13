from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.image import ImageHistoryItem, ImageQualityPreset
from app.schemas.moment_capture import (
    FeedbackState,
    MomentCaptureRecord,
    MomentCaptureRequest,
    ReviewState,
    SceneState,
    VisualChangeCanonStatus,
    VisualChangeEvent,
    VisualFeedbackAction,
)
from app.schemas.relationship_state import RelationshipPhase, RelationshipState
from app.schemas.visual_identity import VisualIdentityProfile


def _scene() -> SceneState:
    return SceneState(
        location="moonlit balcony",
        mood="tender",
        character_appearance=[" amber eyes ", "amber eyes", "black-violet hair"],
        key_objects=["tea cup"],
        wrong_appearance=["blue eyes"],
    )


def _request() -> MomentCaptureRequest:
    return MomentCaptureRequest.from_chat_turn(
        character_id="aria",
        conversation_id="conv-1",
        session_id="sess-1",
        source_message_id="msg-9",
        source_turn_index=9,
        scene_state=_scene(),
        visual_identity=VisualIdentityProfile(identity_anchors=["amber eyes"]),
        relationship_state=RelationshipState(
            current_relationship_phase=RelationshipPhase.close
        ),
    )


def _record(**updates: object) -> MomentCaptureRecord:
    req = _request()
    payload = {
        "capture_id": "cap-1",
        "character_id": req.character_id,
        "conversation_id": req.conversation_id,
        "session_id": req.session_id,
        "source_message_id": req.source_message_id,
        "source_turn_index": req.source_turn_index,
        "scene_state": req.scene_state,
        "relationship_phase_snapshot": req.relationship_phase_snapshot,
        "visual_identity_version": req.visual_identity_version,
        "visual_identity_updated_at": req.visual_identity_updated_at,
        "prompt_hash": req.prompt_hash,
        "image_job_id": "job-1",
        "output_paths": ["/tmp/aria.png"],
    }
    payload.update(updates)
    return MomentCaptureRecord(**payload)


def test_request_from_chat_turn_contains_required_traceability() -> None:
    req = _request()

    assert req.schema_version == "moment_capture.v1"
    assert req.character_id == "aria"
    assert req.conversation_id == "conv-1"
    assert req.session_id == "sess-1"
    assert req.source_message_id == "msg-9"
    assert req.source_turn_index == 9
    assert req.scene_state.character_appearance == ["amber eyes", "black-violet hair"]
    assert req.relationship_phase_snapshot == RelationshipPhase.close
    assert req.visual_identity_version == "visual_identity_profile.v1"
    assert len(req.prompt_hash) == 16


def test_required_fields_and_type_enforcement() -> None:
    with pytest.raises(ValidationError):
        MomentCaptureRequest.model_validate(
            {
                "character_id": "aria",
                "conversation_id": "conv-1",
                "session_id": "sess-1",
                "source_message_id": "msg-1",
                "source_turn_index": "not-an-int",
                "scene_state": _scene().model_dump(),
                "relationship_phase_snapshot": "close",
                "visual_identity_snapshot": VisualIdentityProfile().model_dump(),
                "visual_identity_version": "visual_identity_profile.v1",
                "visual_identity_updated_at": "2026-06-13T00:00:00+00:00",
                "prompt_hash": "12345678",
            }
        )

    with pytest.raises(ValidationError):
        _record(output_paths=[])


def test_safe_defaults_on_optional_fields() -> None:
    record = _record()

    assert record.feedback_state == FeedbackState.pending
    assert record.review_state == ReviewState.unreviewed
    assert record.feedback_actions == []
    assert record.visual_memory_artifacts == []
    assert record.rollback_id is None
    assert record.legacy_image_history == {}


def test_normalizes_legacy_image_history_without_data_loss() -> None:
    created = datetime(2026, 6, 13, 12, tzinfo=timezone.utc)
    history = ImageHistoryItem(
        job_id="job-legacy",
        conversation_id="conv-legacy",
        source="chat",
        source_message_id="msg-legacy",
        prompt="full prompt text kept only in legacy payload",
        prompt_summary="Aria on a balcony",
        negative_prompt="blue eyes",
        requested_preset=ImageQualityPreset.preview_8gb,
        active_preset=ImageQualityPreset.preview_8gb,
        created_at=created,
        completed_at=created,
        output_paths=["/images/aria.png"],
        thumbnail_paths=["/images/thumb.png"],
        metadata={
            "character_id": "aria",
            "source_turn_index": 4,
            "prompt_hash": "abc12345",
        },
    )

    record = MomentCaptureRecord.normalize_image_history(history)

    assert record.capture_id == "legacy-job-legacy"
    assert record.character_id == "aria"
    assert record.conversation_id == "conv-legacy"
    assert record.source_message_id == "msg-legacy"
    assert record.source_turn_index == 4
    assert record.image_job_id == "job-legacy"
    assert record.output_paths == ["/images/aria.png"]
    assert record.prompt_hash == "abc12345"
    assert (
        record.legacy_image_history["prompt"]
        == "full prompt text kept only in legacy payload"
    )
    assert record.legacy_image_history["thumbnail_paths"] == ["/images/thumb.png"]


def test_review_state_transitions_are_validated() -> None:
    accepted = _record().transition_review(ReviewState.accepted)
    assert accepted.review_state == ReviewState.accepted
    canon_requested = accepted.transition_review(ReviewState.canon_requested)
    assert canon_requested.review_transition_from == ReviewState.accepted

    with pytest.raises(ValidationError):
        _record(
            review_transition_from=ReviewState.deleted,
            review_state=ReviewState.accepted,
        )


def test_json_roundtrip_for_record_and_visual_change_event() -> None:
    record = _record(feedback_actions=[VisualFeedbackAction.looks_right])
    decoded = MomentCaptureRecord.model_validate_json(record.model_dump_json())
    assert decoded == record

    event = VisualChangeEvent(
        event_id="evt-1",
        character_id="aria",
        capture_id=record.capture_id,
        changed_trait="hair",
        previous_value="black-violet hair",
        new_value="short silver hair",
        reason="User selected make canon after reviewing capture.",
        feedback_action=VisualFeedbackAction.make_canon,
        canon_status=VisualChangeCanonStatus.canonized,
        rollback_id="rollback-1",
    )
    event_roundtrip = VisualChangeEvent.model_validate_json(event.model_dump_json())
    assert event_roundtrip == event


def test_visual_change_event_requires_rollback_id_when_rolled_back() -> None:
    with pytest.raises(ValidationError):
        VisualChangeEvent(
            event_id="evt-2",
            character_id="aria",
            changed_trait="outfit",
            previous_value="red dress",
            new_value="black coat",
            reason="User rolled back accidental canonization.",
            canon_status=VisualChangeCanonStatus.rolled_back,
        )
