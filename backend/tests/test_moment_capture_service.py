"""Moment Capture orchestration coverage."""

from __future__ import annotations

import asyncio

import pytest

from app.models.image import ImageJobStatus, ImageQualityPreset
from app.schemas.character_blueprint import CharacterBlueprint, CharacterIdentity
from app.schemas.moment_capture import MomentCaptureRequest, SceneState
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
            job.context["moment_capture"]["prompt_hash"]
            == response.record.prompt_hash
        )
        assert (
            job.context["moment_capture"]["scene_state"]["location"]
            == "rainy balcony"
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
