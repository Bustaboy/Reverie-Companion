from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core.config import Settings
from app.models.image import ImageGenerateRequest, ImageJobRead, ImageJobStatus, ImageQualityPreset
from app.repositories.character_repo import CharacterRepository
from app.schemas.character_blueprint import CharacterCreate
from app.schemas.moment_capture import MomentCaptureRequest, SceneState
from app.schemas.visual_identity import VisualIdentityProfile
from app.services.character_service import CharacterNotFoundError, CharacterService
from app.services.moment_capture_service import MomentCaptureService


class FakeImageService:
    def __init__(self) -> None:
        self.requests: list[ImageGenerateRequest] = []

    async def submit(self, request: ImageGenerateRequest) -> ImageJobRead:
        self.requests.append(request)
        return ImageJobRead(
            job_id="img_test_1",
            status=ImageJobStatus.queued,
            prompt=request.prompt,
            negative_prompt=request.negative_prompt or "none",
            requested_preset=request.quality_preset,
            active_preset=request.quality_preset,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            progress=0.0,
            phase="queued",
            message="queued",
            conversation_id=request.conversation_id,
            source=request.source,
            source_message_id=request.source_message_id,
        )


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        image_generation_history_path=str(tmp_path / "images" / "history.json"),
        image_generation_output_dir=str(tmp_path / "images" / "generated"),
        character_assets_dir=str(tmp_path / "characters"),
        character_db_path=str(tmp_path / "characters.sqlite3"),
    )


def _character_service(tmp_path: Path) -> CharacterService:
    service = CharacterService(CharacterRepository(tmp_path / "characters.sqlite3"))
    character = service.create(
        CharacterCreate(
            character_id="aria",
            display_name="Aria",
            core_traits=["tender", "playful"],
        )
    )
    character.visual_identity.identity_anchors = ["amber eyes", "warm brown skin"]
    character.visual_identity.current_appearance = "black-violet hair, soft smile"
    character.visual_identity.rejected_traits = ["blue eyes"]
    service.save(character)
    return service


def _request(character_id: str = "aria") -> MomentCaptureRequest:
    visual_identity = VisualIdentityProfile(
        identity_anchors=["amber eyes", "warm brown skin"],
        current_appearance="black-violet hair",
        rejected_traits=["blue eyes"],
    )
    return MomentCaptureRequest.from_chat_turn(
        character_id=character_id,
        conversation_id="conv-1",
        session_id="sess-1",
        source_message_id="msg-7",
        source_turn_index=7,
        scene_state=SceneState(
            location="moonlit balcony",
            mood="tender",
            character_appearance=["black-violet hair"],
            wrong_appearance=["blue eyes"],
        ),
        visual_identity=visual_identity,
        quality_preset=ImageQualityPreset.preview_8gb,
        metadata={"capture_intent": "capture this tender balcony moment"},
    )


def test_moment_capture_queues_job_and_persists_record_with_metadata(tmp_path) -> None:
    async def run_test() -> None:
        image_service = FakeImageService()
        service = MomentCaptureService(
            settings=_settings(tmp_path),
            character_service=_character_service(tmp_path),
            image_service=image_service,  # type: ignore[arg-type]
        )

        record = await service.capture(_request())

        assert record.image_job_id == "img_test_1"
        assert record.character_id == "aria"
        assert record.prompt_hash
        assert record.output_paths == ["pending://img_test_1"]
        assert len(image_service.requests) == 1
        queued = image_service.requests[0]
        assert queued.source == "moment_capture"
        assert queued.source_message_id == "msg-7"
        assert queued.context["capture_type"] == "moment_capture"  # type: ignore[index]
        assert queued.context["character_id"] == "aria"  # type: ignore[index]
        assert queued.context["prompt_hash"] == record.prompt_hash  # type: ignore[index]
        assert queued.context["scene_state"]["location"] == "moonlit balcony"  # type: ignore[index]
        assert service.list_records()[0].capture_id == record.capture_id

    asyncio.run(run_test())


def test_missing_specific_character_returns_structured_service_error(tmp_path) -> None:
    async def run_test() -> None:
        service = MomentCaptureService(
            settings=_settings(tmp_path),
            character_service=_character_service(tmp_path),
            image_service=FakeImageService(),  # type: ignore[arg-type]
        )

        with pytest.raises(CharacterNotFoundError) as exc_info:
            await service.capture(_request("missing-character"))
        assert exc_info.value.character_id == "missing-character"

    asyncio.run(run_test())


def test_moment_capture_submit_is_non_blocking_and_uses_image_queue_boundary(tmp_path) -> None:
    async def run_test() -> None:
        image_service = FakeImageService()
        service = MomentCaptureService(
            settings=_settings(tmp_path),
            character_service=_character_service(tmp_path),
            image_service=image_service,  # type: ignore[arg-type]
        )

        record = await asyncio.wait_for(service.capture(_request()), timeout=0.5)

        assert record.image_job_id == "img_test_1"
        assert image_service.requests[0].quality_preset == ImageQualityPreset.preview_8gb
        bundle = image_service.requests[0].context["visual_prompt_bundle"]  # type: ignore[index]
        assert bundle["positive_prompt_present"] is True

    asyncio.run(run_test())
