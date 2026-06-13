"""Moment Capture orchestration coverage."""

from __future__ import annotations

import asyncio

import pytest

from app.models.image import ImageJobStatus, ImageQualityPreset
from app.schemas.character_blueprint import CharacterBlueprint, CharacterIdentity
from app.schemas.moment_capture import (
    FeedbackState,
    MomentCaptureRequest,
    ReviewState,
    SceneState,
    VisualChangeCanonStatus,
    VisualFeedbackAction,
)
from app.schemas.relationship_state import RelationshipPhase
from app.schemas.visual_identity import VisualIdentityProfile
from app.services.character_service import CharacterNotFoundError
from app.services.moment_capture_service import MomentCaptureService

from test_image_generation_service import FakeAdapter, FakeCoordinator, make_service


class FakeCharacterService:
    def __init__(self, character: CharacterBlueprint | None) -> None:
        self.character = character

    def load_by_id(self, character_id: str) -> CharacterBlueprint:
        if self.character is None or self.character.character_id != character_id:
            raise CharacterNotFoundError(character_id)
        return self.character

    def get_visual_identity(self, character_id: str) -> VisualIdentityProfile:
        return self.load_by_id(character_id).visual_identity

    def update_visual_identity(
        self, character_id: str, patch: dict[str, object]
    ) -> VisualIdentityProfile:
        character = self.load_by_id(character_id)
        visual = character.visual_identity
        if "evolving_trait" in patch and isinstance(patch["evolving_trait"], dict):
            trait = patch["evolving_trait"]
            visual = visual.with_evolving_trait(
                str(trait["name"]),
                str(trait["value"]),
                provenance=str(trait["provenance"]),
            )
        if "rejected_traits" in patch:
            visual = visual.model_copy(
                update={"rejected_traits": patch["rejected_traits"]}
            )
        self.character = character.model_copy(update={"visual_identity": visual})
        return visual


def _character() -> CharacterBlueprint:
    return CharacterBlueprint(
        character_id="aria",
        identity=CharacterIdentity(display_name="Aria", pronouns="she/her"),
        visual_identity=VisualIdentityProfile(
            identity_anchors=["amber eyes", "warm brown skin", "same face"],
            current_appearance="long black-violet hair and a moon pendant",
            rejected_traits=["blue eyes"],
        ),
    )


def _request() -> MomentCaptureRequest:
    visual_identity = _character().visual_identity
    return MomentCaptureRequest(
        character_id="aria",
        conversation_id="conv-1",
        session_id="session-1",
        source_message_id="msg-7",
        source_turn_index=7,
        scene_state=SceneState(
            location="rainy balcony",
            emotional_tone="tender and relieved",
            pose="looking back over her shoulder",
            wrong_appearance=["blue eyes"],
        ),
        relationship_phase_snapshot=RelationshipPhase.newly_met,
        visual_identity_snapshot=visual_identity,
        visual_identity_version=visual_identity.schema_version,
        visual_identity_updated_at=visual_identity.updated_at,
        prompt_hash="requesthash123",
        quality_preset=ImageQualityPreset.preview_8gb,
        metadata={"capture_intent": "capture this quiet reunion"},
    )


def test_capture_queues_image_job_and_persists_record_with_metadata(tmp_path) -> None:
    async def run_test() -> None:
        coordinator = FakeCoordinator(free_vram_mb=7000)
        image_service = make_service(tmp_path, coordinator, FakeAdapter())
        service = MomentCaptureService(
            character_service=FakeCharacterService(_character()),  # type: ignore[arg-type]
            image_service=image_service,
            records_path=tmp_path / "moment_captures.json",
        )

        response = await service.capture(_request())

        job = image_service._jobs[response.job.job_id]
        assert response.job.status == ImageJobStatus.queued
        assert response.record.image_job_id == response.job.job_id
        assert response.record.character_id == "aria"
        assert (
            response.record.prompt_hash
            == response.prompt_bundle.metadata["prompt_hash"]
        )
        assert response.record.output_paths == [
            f"queued://image-job/{response.job.job_id}"
        ]
        assert job.source == "moment_capture"
        assert job.context["moment_capture"]["character_id"] == "aria"
        assert (
            job.context["moment_capture"]["prompt_hash"] == response.record.prompt_hash
        )
        assert (
            job.context["moment_capture"]["scene_state"]["location"] == "rainy balcony"
        )
        assert service.get_record(response.record.capture_id) == response.record
        assert (tmp_path / "moment_captures.json").exists()

    asyncio.run(run_test())


