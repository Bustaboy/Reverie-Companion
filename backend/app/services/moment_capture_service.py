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
from app.core.memory import (
    MemoryError,
    MemoryManager,
    character_private_metadata,
    get_memory_manager,
)
from app.core.reflection import ReflectionManager, get_reflection_manager
from app.models.image import ImageGenerateRequest, ImageJobRead
from app.schemas.moment_capture import (
    FeedbackState,
    MomentCaptureRecord,
    MomentCaptureRequest,
    ReviewState,
    VisualChangeCanonStatus,
    VisualChangeEvent,
    VisualChangeReviewRequest,
    VisualChangeReviewResponse,
    VisualFeedbackRequest,
    VisualFeedbackResponse,
    VisualFeedbackAction,
    VisualMemoryArtifact,
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
        memory_manager: MemoryManager | None = None,
        reflection_manager: ReflectionManager | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._character_service = character_service or CharacterService.from_settings(
            self._settings
        )
        self._image_service = image_service or get_image_generation_service(
            self._settings
        )
        self._prompt_compiler = prompt_compiler or VisualPromptCompiler()
        self._memory_manager = memory_manager or get_memory_manager()
        self._reflection_manager = reflection_manager or get_reflection_manager()
        self._records_path = records_path or self._default_records_path(self._settings)
        self._events_path = self._records_path.with_name("visual_change_events.json")
        self._records_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, MomentCaptureRecord] = self._load_records()
        self._events: dict[str, VisualChangeEvent] = self._load_events()
        self._transient_blueprints: dict[str, Any] = {}

    async def capture(self, request: MomentCaptureRequest) -> MomentCaptureResponse:
        """Create a durable capture record and queue image generation.

        The only awaited heavy-path call is ImageGenerationService.submit, which
        enqueues work and returns immediately without waiting for generation.
        """

        character = self._character_service.load_by_id(request.character_id)
        return await self._capture_with_character(request, character)

    async def capture_for_blueprint(
        self, request: MomentCaptureRequest, character: Any
    ) -> MomentCaptureResponse:
        """Queue Moment Capture for a transient draft blueprint.

        This bridge lets creator draft validation reuse the existing Moment
        Capture prompt/job/record path without requiring draft persistence or a
        duplicate image-generation abstraction. It remains non-blocking and does
        not mutate visual canon; feedback/review/rollback still use existing
        VisualChangeEvent flows after a real character is saved.
        """

        if character.character_id != request.character_id:
            raise ValueError("Draft blueprint character_id must match capture request.")
        self._transient_blueprints[character.character_id] = character
        return await self._capture_with_character(request, character)

    async def _capture_with_character(
        self, request: MomentCaptureRequest, character: Any
    ) -> MomentCaptureResponse:
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
                **self._creator_capture_metadata(request),
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
    ) -> VisualFeedbackResponse:
        record = self._require_record(capture_id)
        if record.character_id != request.character_id:
            raise ValueError(
                "Feedback character_id must match the capture character_id."
            )

        action = self._canonical_action(request.action)
        event: VisualChangeEvent | None = None
        metadata = dict(record.metadata)
        feedback_summary = dict(metadata.get("feedback_summary") or {})
        feedback_summary.update(
            {
                "latest_action": action.value,
                "latest_note": request.note,
                "source_image_ref": request.source_image_ref
                or (record.output_paths[0] if record.output_paths else None),
                "updated_at": utc_now_iso(),
            }
        )

        state = record.feedback_state
        review_state = record.review_state
        rollback_id = record.rollback_id
        if action == VisualFeedbackAction.looks_right:
            state = FeedbackState.looks_right
            review_state = ReviewState.accepted
        elif action == VisualFeedbackAction.wrong_appearance:
            state = FeedbackState.wrong_appearance
            event = self._build_event(record, request, action, "rejected_trait")
        elif action == VisualFeedbackAction.make_canon:
            state = FeedbackState.looks_right
            review_state = ReviewState.canon_requested
            event = self._build_event(record, request, action, "evolving_trait")
            rollback_id = event.event_id
        elif action == VisualFeedbackAction.use_outfit_again:
            state = FeedbackState.looks_right
            review_state = ReviewState.canon_requested
            event = self._build_event(record, request, action, "outfit")
            rollback_id = event.event_id
        elif action == VisualFeedbackAction.reject_style_trait:
            state = FeedbackState.rejected
            event = self._build_event(record, request, action, "rejected_trait")
            feedback_summary["proposed_rejected_trait"] = event.new_value
        elif action == VisualFeedbackAction.just_this_scene:
            feedback_summary["scene_only"] = True
        else:
            feedback_summary["legacy_or_non_m5_action"] = action.value

        actions = [*record.feedback_actions, action]
        metadata["feedback_summary"] = feedback_summary
        updated = MomentCaptureRecord.model_validate(
            {
                **record.model_dump(),
                "feedback_state": state,
                "review_state": review_state,
                "feedback_actions": actions,
                "rollback_id": rollback_id,
                "metadata": metadata,
                "updated_at": utc_now_iso(),
            }
        )
        self._records[capture_id] = updated
        if event:
            self._events[event.event_id] = event
            metadata = dict(updated.metadata)
            metadata["feedback_summary"] = {
                **feedback_summary,
                "visual_change_event_id": event.event_id,
            }
            self._records[capture_id] = updated.model_copy(
                update={"metadata": metadata}
            )
            updated = self._records[capture_id]
        if action in {VisualFeedbackAction.looks_right, VisualFeedbackAction.favorite}:
            updated = self._write_visual_memory_artifact(
                updated, request, action, review_state.value
            )
        self._write_records()
        self._write_events()
        return VisualFeedbackResponse(record=updated, visual_change_event=event)

    def list_visual_changes(
        self,
        *,
        status: VisualChangeCanonStatus | None = None,
        character_id: str | None = None,
    ) -> list[VisualChangeEvent]:
        events = list(self._events.values())
        if status is not None:
            events = [event for event in events if event.canon_status == status]
        if character_id is not None:
            events = [event for event in events if event.character_id == character_id]
        return sorted(events, key=lambda event: event.created_at)

    def get_visual_change(self, event_id: str) -> VisualChangeEvent | None:
        return self._events.get(event_id)

    def approve_visual_change(
        self, event_id: str, request: VisualChangeReviewRequest
    ) -> VisualChangeReviewResponse:
        event = self._require_event(event_id, request.character_id)
        if event.canon_status != VisualChangeCanonStatus.proposed:
            raise ValueError("Only proposed visual changes can be approved.")
        provenance = (
            f"visual_change:{event.event_id}; capture:{event.capture_id or 'unknown'}"
        )
        if event.changed_trait == "rejected_trait":
            current = self._character_service.get_visual_identity(event.character_id)
            rejected = [*current.rejected_traits, event.new_value]
            visual = self._character_service.update_visual_identity(
                event.character_id, {"rejected_traits": rejected}
            )
        else:
            visual = self._character_service.update_visual_identity(
                event.character_id,
                {
                    "evolving_trait": {
                        "name": event.changed_trait,
                        "value": event.new_value,
                        "provenance": provenance,
                    }
                },
            )
        updated = event.model_copy(
            update={
                "canon_status": VisualChangeCanonStatus.canonized,
                "rollback_id": event.rollback_id or f"rollback:{event.event_id}",
                "updated_at": utc_now_iso(),
                "metadata": {**event.metadata, "approved_note": request.reviewer_note},
            }
        )
        self._events[event_id] = updated
        record = self._records.get(event.capture_id or "")
        if record is not None and event.changed_trait != "rejected_trait":
            self._write_visual_memory_artifact(
                record,
                None,
                event.feedback_action or VisualFeedbackAction.make_canon,
                updated.canon_status.value,
                event=updated,
            )
        self._write_events()
        return VisualChangeReviewResponse(event=updated, visual_identity=visual)

    def reject_visual_change(
        self, event_id: str, request: VisualChangeReviewRequest
    ) -> VisualChangeReviewResponse:
        event = self._require_event(event_id, request.character_id)
        updated = event.model_copy(
            update={
                "canon_status": VisualChangeCanonStatus.rejected,
                "updated_at": utc_now_iso(),
                "metadata": {**event.metadata, "rejected_note": request.reviewer_note},
            }
        )
        self._events[event_id] = updated
        self._write_events()
        return VisualChangeReviewResponse(event=updated)

    def rollback_visual_change(
        self, event_id: str, request: VisualChangeReviewRequest
    ) -> VisualChangeReviewResponse:
        event = self._require_event(event_id, request.character_id)
        if (
            event.canon_status != VisualChangeCanonStatus.canonized
            or not event.rollback_available
        ):
            raise ValueError(
                "Only canonized changes with rollback metadata can be rolled back."
            )
        rollback_event = event.model_copy(
            update={
                "event_id": f"rollback_{uuid4().hex}",
                "previous_value": event.new_value,
                "new_value": event.previous_value or "",
                "reason": f"Rollback of {event.event_id}",
                "canon_status": VisualChangeCanonStatus.rolled_back,
                "rollback_id": event.event_id,
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
                "metadata": {**event.metadata, "rollback_note": request.reviewer_note},
            }
        )
        visual = self._character_service.update_visual_identity(
            event.character_id,
            {
                "evolving_trait": {
                    "name": event.changed_trait,
                    "value": event.previous_value or "",
                    "provenance": f"rollback:{event.event_id}",
                }
            },
        )
        self._events[event_id] = event.model_copy(
            update={
                "canon_status": VisualChangeCanonStatus.rolled_back,
                "updated_at": utc_now_iso(),
            }
        )
        self._events[rollback_event.event_id] = VisualChangeEvent.model_validate(
            rollback_event
        )
        self._write_events()
        return VisualChangeReviewResponse(
            event=self._events[rollback_event.event_id], visual_identity=visual
        )

    def _write_visual_memory_artifact(
        self,
        record: MomentCaptureRecord,
        request: VisualFeedbackRequest | None,
        action: VisualFeedbackAction,
        review_state: str,
        *,
        event: VisualChangeEvent | None = None,
    ) -> MomentCaptureRecord:
        if not record.character_id:
            raise ValueError("Visual memory writeback requires character_id.")
        metadata = request.metadata if request is not None else {}
        memory_scope = str(metadata.get("memory_scope") or "character_private")
        if memory_scope not in {"character_private", "shared", "global"}:
            raise ValueError(
                "memory_scope must be character_private, shared, or global."
            )
        if memory_scope == "character_private" and not record.character_id:
            raise ValueError("Character-private visual memory requires character_id.")
        if metadata.get("private") is True or metadata.get("write_memory") is False:
            return record
        summary = self._visual_memory_summary(record, request, action, event)
        provenance = {
            "capture_id": record.capture_id,
            "image_job_id": record.image_job_id,
            "visual_change_event_id": event.event_id if event else None,
            "prompt_hash": record.prompt_hash,
        }
        base_memory_metadata = {
            "memory_scope": memory_scope,
            "memory_type": "visual_memory",
            "source": "visual_feedback",
            "capture_id": record.capture_id,
            "image_job_id": record.image_job_id,
            "feedback_action": action.value,
            "review_state": review_state,
            "provenance": provenance,
            "rollback_id": (event.rollback_id if event else record.rollback_id),
            "training_eligible": False,
            "training_eligibility": "not_eligible",
            "training_policy": "disabled_without_explicit_collection_policy",
            "tags": ["visual_memory", action.value],
        }
        memory_metadata = (
            character_private_metadata(record.character_id, base_memory_metadata)
            if memory_scope == "character_private"
            else {**base_memory_metadata, "character_id": record.character_id}
        )
        try:
            memory = self._memory_manager.add_memory(summary, memory_metadata)
        except MemoryError as exc:
            metadata = dict(record.metadata)
            metadata["visual_memory_writeback"] = {
                "state": "quarantined",
                "reason": str(exc),
                "character_id": record.character_id,
                "memory_scope": memory_scope,
                "capture_id": record.capture_id,
            }
            updated = record.model_copy(
                update={"metadata": metadata, "updated_at": utc_now_iso()}
            )
            self._records[record.capture_id] = updated
            return updated
        artifact = VisualMemoryArtifact(
            artifact_id=f"vma_{uuid4().hex}",
            artifact_type="memory",
            path=None,
            memory_id=memory["id"],
            training_candidate=False,
            metadata={
                "character_id": record.character_id,
                "memory_scope": memory_scope,
                "capture_id": record.capture_id,
                "image_job_id": record.image_job_id,
                "feedback_action": action.value,
                "review_state": review_state,
                "source": "visual_feedback",
                "provenance": provenance,
                "rollback_id": event.rollback_id if event else record.rollback_id,
                "training_candidate": False,
                "training_eligible": False,
                "training_eligibility": "not_eligible",
                "training_policy": "disabled_without_explicit_collection_policy",
            },
        )
        artifacts = [*record.visual_memory_artifacts, artifact]
        updated = record.model_copy(
            update={"visual_memory_artifacts": artifacts, "updated_at": utc_now_iso()}
        )
        self._records[record.capture_id] = updated
        if metadata.get("create_journal") is True:
            self._reflection_manager.save_journal_entry(
                {
                    "entry_id": f"journal_visual_{uuid4().hex}",
                    "created_at": utc_now_iso(),
                    "status": "active",
                    "conversation_window": {"capture_id": record.capture_id},
                    "linked_memory_ids": [memory["id"]],
                    "linked_journal_ids": [],
                    "character_summary": summary,
                    "structured_summary": {
                        "visual_memory": artifact.model_dump(mode="json")
                    },
                    "insights": [],
                    "emotional_valence": 0.0,
                    "emotional_intensity": 0.0,
                    "themes": ["visual_continuity"],
                    "confidence": 0.8,
                    "evidence_count": 1,
                    "privacy_tags": ["local", "visual_feedback"],
                    "sensitivity_tags": [],
                    "training_eligibility": "not_eligible",
                    "rollback_id": (
                        event.rollback_id
                        if event
                        else record.rollback_id or f"rollback:{record.capture_id}"
                    ),
                    "growth_notification": None,
                    "metadata": artifact.metadata,
                }
            )
        return updated

    def _visual_memory_summary(
        self,
        record: MomentCaptureRecord,
        request: VisualFeedbackRequest | None,
        action: VisualFeedbackAction,
        event: VisualChangeEvent | None,
    ) -> str:
        pieces = [f"Approved visual feedback for this character: {action.value}."]
        if event is not None:
            pieces.append(
                f"Visual trait '{event.changed_trait}' was approved as '{event.new_value}'."
            )
        elif request and request.note:
            pieces.append(str(request.note))
        elif record.scene_state.outfit:
            pieces.append(f"Outfit detail: {record.scene_state.outfit}.")
        if record.scene_state.location:
            pieces.append(f"Scene context: {record.scene_state.location}.")
        return " ".join(pieces)[:1000]

    @staticmethod
    def _default_records_path(settings: Settings) -> Path:
        return Path(settings.image_generation_history_path).with_name(
            "moment_captures.json"
        )

    def _creator_capture_metadata(
        self, request: MomentCaptureRequest
    ) -> dict[str, Any]:
        return {
            key: value
            for key, value in request.metadata.items()
            if key in {"source_context", "creator_draft", "draft_id", "non_blocking"}
        }

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
                "moment_capture_id": capture_id,
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
                **self._creator_capture_metadata(request),
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

    def _load_events(self) -> dict[str, VisualChangeEvent]:
        if not self._events_path.exists():
            return {}
        data = json.loads(self._events_path.read_text(encoding="utf-8"))
        return {
            item["event_id"]: VisualChangeEvent.model_validate(item)
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

    def _require_record(self, capture_id: str) -> MomentCaptureRecord:
        record = self.get_record(capture_id)
        if record is None:
            raise KeyError(capture_id)
        return record

    def _require_event(self, event_id: str, character_id: str) -> VisualChangeEvent:
        event = self.get_visual_change(event_id)
        if event is None:
            raise KeyError(event_id)
        if event.character_id != character_id:
            raise ValueError("Visual change character_id mismatch.")
        return event

    def _canonical_action(self, action: VisualFeedbackAction) -> VisualFeedbackAction:
        if action == VisualFeedbackAction.scene_only:
            return VisualFeedbackAction.just_this_scene
        if action == VisualFeedbackAction.never_use_trait:
            return VisualFeedbackAction.reject_style_trait
        return action

    def _visual_identity_for_record(self, record: MomentCaptureRecord):
        transient = self._transient_blueprints.get(record.character_id)
        if transient is not None:
            return transient.visual_identity
        return self._character_service.get_visual_identity(record.character_id)

    def _build_event(
        self,
        record: MomentCaptureRecord,
        request: VisualFeedbackRequest,
        action: VisualFeedbackAction,
        default_trait: str,
    ) -> VisualChangeEvent:
        trait_name = request.trait_name or default_trait
        new_value = (
            request.trait_value
            or request.note
            or record.scene_state.outfit
            or action.value
        )
        current = self._visual_identity_for_record(record)
        previous = None
        if trait_name == "current_appearance":
            previous = current.current_appearance
        else:
            for trait in current.evolving_traits:
                if trait.name == trait_name:
                    previous = trait.value
                    break
        return VisualChangeEvent(
            event_id=f"vce_{uuid4().hex}",
            character_id=record.character_id,
            capture_id=record.capture_id,
            changed_trait=trait_name,
            previous_value=previous,
            new_value=new_value,
            reason=request.note
            or f"User selected {action.value} for a Moment Capture image.",
            feedback_action=action,
            canon_status=VisualChangeCanonStatus.proposed,
            rollback_id=f"rollback:{record.capture_id}:{trait_name}",
            metadata={
                "source_image_ref": request.source_image_ref
                or (record.output_paths[0] if record.output_paths else None),
                "image_job_id": record.image_job_id,
                "prompt_hash": record.prompt_hash,
                **request.metadata,
            },
        )
