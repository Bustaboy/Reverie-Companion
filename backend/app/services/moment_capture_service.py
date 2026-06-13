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
from app.schemas.moment_capture import (
    FeedbackState,
    MomentCaptureRecord,
    MomentCaptureRequest,
    ReviewState,
    VisualChangeCanonStatus,
    VisualChangeEvent,
    VisualFeedbackAction,
    VisualFeedbackRequest,
    utc_now_iso,
)
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
        self._events_path = self._records_path.with_name("visual_change_events.json")
        self._records_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, MomentCaptureRecord] = self._load_records()
        self._events: dict[str, VisualChangeEvent] = self._load_events()

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

    def submit_feedback(
        self, capture_id: str, request: VisualFeedbackRequest
    ) -> tuple[MomentCaptureRecord, VisualChangeEvent | None]:
        """Persist capture feedback and create reviewable visual events when needed."""

        record = self._require_record(capture_id, request.character_id)
        character = self._character_service.load_by_id(request.character_id)
        action = request.action
        metadata = dict(record.metadata)
        feedback_summary = {
            "action": action.value,
            "note": request.note,
            "changed_trait": request.changed_trait,
            "proposed_value": request.proposed_value,
            "rejected_trait": request.rejected_trait,
            "source_image_ref": request.source_image_ref
            or self._source_image_ref(record),
            "updated_at": utc_now_iso(),
        }
        metadata["feedback_summary"] = feedback_summary

        event: VisualChangeEvent | None = None
        feedback_state = record.feedback_state
        review_state = record.review_state
        rollback_id = record.rollback_id

        if action == VisualFeedbackAction.looks_right:
            feedback_state = FeedbackState.looks_right
            review_state = ReviewState.accepted
        elif action == VisualFeedbackAction.wrong_appearance:
            feedback_state = FeedbackState.wrong_appearance
            rejected = request.rejected_trait or request.proposed_value or request.note
            metadata.setdefault("rejected_visual_evidence", [])
            if rejected:
                metadata["rejected_visual_evidence"].append(str(rejected))
        elif action == VisualFeedbackAction.just_this_scene:
            feedback_state = FeedbackState.looks_right
            metadata["scene_only"] = True
        elif action == VisualFeedbackAction.reject_style_trait:
            feedback_state = FeedbackState.rejected
            rejected = request.rejected_trait or request.proposed_value or request.note
            if rejected:
                metadata.setdefault("rejected_trait_additions", []).append(
                    str(rejected)
                )
                self._add_rejected_trait(
                    request.character_id, str(rejected), source=capture_id
                )
        elif action in {
            VisualFeedbackAction.make_canon,
            VisualFeedbackAction.use_outfit_again,
        }:
            changed_trait = request.changed_trait or (
                "outfit"
                if action == VisualFeedbackAction.use_outfit_again
                else "appearance"
            )
            new_value = (
                request.proposed_value or request.note or record.scene_state.outfit
            )
            if not new_value:
                raise ValueError(
                    "Canon-affecting feedback requires proposed_value or note."
                )
            previous_value = self._previous_visual_value(
                character.visual_identity, changed_trait
            )
            event = VisualChangeEvent(
                event_id=f"vce_{uuid4().hex}",
                character_id=request.character_id,
                capture_id=capture_id,
                changed_trait=changed_trait,
                previous_value=previous_value,
                new_value=str(new_value),
                reason=request.note
                or f"User selected {action.value} for reviewed Moment Capture.",
                feedback_action=action,
                canon_status=VisualChangeCanonStatus.proposed,
                rollback_id=f"rollback_{uuid4().hex}",
                metadata={
                    "source_image_ref": request.source_image_ref
                    or self._source_image_ref(record),
                    "provenance": f"moment_capture:{capture_id}",
                    **request.metadata,
                },
            )
            self._events[event.event_id] = event
            self._write_events()
            feedback_state = FeedbackState.looks_right
            review_state = ReviewState.canon_requested
            rollback_id = event.event_id

        updated = MomentCaptureRecord.model_validate(
            {
                **record.model_dump(mode="json"),
                "feedback_state": feedback_state,
                "review_state": review_state,
                "feedback_actions": [*record.feedback_actions, action],
                "metadata": metadata,
                "rollback_id": rollback_id,
                "updated_at": utc_now_iso(),
            }
        )
        self._records[capture_id] = updated
        self._write_records()
        return updated, event

    def list_visual_changes(
        self, *, character_id: str, status: VisualChangeCanonStatus | None = None
    ) -> list[VisualChangeEvent]:
        return [
            event
            for event in sorted(self._events.values(), key=lambda item: item.created_at)
            if event.character_id == character_id
            and (status is None or event.canon_status == status)
        ]

    def get_visual_change(
        self, event_id: str, *, character_id: str
    ) -> VisualChangeEvent | None:
        event = self._events.get(event_id)
        if event is None or event.character_id != character_id:
            return None
        return event

    def approve_visual_change(
        self, event_id: str, *, character_id: str, note: str | None = None
    ) -> VisualChangeEvent:
        event = self._require_event(event_id, character_id)
        if event.canon_status != VisualChangeCanonStatus.proposed:
            raise ValueError("Only pending visual changes can be approved.")
        provenance = f"visual_change_event:{event.event_id}"
        self._character_service.update_visual_identity(
            character_id,
            {
                "evolving_trait": {
                    "name": event.changed_trait,
                    "value": event.new_value,
                    "provenance": provenance,
                },
                "rejected_traits": self._without_rejected_trait(
                    character_id, event.new_value
                ),
            },
        )
        approved = event.model_copy(
            update={
                "canon_status": VisualChangeCanonStatus.approved,
                "updated_at": utc_now_iso(),
                "metadata": {
                    **event.metadata,
                    "approval_note": note,
                    "provenance": provenance,
                    "rollback_source_event_id": event.event_id,
                },
            }
        )
        self._events[event_id] = approved
        self._write_events()
        return approved

    def reject_visual_change(
        self, event_id: str, *, character_id: str, note: str | None = None
    ) -> VisualChangeEvent:
        event = self._require_event(event_id, character_id)
        rejected = event.model_copy(
            update={
                "canon_status": VisualChangeCanonStatus.rejected,
                "updated_at": utc_now_iso(),
                "metadata": {**event.metadata, "rejection_note": note},
            }
        )
        self._events[event_id] = rejected
        self._write_events()
        return rejected

    def rollback_visual_change(
        self, event_id: str, *, character_id: str, note: str | None = None
    ) -> VisualChangeEvent:
        event = self._require_event(event_id, character_id)
        if (
            event.canon_status != VisualChangeCanonStatus.approved
            or not event.rollback_available
        ):
            raise ValueError(
                "Only approved changes with rollback metadata can be rolled back."
            )
        rollback = VisualChangeEvent(
            event_id=f"vce_{uuid4().hex}",
            character_id=character_id,
            capture_id=event.capture_id,
            changed_trait=event.changed_trait,
            previous_value=event.new_value,
            new_value=event.previous_value or "",
            reason=note or f"Rollback of approved visual change {event.event_id}.",
            feedback_action=VisualFeedbackAction.rollback,
            canon_status=VisualChangeCanonStatus.rolled_back,
            rollback_id=event.event_id,
            metadata={**event.metadata, "rollback_of": event.event_id},
        )
        self._character_service.update_visual_identity(
            character_id,
            {
                "evolving_trait": {
                    "name": event.changed_trait,
                    "value": rollback.new_value,
                    "provenance": f"visual_change_rollback:{rollback.event_id}",
                },
            },
        )
        self._events[event.event_id] = event.model_copy(
            update={
                "canon_status": VisualChangeCanonStatus.rolled_back,
                "updated_at": utc_now_iso(),
            }
        )
        self._events[rollback.event_id] = rollback
        self._write_events()
        return rollback

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

    def _load_events(self) -> dict[str, VisualChangeEvent]:
        if not self._events_path.exists():
            return {}
        data = json.loads(self._events_path.read_text(encoding="utf-8"))
        return {
            item["event_id"]: VisualChangeEvent.model_validate(item)
            for item in data.get("items", [])
        }

    def _write_events(self) -> None:
        payload = {
            "schema_version": "visual_change_events.v1",
            "items": [
                event.model_dump(mode="json")
                for event in sorted(
                    self._events.values(), key=lambda item: item.created_at
                )
            ],
        }
        self._events_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )

    def _require_record(
        self, capture_id: str, character_id: str
    ) -> MomentCaptureRecord:
        record = self._records.get(capture_id)
        if record is None or record.character_id != character_id:
            raise KeyError(capture_id)
        return record

    def _require_event(self, event_id: str, character_id: str) -> VisualChangeEvent:
        event = self.get_visual_change(event_id, character_id=character_id)
        if event is None:
            raise KeyError(event_id)
        return event

    def _source_image_ref(self, record: MomentCaptureRecord) -> str:
        return (
            record.output_paths[0]
            if record.output_paths
            else f"image-job:{record.image_job_id}"
        )

    def _previous_visual_value(self, profile, changed_trait: str) -> str | None:
        for trait in profile.evolving_traits:
            if trait.name == changed_trait:
                return trait.value
        return profile.current_appearance

    def _add_rejected_trait(
        self, character_id: str, trait: str, *, source: str
    ) -> None:
        visual = self._character_service.get_visual_identity(character_id)
        rejected = [*visual.rejected_traits, trait]
        self._character_service.update_visual_identity(
            character_id,
            {
                "rejected_traits": rejected,
                "current_appearance": visual.current_appearance,
            },
        )

    def _without_rejected_trait(self, character_id: str, value: str) -> list[str]:
        visual = self._character_service.get_visual_identity(character_id)
        return [
            item
            for item in visual.rejected_traits
            if item.casefold() != value.casefold()
        ]