def test_missing_specific_character_returns_structured_error_boundary(tmp_path) -> None:
    async def run_test() -> None:
        image_service = make_service(tmp_path, FakeCoordinator(), FakeAdapter())
        service = MomentCaptureService(
            character_service=FakeCharacterService(None),  # type: ignore[arg-type]
            image_service=image_service,
            records_path=tmp_path / "moment_captures.json",
        )

        with pytest.raises(CharacterNotFoundError) as exc:
            await service.capture(_request())

        assert exc.value.character_id == "aria"
        assert image_service._jobs == {}

    asyncio.run(run_test())


def test_capture_submit_does_not_wait_for_tts_idle(tmp_path) -> None:
    async def run_test() -> None:
        coordinator = FakeCoordinator(free_vram_mb=7000)
        coordinator.tts_active = True
        image_service = make_service(tmp_path, coordinator, FakeAdapter())
        service = MomentCaptureService(
            character_service=FakeCharacterService(_character()),  # type: ignore[arg-type]
            image_service=image_service,
            records_path=tmp_path / "moment_captures.json",
        )

        response = await service.capture(_request())

        assert response.job.status == ImageJobStatus.queued
        assert coordinator.wait_calls == 0
        assert (
            image_service.get_job(response.job.job_id).status == ImageJobStatus.queued
        )

    asyncio.run(run_test())


def test_api_boundary_returns_structured_missing_character_error() -> None:
    async def run_test() -> None:
        from fastapi import HTTPException

        from app.api.routes.moment_capture import create_moment_capture

        class MissingCharacterMomentCaptureService:
            async def capture(self, request: MomentCaptureRequest):
                raise CharacterNotFoundError(request.character_id)

        with pytest.raises(HTTPException) as exc:
            await create_moment_capture(
                _request(),
                MissingCharacterMomentCaptureService(),  # type: ignore[arg-type]
            )

        assert exc.value.status_code == 404
        assert exc.value.detail["error"]["code"] == "character_not_found"
        assert exc.value.detail["error"]["details"] == {"character_id": "aria"}
        assert exc.value.detail["error"]["retryable"] is False

    asyncio.run(run_test())


def test_feedback_actions_validate_and_persist_summary(tmp_path) -> None:
    service = MomentCaptureService(
        character_service=FakeCharacterService(_character()),  # type: ignore[arg-type]
        image_service=make_service(tmp_path, FakeCoordinator(), FakeAdapter()),
        records_path=tmp_path / "moment_captures.json",
    )
    record = MomentCaptureRecordForTest(_request(), "job-feedback")
    service._records[record.capture_id] = record

    from app.services.moment_capture_service import VisualFeedbackRequest

    for action in (
        VisualFeedbackAction.looks_right,
        VisualFeedbackAction.wrong_appearance,
        VisualFeedbackAction.make_canon,
        VisualFeedbackAction.use_outfit_again,
        VisualFeedbackAction.just_this_scene,
        VisualFeedbackAction.reject_style_trait,
    ):
        response = service.submit_feedback(
            record.capture_id,
            VisualFeedbackRequest(
                character_id="aria",
                action=action,
                trait_name="hair",
                trait_value="silver braid",
                note=f"user chose {action.value}",
            ),
        )
        assert (
            response.record.metadata["feedback_summary"]["latest_action"]
            == action.value
        )

    assert service.get_record(record.capture_id).metadata["feedback_summary"]


