from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.image import ImageHistoryItem, ImageQualityPreset
from app.schemas.moment_capture import (
    MomentCaptureRecord,
    MomentCaptureRequest,
    MomentReviewState,
    SceneState,
    VisualCanonStatus,
    VisualChangeEvent,
    VisualFeedbackAction,
    VisualFeedbackActionType,
    VisualFeedbackState,
)
from app.schemas.relationship_state import RelationshipPhase


def _scene() -> SceneState:
    return SceneState(
        location="cafe",
        mood="tender",
        character_appearance=[" amber eyes ", "amber eyes", "blue cardigan"],
        key_objects=["mug"],
        wrong_appearance=["green eyes"],
    )


def _record(**overrides: object) -> MomentCaptureRecord:
    data = {
        "character_id": "aria",
        "conversation_id": "conv-1",
        "source_message_id": "msg-2",
        "source_turn_index": 2,
        "scene_state": _scene(),
        "relationship_phase_snapshot": RelationshipPhase.friends,
        "visual_identity_version": "visual_identity_profile.v1",
        "prompt_hash": "a" * 64,
        "image_job_id": "job-1",
        "output_paths": ["/tmp/aria.png"],
    }
    data.update(overrides)
    return MomentCaptureRecord(**data)


def test_request_requires_traceability_fields_and_normalizes_scene_defaults() -> None:
    request = MomentCaptureRequest(
        character_id="aria",
        conversation_id="conv-1",
        source_message_id="msg-1",
        source_turn_index=1,
        scene_state=_scene(),
        relationship_phase_snapshot=RelationshipPhase.close,
        visual_identity_updated_at=datetime.now(UTC),
    )

    assert request.schema_version == "moment_capture.v1"
    assert request.scene_state.schema_version == "scene_state.v1"
    assert request.scene_state.character_appearance == ["amber eyes", "blue cardigan"]
    assert request.quality_preset == ImageQualityPreset.preview_8gb
    assert request.relevant_visual_memories == []


def test_request_rejects_missing_source_turn_index() -> None:
    with pytest.raises(ValidationError):
        MomentCaptureRequest(
            character_id="aria",
            conversation_id="conv-1",
            source_message_id="msg-1",
            scene_state=_scene(),
            relationship_phase_snapshot=RelationshipPhase.close,
        )


def test_record_json_roundtrip_preserves_required_metadata() -> None:
    record = _record(
        feedback_state=VisualFeedbackState.liked,
        review_state=MomentReviewState.approved,
    )

    payload = record.model_dump_json()
    restored = MomentCaptureRecord.model_validate_json(payload)

    assert restored.character_id == "aria"
    assert restored.prompt_hash == "a" * 64
    assert restored.output_paths == ["/tmp/aria.png"]
    assert restored.feedback_state == VisualFeedbackState.liked
    assert restored.review_state == MomentReviewState.approved


def test_record_rejects_deleted_without_rollback_tombstone() -> None:
    with pytest.raises(ValidationError, match="rollback_id"):
        _record(review_state=MomentReviewState.deleted)


def test_feedback_action_validates_review_state_transition() -> None:
    action = VisualFeedbackAction(
        action=VisualFeedbackActionType.request_correction,
        from_state=VisualFeedbackState.disliked,
        to_state=VisualFeedbackState.correction_requested,
    )
    assert action.to_state == VisualFeedbackState.correction_requested

    with pytest.raises(ValidationError, match="cannot transition"):
        VisualFeedbackAction(
            action=VisualFeedbackActionType.like,
            from_state=VisualFeedbackState.none,
            to_state=VisualFeedbackState.canonized,
        )


def test_visual_change_event_represents_reversible_rollback() -> None:
    event = VisualChangeEvent(
        character_id="aria",
        source_record_id="record-1",
        changed_trait="hair",
        previous_value="long brown hair",
        new_value="short silver hair",
        reason="user requested an alternate look",
        user_reaction=VisualFeedbackState.correction_requested,
        canon_status=VisualCanonStatus.proposed,
    )

    assert event.rollback_available is True
    assert event.previous_value == "long brown hair"

    with pytest.raises(ValidationError, match="rollback"):
        VisualChangeEvent(
            character_id="aria",
            source_record_id="record-1",
            changed_trait="hair",
            reason="undo disliked change",
            canon_status=VisualCanonStatus.rolled_back,
        )


def test_legacy_image_history_normalizes_without_losing_original_record() -> None:
    created = datetime(2026, 1, 1, tzinfo=UTC)
    history = ImageHistoryItem(
        job_id="job-legacy",
        conversation_id="conv-legacy",
        source="chat",
        source_message_id="msg-legacy",
        prompt="portrait of Aria in a cafe",
        prompt_summary="Aria cafe portrait",
        negative_prompt="wrong face",
        requested_preset=ImageQualityPreset.preview_8gb,
        active_preset=ImageQualityPreset.preview_8gb,
        created_at=created,
        completed_at=created,
        output_paths=["/images/aria.png"],
        thumbnail_paths=["/images/aria-thumb.png"],
        metadata={
            "character_id": "aria",
            "source_turn_index": 7,
            "scene_state": {"location": "cafe", "key_objects": ["mug"]},
            "relationship_phase_snapshot": "friends",
        },
    )

    record = MomentCaptureRecord.normalize_legacy_image_history(history)

    assert record.record_id == "legacy_job-legacy"
    assert record.character_id == "aria"
    assert record.source_turn_index == 7
    assert record.scene_state.location == "cafe"
    assert record.output_paths == ["/images/aria.png"]
    assert record.legacy_image_record is not None
    assert record.legacy_image_record["prompt"] == "portrait of Aria in a cafe"
    assert record.metadata["normalized_from"] == "ImageHistoryItem"
    assert len(record.prompt_hash) == 64
