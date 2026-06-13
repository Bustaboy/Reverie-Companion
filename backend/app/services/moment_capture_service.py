"""Moment Capture orchestration service.

High-level flow:

1. Load the explicitly selected character through ``CharacterService``.
2. Build a ``VisualPromptBundle`` through ``VisualPromptCompiler`` using the
   character visual identity plus scene/dialogue capture context.
3. Submit an ``ImageGenerateRequest`` to ``ImageGenerationService`` as a queue-only
   operation; this service never calls image backends or waits for completion.
4. Create and persist a ``MomentCaptureRecord`` linked to the queued image job.

This service coordinates those boundaries only. It deliberately does not own image
generation, block on image completion, or mutate visual canon.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.models.image import ImageGenerateRequest, ImageJobRead
from app.schemas.moment_capture import MomentCaptureRecord, MomentCaptureRequest
from app.services.character_service import CharacterService
from app.services.image_generation_service import (
    ImageGenerationService,
    get_image_generation_service,
)
from app.services.visual_prompt_compiler import VisualPromptBundle, VisualPromptCompiler


class MomentCaptureResponse(BaseModel):
    """Response returned when a capture has been recorded and queued."""

    request_id: str
    record: MomentCaptureRecord
    job: ImageJobRead
    prompt_bundle: VisualPromptBundle


class MomentCaptureService:
    """Orchestrate non-blocking Moment Capture job creation."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        character_service: CharacterService | None = None,
        image_service: ImageGenerationService | None = None,
        prompt_compiler: VisualPromptCompiler | None = None,
        records_path: Path | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._character_service = character_service or CharacterService.from_settings(
            self._settings
        )
        self._image_service = image_service or get_image_generation_service(
            self._settings
        )
        self._prompt_compiler = prompt_compiler or VisualPromptCompiler()
        self._records_path = records_path or self._default_records_path(self._settings)
        self._records_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, MomentCaptureRecord] = self._load_records()

    async def capture(self, request: MomentCaptureRequest) -> MomentCaptureResponse:
        """Create a durable capture record and queue image generation.

        The only awaited heavy-path call is ImageGenerationService.submit, which
        enqueues work and returns immediately without waiting for generation.
        """

        character = self._character_service.load_by_id(request.character_id)
        scene_state = request.scene_state.model_dump(mode="json")
        capture_intent = str(
            request.metadata.get("capture_intent")
            or request.metadata.get("user_instruction")
            or "capture this moment"
        )
        prompt_bundle = self._prompt_compiler.compile(
            character=character,
            character_id=request.character_id,
            visual_identity=request.visual_identity_snapshot,
            scene_state=scene_state,
            capture_intent=capture_intent,
            relationship_context=character.relationship.prompt_summary(),
            emotional_tone=request.scene_state.emotional_tone,
        )
        prompt_hash = str(
            prompt_bundle.metadata.get("prompt_hash") or request.prompt_hash
        )
        capture_id = f"mc_{uuid4().hex}"
        context = self._job_context(
            request=request,
            capture_id=capture_id,
            capture_intent=capture_intent,
            prompt_bundle=prompt_bundle,
            prompt_hash=prompt_hash,
            character_name=character.identity.display_name,
        )
        job = await self._image_service.submit(
            ImageGenerateRequest(
                conversation_id=request.conversation_id,
                source="moment_capture",
                source_message_id=request.source_message_id,
                prompt=prompt_bundle.positive_prompt,
                negative_prompt=prompt_bundle.negative_prompt,
                context=context,
                quality_preset=request.quality_preset,
            )
        )
        record = MomentCaptureRecord(
            capture_id=capture_id,
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
            output_paths=[f"queued://image-job/{job.job_id}"],
            visual_memory_artifacts=list(request.relevant_visual_memories),
            metadata={
                "capture_intent": capture_intent,
                "image_job_status": job.status,
                "image_job_source": job.source,
                "prompt_bundle_metadata": prompt_bundle.metadata,
                "request_created_at": request.created_at,
                **request.metadata,
            },
        )
        self._records[record.capture_id] = record
        self._write_records()
        return MomentCaptureResponse(
            request_id=str(uuid4()),
            record=record,
            job=job,
            prompt_bundle=prompt_bundle,
        )

    def get_record(self, capture_id: str) -> MomentCaptureRecord | None:
        return self._records.get(capture_id)

    @staticmethod
    def _default_records_path(settings: Settings) -> Path:
        return Path(settings.image_generation_history_path).with_name(
            "moment_captures.json"
        )

    def _job_context(
        self,
        *,
        request: MomentCaptureRequest,
        capture_id: str,
        capture_intent: str,
        prompt_bundle: VisualPromptBundle,
        prompt_hash: str,
        character_name: str,
    ) -> dict[str, Any]:
        return {
            "moment_capture": {
                "schema_version": request.schema_version,
                "capture_id": capture_id,
                "character_id": request.character_id,
                "conversation_id": request.conversation_id,
                "session_id": request.session_id,
                "source_message_id": request.source_message_id,
                "source_turn_index": request.source_turn_index,
                "prompt_hash": prompt_hash,
                "capture_intent": capture_intent,
                "scene_state": request.scene_state.model_dump(mode="json"),
                "relationship_phase_snapshot": str(request.relationship_phase_snapshot),
                "visual_identity_version": request.visual_identity_version,
                "visual_identity_updated_at": request.visual_identity_updated_at,
                "relevant_visual_memory_ids": [
                    artifact.artifact_id
                    for artifact in request.relevant_visual_memories
                ],
                "prompt_bundle_metadata": prompt_bundle.metadata,
            },
            "character": {
                "id": request.character_id,
                "name": character_name,
                "appearance": request.visual_identity_snapshot.current_appearance,
            },
            "scene_tags": ["moment_capture"],
            "participants": ["character"],
        }

    def _load_records(self) -> dict[str, MomentCaptureRecord]:
        if not self._records_path.exists():
            return {}
        data = json.loads(self._records_path.read_text(encoding="utf-8"))
        return {
            item["capture_id"]: MomentCaptureRecord.model_validate(item)
            for item in data.get("items", [])
        }

    def _write_records(self) -> None:
        payload = {
            "schema_version": "moment_capture_records.v1",
            "items": [
                record.model_dump(mode="json")
                for record in sorted(
                    self._records.values(), key=lambda item: item.created_at
                )
            ],
        }
        self._records_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