def test_make_canon_is_pending_until_approved_then_rolls_back(tmp_path) -> None:
    character = _character().model_copy(
        update={
            "visual_identity": _character().visual_identity.with_evolving_trait(
                "hair", "long black-violet hair", provenance="creator_seed"
            )
        }
    )
    character_service = FakeCharacterService(character)
    service = MomentCaptureService(
        character_service=character_service,  # type: ignore[arg-type]
        image_service=make_service(tmp_path, FakeCoordinator(), FakeAdapter()),
        records_path=tmp_path / "moment_captures.json",
    )
    record = MomentCaptureRecordForTest(_request(), "job-canon")
    service._records[record.capture_id] = record

    from app.services.moment_capture_service import (
        VisualChangeReviewRequest,
        VisualFeedbackRequest,
    )

    feedback = service.submit_feedback(
        record.capture_id,
        VisualFeedbackRequest(
            character_id="aria",
            action=VisualFeedbackAction.make_canon,
            trait_name="hair",
            trait_value="short silver hair",
            source_image_ref="/captures/aria.png",
        ),
    )

    event = feedback.visual_change_event
    assert event is not None
    assert event.canon_status == VisualChangeCanonStatus.proposed
    assert event.metadata["source_image_ref"] == "/captures/aria.png"
    assert (
        character_service.get_visual_identity("aria").evolving_traits[-1].value
        == "long black-violet hair"
    )
    assert feedback.record.review_state == ReviewState.canon_requested

    approved = service.approve_visual_change(
        event.event_id, VisualChangeReviewRequest(character_id="aria")
    )
    assert approved.event.canon_status == VisualChangeCanonStatus.canonized
    assert approved.event.rollback_id
    assert (
        character_service.get_visual_identity("aria").evolving_traits[-1].value
        == "short silver hair"
    )
    assert (
        "visual_change:"
        in character_service.get_visual_identity("aria").evolving_traits[-1].provenance
    )

    rollback = service.rollback_visual_change(
        event.event_id, VisualChangeReviewRequest(character_id="aria")
    )
    assert rollback.event.rollback_id == event.event_id
    assert rollback.event.canon_status == VisualChangeCanonStatus.rolled_back
    assert (
        character_service.get_visual_identity("aria").evolving_traits[-1].value
        == "long black-violet hair"
    )


def test_rejected_and_scene_only_feedback_do_not_update_positive_identity(
    tmp_path,
) -> None:
    character_service = FakeCharacterService(_character())
    service = MomentCaptureService(
        character_service=character_service,  # type: ignore[arg-type]
        image_service=make_service(tmp_path, FakeCoordinator(), FakeAdapter()),
        records_path=tmp_path / "moment_captures.json",
    )
    record = MomentCaptureRecordForTest(_request(), "job-reject")
    service._records[record.capture_id] = record

    from app.services.moment_capture_service import (
        VisualChangeReviewRequest,
        VisualFeedbackRequest,
    )
    from app.services.visual_prompt_compiler import VisualPromptCompiler

    rejected = service.submit_feedback(
        record.capture_id,
        VisualFeedbackRequest(
            character_id="aria",
            action=VisualFeedbackAction.reject_style_trait,
            trait_value="blue eyes",
        ),
    )
    assert rejected.visual_change_event is not None
    service.reject_visual_change(
        rejected.visual_change_event.event_id,
        VisualChangeReviewRequest(character_id="aria"),
    )
    assert "blue eyes" in character_service.get_visual_identity("aria").rejected_traits
    assert (
        character_service.get_visual_identity("aria").current_appearance
        == "long black-violet hair and a moon pendant"
    )

    scene_only = service.submit_feedback(
        record.capture_id,
        VisualFeedbackRequest(
            character_id="aria",
            action=VisualFeedbackAction.just_this_scene,
            trait_value="red dress",
        ),
    )
    assert scene_only.visual_change_event is None
    assert scene_only.record.metadata["feedback_summary"]["scene_only"] is True

    prompt = VisualPromptCompiler().compile(
        visual_identity=character_service.get_visual_identity("aria")
    )
    assert "blue eyes" not in prompt.positive_prompt
    assert "blue eyes" in prompt.negative_prompt


def MomentCaptureRecordForTest(request: MomentCaptureRequest, image_job_id: str):
    from app.schemas.moment_capture import MomentCaptureRecord

    return MomentCaptureRecord(
        capture_id=f"cap-{image_job_id}",
        character_id=request.character_id,
        conversation_id=request.conversation_id,
        session_id=request.session_id,
        source_message_id=request.source_message_id,
        source_turn_index=request.source_turn_index,
        scene_state=request.scene_state,
        relationship_phase_snapshot=request.relationship_phase_snapshot,
        visual_identity_version=request.visual_identity_version,
        visual_identity_updated_at=request.visual_identity_updated_at,
        prompt_hash=request.prompt_hash,
        image_job_id=image_job_id,
        output_paths=[f"/tmp/{image_job_id}.png"],
    )


