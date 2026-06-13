"""Versioned local-first contracts for Moment Capture and visual continuity.

These schemas intentionally do not submit image jobs or write to visual canon.
Moment Capture records are durable gallery/history metadata: deleting a record
should remove only the record and caller-owned output files. Any canon or memory
artifact linked by id must be deleted/rolled back by its owning subsystem.
Rollback is represented by ``rollback_id``/``rolled_back_by_event_id`` links so
future services can reverse visual changes without inventing new metadata.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.image import ImageHistoryItem, ImageQualityPreset
from app.schemas.relationship_state import RelationshipPhase

MOMENT_CAPTURE_SCHEMA_VERSION: Literal["moment_capture.v1"] = "moment_capture.v1"
SCENE_STATE_SCHEMA_VERSION: Literal["scene_state.v1"] = "scene_state.v1"
VISUAL_CHANGE_EVENT_SCHEMA_VERSION: Literal["visual_change_event.v1"] = (
    "visual_change_event.v1"
)
VISUAL_MEMORY_ARTIFACT_SCHEMA_VERSION: Literal["visual_memory_artifact.v1"] = (
    "visual_memory_artifact.v1"
)

MAX_TEXT = 480
MAX_ITEMS = 24


def utc_now() -> datetime:
    return datetime.now(UTC)


class MomentReviewState(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    archived = "archived"
    deleted = "deleted"


class VisualFeedbackState(StrEnum):
    none = "none"
    liked = "liked"
    disliked = "disliked"
    correction_requested = "correction_requested"
    canon_candidate = "canon_candidate"
    canonized = "canonized"
    rolled_back = "rolled_back"


class VisualFeedbackActionType(StrEnum):
    like = "like"
    dislike = "dislike"
    request_correction = "request_correction"
    mark_canon_candidate = "mark_canon_candidate"
    canonize = "canonize"
    rollback = "rollback"


class VisualCanonStatus(StrEnum):
    proposed = "proposed"
    canon_candidate = "canon_candidate"
    canonized = "canonized"
    rejected = "rejected"
    rolled_back = "rolled_back"


class SceneState(BaseModel):
    """Prompt-safe scene context needed for visual continuity only."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["scene_state.v1"] = SCENE_STATE_SCHEMA_VERSION
    location: str | None = Field(default=None, max_length=160)
    time_of_day: str | None = Field(default=None, max_length=80)
    mood: str | None = Field(default=None, max_length=120)
    emotional_tone: str | None = Field(default=None, max_length=120)
    character_appearance: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    expression: str | None = Field(default=None, max_length=80)
    pose: str | None = Field(default=None, max_length=80)
    outfit: str | None = Field(default=None, max_length=240)
    key_objects: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    nearby_characters: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    lighting: str | None = Field(default=None, max_length=160)
    camera_framing: str | None = Field(default=None, max_length=160)
    continuity_notes: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    wrong_appearance: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)

    @field_validator(
        "character_appearance",
        "key_objects",
        "nearby_characters",
        "continuity_notes",
        "wrong_appearance",
        mode="after",
    )
    @classmethod
    def normalize_text_list(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = " ".join(str(value).strip().split())[:160]
            if item and item not in normalized:
                normalized.append(item)
        return normalized


class VisualMemoryArtifact(BaseModel):
    """Future link to memory/journal entries created from a reviewed image."""

    schema_version: Literal["visual_memory_artifact.v1"] = (
        VISUAL_MEMORY_ARTIFACT_SCHEMA_VERSION
    )
    artifact_id: str = Field(default_factory=lambda: f"vma_{uuid4().hex}")
    memory_id: str | None = Field(default=None, max_length=120)
    journal_id: str | None = Field(default=None, max_length=120)
    character_id: str = Field(..., min_length=1, max_length=120)
    source_record_id: str = Field(..., min_length=1, max_length=120)
    created_at: datetime = Field(default_factory=utc_now)
    deleted_at: datetime | None = None
    rollback_id: str | None = Field(default=None, max_length=120)


class MomentCaptureRequest(BaseModel):
    """Request contract M5-P03 can consume before delegating to image generation."""

    schema_version: Literal["moment_capture.v1"] = MOMENT_CAPTURE_SCHEMA_VERSION
    character_id: str = Field(..., min_length=1, max_length=120)
    conversation_id: str = Field(..., min_length=1, max_length=120)
    session_id: str | None = Field(default=None, max_length=120)
    source_message_id: str = Field(..., min_length=1, max_length=120)
    source_turn_index: int = Field(..., ge=0)
    scene_state: SceneState
    relationship_phase_snapshot: RelationshipPhase | str
    visual_identity_version: str | None = Field(default=None, max_length=120)
    visual_identity_updated_at: datetime | str | None = None
    visual_identity_snapshot: dict[str, Any] = Field(default_factory=dict)
    user_instruction: str | None = Field(default=None, max_length=MAX_TEXT)
    quality_preset: ImageQualityPreset = ImageQualityPreset.preview_8gb
    relevant_visual_memories: list[VisualMemoryArtifact] = Field(
        default_factory=list, max_length=MAX_ITEMS
    )
    created_at: datetime = Field(default_factory=utc_now)


class VisualFeedbackAction(BaseModel):
    """Explicit user/reviewer action; services apply it to record state."""

    action_id: str = Field(default_factory=lambda: f"vfa_{uuid4().hex}")
    action: VisualFeedbackActionType
    from_state: VisualFeedbackState = VisualFeedbackState.none
    to_state: VisualFeedbackState
    reason: str | None = Field(default=None, max_length=MAX_TEXT)
    reviewer_id: str = Field(default="local_user", min_length=1, max_length=120)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_transition(self) -> "VisualFeedbackAction":
        allowed = {
            VisualFeedbackActionType.like: {VisualFeedbackState.liked},
            VisualFeedbackActionType.dislike: {VisualFeedbackState.disliked},
            VisualFeedbackActionType.request_correction: {
                VisualFeedbackState.correction_requested
            },
            VisualFeedbackActionType.mark_canon_candidate: {
                VisualFeedbackState.canon_candidate
            },
            VisualFeedbackActionType.canonize: {VisualFeedbackState.canonized},
            VisualFeedbackActionType.rollback: {VisualFeedbackState.rolled_back},
        }
        if self.to_state not in allowed[self.action]:
            raise ValueError(
                f"{self.action.value} cannot transition to {self.to_state.value}"
            )
        if (
            self.from_state == VisualFeedbackState.rolled_back
            and self.action != VisualFeedbackActionType.rollback
        ):
            raise ValueError(
                "Rolled-back feedback cannot be advanced without a new record."
            )
        return self


class VisualChangeEvent(BaseModel):
    """Reversible visual-change ledger entry; it does not mutate canon by itself."""

    schema_version: Literal["visual_change_event.v1"] = (
        VISUAL_CHANGE_EVENT_SCHEMA_VERSION
    )
    event_id: str = Field(default_factory=lambda: f"vce_{uuid4().hex}")
    character_id: str = Field(..., min_length=1, max_length=120)
    source_record_id: str = Field(..., min_length=1, max_length=120)
    changed_trait: str = Field(..., min_length=1, max_length=120)
    previous_value: str | None = Field(default=None, max_length=MAX_TEXT)
    new_value: str | None = Field(default=None, max_length=MAX_TEXT)
    reason: str = Field(..., min_length=1, max_length=MAX_TEXT)
    user_reaction: VisualFeedbackState | None = None
    canon_status: VisualCanonStatus = VisualCanonStatus.proposed
    rollback_available: bool = True
    rollback_id: str | None = Field(default=None, max_length=120)
    rolled_back_by_event_id: str | None = Field(default=None, max_length=120)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_rollback_links(self) -> "VisualChangeEvent":
        if self.canon_status == VisualCanonStatus.rolled_back and not (
            self.rollback_id or self.rolled_back_by_event_id
        ):
            raise ValueError(
                "Rolled-back visual changes must reference a rollback id or event."
            )
        return self


class MomentCaptureRecord(BaseModel):
    """Durable capture/gallery record with traceability and rollback metadata.

    Deletion should tombstone or remove this record plus local output files only.
    Rollback should create/update VisualChangeEvent links and set ``rollback_id``;
    it must not silently edit ``VisualIdentityProfile`` or memory records.
    """

    schema_version: Literal["moment_capture.v1"] = MOMENT_CAPTURE_SCHEMA_VERSION
    record_id: str = Field(default_factory=lambda: f"mcr_{uuid4().hex}")
    character_id: str = Field(..., min_length=1, max_length=120)
    conversation_id: str = Field(..., min_length=1, max_length=120)
    session_id: str | None = Field(default=None, max_length=120)
    source_message_id: str = Field(..., min_length=1, max_length=120)
    source_turn_index: int = Field(..., ge=0)
    scene_state: SceneState
    relationship_phase_snapshot: RelationshipPhase | str
    visual_identity_version: str | None = Field(default=None, max_length=120)
    visual_identity_updated_at: datetime | str | None = None
    prompt_hash: str = Field(..., min_length=16, max_length=128)
    image_job_id: str = Field(..., min_length=1, max_length=120)
    output_paths: list[str] = Field(
        default_factory=list, min_length=1, max_length=MAX_ITEMS
    )
    thumbnail_paths: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    feedback_state: VisualFeedbackState = VisualFeedbackState.none
    review_state: MomentReviewState = MomentReviewState.pending
    feedback_actions: list[VisualFeedbackAction] = Field(
        default_factory=list, max_length=MAX_ITEMS
    )
    visual_change_events: list[VisualChangeEvent] = Field(
        default_factory=list, max_length=MAX_ITEMS
    )
    memory_artifacts: list[VisualMemoryArtifact] = Field(
        default_factory=list, max_length=MAX_ITEMS
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    rollback_id: str | None = Field(default=None, max_length=120)
    legacy_image_record: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_record_states(self) -> "MomentCaptureRecord":
        if self.review_state == MomentReviewState.deleted and not self.rollback_id:
            raise ValueError(
                "Deleted MomentCaptureRecord entries must carry a rollback_id/tombstone id."
            )
        if (
            self.feedback_state == VisualFeedbackState.rolled_back
            and not self.rollback_id
        ):
            raise ValueError(
                "Rolled-back MomentCaptureRecord entries must carry rollback_id."
            )
        return self

    @classmethod
    def normalize_legacy_image_history(
        cls,
        item: ImageHistoryItem | dict[str, Any],
        *,
        character_id: str = "default",
        source_turn_index: int = 0,
        scene_state: SceneState | None = None,
        relationship_phase_snapshot: (
            RelationshipPhase | str
        ) = RelationshipPhase.newly_met,
    ) -> "MomentCaptureRecord":
        """Safely wrap existing image history in the new shape without data loss."""

        history = (
            item
            if isinstance(item, ImageHistoryItem)
            else ImageHistoryItem.model_validate(item)
        )
        raw = history.model_dump(mode="json")
        metadata = dict(history.metadata or {})
        prompt_hash = str(
            metadata.get("prompt_hash")
            or sha256(history.prompt.encode("utf-8")).hexdigest()
        )
        return cls(
            record_id=f"legacy_{history.job_id}",
            character_id=str(metadata.get("character_id") or character_id),
            conversation_id=history.conversation_id,
            session_id=metadata.get("session_id"),
            source_message_id=history.source_message_id
            or str(metadata.get("source_message_id") or history.job_id),
            source_turn_index=int(metadata.get("source_turn_index", source_turn_index)),
            scene_state=scene_state
            or SceneState.model_validate(metadata.get("scene_state") or {}),
            relationship_phase_snapshot=metadata.get(
                "relationship_phase_snapshot", relationship_phase_snapshot
            ),
            visual_identity_version=metadata.get("visual_identity_version"),
            visual_identity_updated_at=metadata.get("visual_identity_updated_at"),
            prompt_hash=prompt_hash,
            image_job_id=history.job_id,
            output_paths=history.output_paths
            or [history.asset_manifest_path or f"legacy://{history.job_id}"],
            thumbnail_paths=history.thumbnail_paths,
            feedback_state=VisualFeedbackState(
                metadata.get("feedback_state", VisualFeedbackState.none)
            ),
            review_state=MomentReviewState(
                metadata.get("review_state", MomentReviewState.pending)
            ),
            created_at=history.created_at,
            updated_at=history.completed_at,
            rollback_id=metadata.get("rollback_id"),
            legacy_image_record=raw,
            metadata={"normalized_from": "ImageHistoryItem", **metadata},
        )
