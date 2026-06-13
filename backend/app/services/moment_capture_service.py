"""Moment Capture orchestration service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import Settings, get_settings
from app.models.image import ImageGenerateRequest
from app.schemas.moment_capture import (
    MomentCaptureRecord,
    MomentCaptureRequest,
    utc_now_iso,
)
from app.services.character_service import CharacterNotFoundError, CharacterService
from app.services.image_generation_service import (
    ImageGenerationService,
    get_image_generation_service,
)
from app.services.visual_prompt_compiler import VisualPromptCompiler


class MomentCaptureService:
    """Coordinate character loading, prompt compilation, image queueing, and record persistence.

    The service deliberately does not generate images directly and never waits for
    image completion. Heavy work remains behind ``ImageGenerationService`` so chat
    and TTS priority/resource behavior stay unchanged.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        character_service: CharacterService,
        image_service: ImageGenerationService,
        prompt_compiler: VisualPromptCompiler | None = None,
        records_path: Path | None = None,
    ) -> None:
        self._settings = settings
        self._character_service = character_service
        self._image_service = image_service
        self._prompt_compiler = prompt_compiler or VisualPromptCompiler()
        self._records_path = records_path or (
            Path(settings.image_generation_history_path).parent / "moment_captures.json"
        )
        self._records_path.parent.mkdir(parents=True, exist_ok=True)

    async def capture(self, request: MomentCaptureRequest) -> MomentCaptureRecord:
        """Create a queued Moment Capture job and persist its initial record."""

        character = self._character_service.load_by_id(request.character_id)
        bundle = self._prompt_compiler.compile(
            character=character,
            visual_identity=request.visual_identity_snapshot,
            character_id=request.character_id,
            scene_state=request.scene_state.model_dump(mode="json"),
            capture_intent=str(
                request.metadata.get("capture_intent") or "capture this moment"
            ),
            relationship_context=character.relationship.prompt_summary(),
            emotional_tone=(
                request.scene_state.emotional_tone or request.scene_state.mood
            ),
        )
        prompt_hash = str(bundle.metadata.get("prompt_hash") or request.prompt_hash)
        context = self._build_job_context(request, bundle.metadata, prompt_hash)
        job = await self._image_service.submit(
            ImageGenerateRequest(
                conversation_id=request.conversation_id,
                source="moment_capture",
                source_message_id=request.source_message_id,
                prompt=bundle.positive_prompt,
                negative_prompt=bundle.negative_prompt,
                context=context,
                quality_preset=request.quality_preset,
            )
        )
        record = MomentCaptureRecord(
            capture_id=f"cap_{uuid4().hex}",
            character_id=request.character_id,
            conversation_id=request.conversation_id,
            session_id=request.session_id,
            source_message_id=request.source_message_id,
            source_turn_index=request.source_turn_index,
            scene_state=request.scene_state,
            relationship_phase_snapshot=request.relationship_phase_snapshot,
            visual_identity_version=request.visual_identity_version,
            visual_identity_updated_at=request.visual_identity_updated_at,
            prompt_hash=prompt_hash,
            image_job_id=job.job_id,
            output_paths=[f"pending://{job.job_id}"],
            visual_memory_artifacts=list(request.relevant_visual_memories),
            metadata={
                "queued": True,
                "source": "moment_capture",
                "quality_preset": request.quality_preset.value,
                "job_context": context,
            },
        )
        self._append_record(record)
        return record

    def list_records(self) -> list[MomentCaptureRecord]:
        return self._load_records()

    def _build_job_context(
        self,
        request: MomentCaptureRequest,
        prompt_metadata: dict[str, Any],
        prompt_hash: str,
    ) -> dict[str, Any]:
        return {
            "capture_type": "moment_capture",
            "character_id": request.character_id,
            "conversation_id": request.conversation_id,
            "session_id": request.session_id,
            "source_message_id": request.source_message_id,
            "source_turn_index": request.source_turn_index,
            "prompt_hash": prompt_hash,
            "scene_state": request.scene_state.model_dump(mode="json"),
            "relationship_phase_snapshot": str(request.relationship_phase_snapshot),
            "visual_identity_version": request.visual_identity_version,
            "visual_identity_updated_at": request.visual_identity_updated_at,
            "relevant_visual_memory_ids": [
                artifact.artifact_id for artifact in request.relevant_visual_memories
            ],
            "visual_prompt_bundle": {
                "metadata": prompt_metadata,
                "positive_prompt_present": True,
                "negative_prompt_present": True,
            },
            "request_metadata": request.metadata,
        }

    def _load_records(self) -> list[MomentCaptureRecord]:
        if not self._records_path.exists():
            return []
        try:
            payload = json.loads(
                self._records_path.read_text(encoding="utf-8") or "[]"
            )
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(payload, list):
            return []
        return [MomentCaptureRecord.model_validate(item) for item in payload]

    def _append_record(self, record: MomentCaptureRecord) -> None:
        records = self._load_records()
        records.append(record.model_copy(update={"updated_at": utc_now_iso()}))
        self._records_path.write_text(
            json.dumps([item.model_dump(mode="json") for item in records], indent=2),
            encoding="utf-8",
        )


def get_moment_capture_service(settings: Settings | None = None) -> MomentCaptureService:
    settings = settings or get_settings()
    return MomentCaptureService(
        settings=settings,
        character_service=CharacterService.from_settings(settings),
        image_service=get_image_generation_service(settings),
    )