class FakeMemoryManager:
    def __init__(self) -> None:
        self.memories: list[dict[str, object]] = []

    def add_memory(self, text: str, metadata: dict[str, object]) -> dict[str, object]:
        if metadata.get("memory_scope") == "character_private" and not metadata.get(
            "character_id"
        ):
            raise ValueError("missing character_id")
        memory = {
            "id": f"mem-{len(self.memories) + 1}",
            "text": text,
            "metadata": metadata,
            "source": metadata.get("source", "test"),
        }
        self.memories.append(memory)
        return memory

    def search_memories(
        self, query: str, limit: int = 10, *, character_id: str | None = None
    ):
        results = []
        for memory in self.memories:
            metadata = memory["metadata"]
            if character_id and not (
                metadata.get("character_id") == character_id
                or metadata.get("memory_scope") in {"shared", "global"}
            ):
                continue
            results.append(memory)
        return results[:limit]

    def delete_memory(self, memory_id: str) -> bool:
        before = len(self.memories)
        self.memories = [m for m in self.memories if m["id"] != memory_id]
        return len(self.memories) != before


class FakeReflectionManager:
    def __init__(self) -> None:
        self.entries = []

    def save_journal_entry(self, entry):
        self.entries.append(entry)
        return entry


def _service_with_memory(tmp_path, memory: FakeMemoryManager):
    return MomentCaptureService(
        character_service=FakeCharacterService(_character()),  # type: ignore[arg-type]
        image_service=make_service(tmp_path, FakeCoordinator(), FakeAdapter()),
        records_path=tmp_path / "moment_captures.json",
        memory_manager=memory,  # type: ignore[arg-type]
        reflection_manager=FakeReflectionManager(),  # type: ignore[arg-type]
    )


def test_approved_visual_feedback_writes_character_scoped_visual_memory(
    tmp_path,
) -> None:
    from app.services.moment_capture_service import VisualFeedbackRequest

    memory = FakeMemoryManager()
    service = _service_with_memory(tmp_path, memory)
    record = MomentCaptureRecordForTest(_request(), "job-memory")
    service._records[record.capture_id] = record

    response = service.submit_feedback(
        record.capture_id,
        VisualFeedbackRequest(
            character_id="aria",
            action=VisualFeedbackAction.looks_right,
            note="Keep the moon pendant and gentle balcony mood.",
        ),
    )

    assert len(memory.memories) == 1
    metadata = memory.memories[0]["metadata"]
    assert metadata["character_id"] == "aria"
    assert metadata["memory_scope"] == "character_private"
    assert metadata["capture_id"] == record.capture_id
    assert metadata["image_job_id"] == "job-memory"
    assert metadata["feedback_action"] == "looks_right"
    assert metadata["source"] == "visual_feedback"
    assert metadata["training_eligible"] is False
    artifact_metadata = response.record.visual_memory_artifacts[0].metadata
    assert response.record.visual_memory_artifacts[0].memory_id == "mem-1"
    assert response.record.visual_memory_artifacts[0].training_candidate is False
    assert artifact_metadata["training_candidate"] is False
    assert artifact_metadata["training_eligible"] is False
    assert artifact_metadata["training_eligibility"] == "not_eligible"
    assert memory.search_memories("pendant", character_id="aria")
    assert memory.search_memories("pendant", character_id="other") == []


def test_shared_visual_memory_is_explicitly_cross_character_and_deletable(
    tmp_path,
) -> None:
    from app.services.moment_capture_service import VisualFeedbackRequest

    memory = FakeMemoryManager()
    service = _service_with_memory(tmp_path, memory)
    record = MomentCaptureRecordForTest(_request(), "job-shared")
    service._records[record.capture_id] = record

    service.submit_feedback(
        record.capture_id,
        VisualFeedbackRequest(
            character_id="aria",
            action=VisualFeedbackAction.looks_right,
            metadata={"memory_scope": "shared"},
        ),
    )

    assert memory.search_memories("balcony", character_id="aria")
    assert memory.search_memories("balcony", character_id="other")
    assert memory.delete_memory("mem-1") is True
    assert memory.search_memories("balcony", character_id="aria") == []


def test_rejected_private_and_pending_feedback_do_not_create_visual_memory(
    tmp_path,
) -> None:
    from app.services.moment_capture_service import VisualFeedbackRequest

    memory = FakeMemoryManager()
    service = _service_with_memory(tmp_path, memory)
    record = MomentCaptureRecordForTest(_request(), "job-no-memory")
    service._records[record.capture_id] = record

    service.submit_feedback(
        record.capture_id,
        VisualFeedbackRequest(
            character_id="aria",
            action=VisualFeedbackAction.reject_style_trait,
            trait_value="blue eyes",
        ),
    )
    service.submit_feedback(
        record.capture_id,
        VisualFeedbackRequest(
            character_id="aria",
            action=VisualFeedbackAction.looks_right,
            metadata={"private": True},
        ),
    )

    assert memory.memories == []
