"""Versioned data contracts for Moment Capture and visual continuity.

These schemas are intentionally storage-agnostic and local-first. They describe
what a capture request/record means, not how images are generated or persisted.
Deletion behavior: deleting a record should tombstone gallery metadata first and
then remove local image files only after callers have confirmed no training,
memory, or rollback references still need them. Rollback behavior: canon-changing
visual events must keep enough previous/new value metadata to reverse the
change without mutating ``VisualIdentityProfile`` silently.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.image import ImageHistoryItem, ImageQualityPreset
from app.schemas.relationship_state import RelationshipPhase, RelationshipState
from app.schemas.visual_identity import VisualIdentityProfile

MOMENT_CAPTURE_SCHEMA_VERSION: Literal["moment_capture.v1"] = "moment_capture.v1"
SCENE_STATE_SCHEMA_VERSION: Literal["scene_state.v1"] = "scene_state.v1"
VISUAL_CHANGE_EVENT_SCHEMA_VERSION: Literal["visual_change_event.v1"] = (
    "visual_change_event.v1"
)
VISUAL_MEMORY_ARTIFACT_SCHEMA_VERSION: Literal["visual_memory_artifact.v1"] = (
    "visual_memory_artifact.v1"
)

MAX_SHORT_TEXT = 240
MAX_MEDIUM_TEXT = 1000
MAX_TAGS = 24


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _compact_text(value: str, *, max_length: int = MAX_SHORT_TEXT) -> str:
    normalized = " ".join(str(value).strip().split())
    if not normalized:
        raise ValueError("Text fields cannot be empty.")
    return normalized[:max_length]


def stable_prompt_hash(*parts: Any) -> str:
    """Return a stable short hash for prompt-derived metadata, not raw prompts."""

    digest = hashlib.sha256(repr(parts).encode("utf-8")).hexdigest()
    return digest[:16]


class FeedbackState(StrEnum):
    pending = "pending"
    looks_right = "looks_right"
    wrong_appearance = "wrong_appearance"
    favorite = "favorite"
    rejected = "rejected"
    deleted = "deleted"


class ReviewState(StrEnum):
    unreviewed = "unreviewed"
    accepted = "accepted"
    needs_changes = "needs_changes"
    canon_requested = "canon_requested"
    canonized = "canonized"
    rolled_back = "rolled_back"
    deleted = "deleted"


class VisualFeedbackAction(StrEnum):
    """User-review actions stored as metadata; services decide side effects."""

    looks_right = "looks_right"
    wrong_appearance = "wrong_appearance"
    make_canon = "make_canon"
    use_outfit_again = "use_outfit_again"
    scene_only = "scene_only"
    never_use_trait = "never_use_trait"
    favorite = "favorite"
    delete = "delete"
    rollback = "rollback"


class VisualChangeCanonStatus(StrEnum):
    proposed = "proposed"
    approved = "approved"
    canonized = "canonized"
    rolled_back = "rolled_back"
    rejected = "rejected"


class SceneState(BaseModel):
    """Compact visual-continuity context extracted from a chat moment.

    Keep this focused on things an image prompt/reviewer needs: who is present,
    visible appearance, mood, setting, props, and explicit anti-drift notes.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["scene_state.v1"] = SCENE_STATE_SCHEMA_VERSION
    location: str | None = Field(default=None, max_length=MAX_SHORT_TEXT)
    time_of_day: str | None = Field(default=None, max_length=80)
    mood: str | None = Field(default=None, max_length=MAX_SHORT_TEXT)
    emotional_tone: str | None = Field(default=None, max_length=MAX_SHORT_TEXT)
    character_appearance: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    pose: str | None = Field(default=None, max_length=120)
    outfit: str | None = Field(default=None, max_length=MAX_SHORT_TEXT)
    key_objects: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    background_details: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    continuity_notes: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    wrong_appearance: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "character_appearance",
        "key_objects",
        "background_details",
        "continuity_notes",
        "wrong_appearance",
        mode="after",
    )
    @classmethod
    def normalize_lists(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = _compact_text(value, max_length=120)
            if item not in normalized:
                normalized.append(item)
        return normalized

    @field_validator(
        "location", "time_of_day", "mood", "emotional_tone", "pose", "outfit"
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _compact_text(value) if value is not None else value


class VisualMemoryArtifact(BaseModel):
    """Optional link from a capture to future memory or training artifacts.

    This model is intentionally a pointer, not a storage layer. Deleting a
    ``MomentCaptureRecord`` should not blindly delete linked memories or
    training candidates; callers should first inspect these references and
    either tombstone, detach, or explicitly remove each downstream artifact.
    """

    schema_version: Literal["visual_memory_artifact.v1"] = (
        VISUAL_MEMORY_ARTIFACT_SCHEMA_VERSION
    )
    artifact_id: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Stable local identifier for the linked memory/training artifact.",
    )
    artifact_type: str = Field(
        default="moment_capture",
        min_length=1,
        max_length=80,
        description="Small type tag such as moment_capture, thumbnail, memory, or training_candidate.",
    )
    path: str | None = Field(
        default=None,
        max_length=500,
        description="Optional local path or asset URL; never implies ownership for deletion by itself.",
    )
    memory_id: str | None = Field(
        default=None,
        max_length=120,
        description="Optional memory-store identifier when this capture is promoted to visual memory.",
    )
    training_candidate: bool = Field(
        default=False,
        description="Marks whether this artifact may be offered to later opt-in training review.",
    )
    created_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Optional implementation-specific notes for this artifact link; "
            "not a replacement for structured artifact fields."
        ),
    )


class MomentCaptureRequest(BaseModel):
    """Typed request shape M5-P03 can pass to the image service boundary."""

    schema_version: Literal["moment_capture.v1"] = MOMENT_CAPTURE_SCHEMA_VERSION
    character_id: str = Field(..., min_length=1, max_length=120)
    conversation_id: str = Field(..., min_length=1, max_length=120)
    session_id: str = Field(..., min_length=1, max_length=120)
    source_message_id: str = Field(..., min_length=1, max_length=120)
    source_turn_index: int = Field(..., ge=0)
    scene_state: SceneState
    relationship_phase_snapshot: RelationshipPhase | str
    visual_identity_snapshot: VisualIdentityProfile
    visual_identity_version: str = Field(..., min_length=1, max_length=80)
    visual_identity_updated_at: str = Field(..., min_length=1, max_length=80)
    prompt_hash: str = Field(..., min_length=8, max_length=80)
    quality_preset: ImageQualityPreset = ImageQualityPreset.preview_8gb
    relevant_visual_memories: list[VisualMemoryArtifact] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_chat_turn(
        cls,
        *,
        character_id: str,
        conversation_id: str,
        session_id: str,
        source_message_id: str,
        source_turn_index: int,
        scene_state: SceneState,
        visual_identity: VisualIdentityProfile,
        relationship_state: RelationshipState | None = None,
        prompt_hash: str | None = None,
        **kwargs: Any,
    ) -> "MomentCaptureRequest":
        phase = (
            relationship_state.phase
            if relationship_state
            else RelationshipPhase.newly_met
        )
        return cls(
            character_id=character_id,
            conversation_id=conversation_id,
            session_id=session_id,
            source_message_id=source_message_id,
            source_turn_index=source_turn_index,
            scene_state=scene_state,
            relationship_phase_snapshot=phase,
            visual_identity_snapshot=visual_identity,
            visual_identity_version=visual_identity.schema_version,
            visual_identity_updated_at=visual_identity.updated_at,
            prompt_hash=prompt_hash
            or stable_prompt_hash(
                character_id,
                scene_state.model_dump(mode="json"),
                visual_identity.updated_at,
            ),
            **kwargs,
        )


_ALLOWED_REVIEW_TRANSITIONS: dict[ReviewState, set[ReviewState]] = {
    ReviewState.unreviewed: {
        ReviewState.accepted,
        ReviewState.needs_changes,
        ReviewState.canon_requested,
        ReviewState.deleted,
    },
    ReviewState.accepted: {ReviewState.canon_requested, ReviewState.deleted},
    ReviewState.needs_changes: {ReviewState.accepted, ReviewState.deleted},
    ReviewState.canon_requested: {
        ReviewState.canonized,
        ReviewState.rolled_back,
        ReviewState.deleted,
    },
    ReviewState.canonized: {ReviewState.rolled_back, ReviewState.deleted},
    ReviewState.rolled_back: {ReviewState.deleted},
    ReviewState.deleted: set(),
}


class MomentCaptureRecord(BaseModel):
    """Durable reviewed capture metadata for gallery, memory, and rollback.

    Deletion is a two-step semantic operation: first transition
    ``review_state``/``feedback_state`` to ``deleted`` so gallery, memory, and
    training queues stop treating the record as active; only then may a storage
    service decide whether local files in ``output_paths`` are safe to remove.
    Linked ``visual_memory_artifacts`` must be inspected separately; deleting a
    record must not automatically delete, detach, or tombstone those artifacts.

    ``rollback_id`` is a pointer to a reversible visual change, usually a
    ``VisualChangeEvent.event_id`` or application-defined rollback receipt. It
    is not a delete marker and should never silently mutate
    ``VisualIdentityProfile``. Rollback services should use it to locate the
    prior canon value and create an explicit rolled-back change event. Linked
    ``visual_memory_artifacts`` generally remain attached during rollback unless
    a caller explicitly cleans them up.
    """

    schema_version: Literal["moment_capture.v1"] = MOMENT_CAPTURE_SCHEMA_VERSION
    capture_id: str = Field(..., min_length=1, max_length=120)
    character_id: str = Field(..., min_length=1, max_length=120)
    conversation_id: str = Field(..., min_length=1, max_length=120)
    session_id: str = Field(..., min_length=1, max_length=120)
    source_message_id: str = Field(..., min_length=1, max_length=120)
    source_turn_index: int = Field(..., ge=0)
    scene_state: SceneState
    relationship_phase_snapshot: RelationshipPhase | str
    visual_identity_version: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="Schema/version label of the VisualIdentityProfile snapshot used for this capture.",
    )
    visual_identity_updated_at: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="Timestamp from the visual identity snapshot so reviewers can detect stale captures.",
    )
    prompt_hash: str = Field(
        ...,
        min_length=8,
        max_length=80,
        description="Stable hash of prompt-relevant inputs; avoids storing raw prompt text on the main record.",
    )
    image_job_id: str = Field(..., min_length=1, max_length=120)
    output_paths: list[str] = Field(..., min_length=1)
    feedback_state: FeedbackState = Field(
        default=FeedbackState.pending,
        description="Latest lightweight user feedback outcome for gallery filtering and future writeback decisions.",
    )
    review_state: ReviewState = Field(
        default=ReviewState.unreviewed,
        description="Explicit review lifecycle state; services must validate transitions before canon writeback.",
    )
    review_transition_from: ReviewState | None = Field(
        default=None,
        description="Previous review state used to validate a proposed transition on model construction.",
    )
    feedback_actions: list[VisualFeedbackAction] = Field(default_factory=list)
    visual_memory_artifacts: list[VisualMemoryArtifact] = Field(
        default_factory=list,
        description=(
            "Optional linked visual memory/training artifacts; deletion and rollback "
            "callers must inspect these references and decide whether to tombstone, "
            "detach, keep, or explicitly remove them."
        ),
    )
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    rollback_id: str | None = Field(
        default=None,
        max_length=120,
        description="Pointer to the VisualChangeEvent or rollback receipt that can reverse a canonized visual change.",
    )
    legacy_image_history: dict[str, Any] = Field(
        default_factory=dict,
        description="Lossless copy of a normalized legacy ImageHistoryItem for safe migration/audit.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Non-canonical service metadata; do not place raw prompt text here unless explicitly needed.",
    )

    @field_validator("output_paths")
    @classmethod
    def output_paths_not_blank(cls, values: list[str]) -> list[str]:
        return [_compact_text(value, max_length=500) for value in values]

    @model_validator(mode="after")
    def validate_review_transition(self) -> "MomentCaptureRecord":
        if self.review_transition_from is not None:
            allowed = _ALLOWED_REVIEW_TRANSITIONS[self.review_transition_from]
            if (
                self.review_state not in allowed
                and self.review_state != self.review_transition_from
            ):
                raise ValueError(
                    f"Invalid review transition: {self.review_transition_from} -> {self.review_state}"
                )
        if (
            self.review_state == ReviewState.deleted
            and self.feedback_state != FeedbackState.deleted
        ):
            self.feedback_state = FeedbackState.deleted
        return self

    def transition_review(self, new_state: ReviewState) -> "MomentCaptureRecord":
        return MomentCaptureRecord.model_validate(
            {
                **self.model_dump(),
                "review_transition_from": self.review_state,
                "review_state": new_state,
                "updated_at": utc_now_iso(),
            }
        )

    @classmethod
    def normalize_image_history(
        cls,
        item: ImageHistoryItem | dict[str, Any],
        *,
        character_id: str = "default",
        session_id: str | None = None,
        source_turn_index: int = 0,
        scene_state: SceneState | None = None,
        relationship_phase_snapshot: (
            RelationshipPhase | str
        ) = RelationshipPhase.newly_met,
        visual_identity_version: str = "legacy_image_history",
        visual_identity_updated_at: str | None = None,
    ) -> "MomentCaptureRecord":
        history = (
            item
            if isinstance(item, ImageHistoryItem)
            else ImageHistoryItem.model_validate(item)
        )
        metadata = dict(history.metadata)
        return cls(
            capture_id=f"legacy-{history.job_id}",
            character_id=str(metadata.get("character_id") or character_id),
            conversation_id=history.conversation_id,
            session_id=session_id
            or str(metadata.get("session_id") or history.conversation_id),
            source_message_id=history.source_message_id or history.job_id,
            source_turn_index=int(
                metadata.get("source_turn_index") or source_turn_index
            ),
            scene_state=scene_state
            or SceneState(metadata={"legacy_source": history.source}),
            relationship_phase_snapshot=metadata.get("relationship_phase_snapshot")
            or relationship_phase_snapshot,
            visual_identity_version=str(
                metadata.get("visual_identity_version") or visual_identity_version
            ),
            visual_identity_updated_at=str(
                metadata.get("visual_identity_updated_at")
                or visual_identity_updated_at
                or history.created_at.isoformat()
            ),
            prompt_hash=str(
                metadata.get("prompt_hash")
                or stable_prompt_hash(history.prompt_summary, history.job_id)
            ),
            image_job_id=history.job_id,
            output_paths=list(history.output_paths),
            created_at=history.created_at.isoformat(),
            updated_at=history.completed_at.isoformat(),
            legacy_image_history=history.model_dump(mode="json"),
            metadata={
                "normalized_from": "ImageHistoryItem",
                "prompt_summary": history.prompt_summary,
                **metadata,
            },
        )


class VisualChangeEvent(BaseModel):
    """Reversible visual canon/change event linked to a reviewed capture.

    This event records what changed, why it changed, and whether it became
    canon. It is the audit trail for user-confirmed visual updates; constructing
    one should not itself mutate ``VisualIdentityProfile``. For rollback, create
    a new event with ``canon_status='rolled_back'`` and ``rollback_id`` pointing
    at the event being reversed (or at an application-defined rollback receipt).
    Deleting a capture should not delete change events automatically because
    canon history may still need the audit trail.
    """

    schema_version: Literal["visual_change_event.v1"] = (
        VISUAL_CHANGE_EVENT_SCHEMA_VERSION
    )
    event_id: str = Field(..., min_length=1, max_length=120)
    character_id: str = Field(..., min_length=1, max_length=120)
    capture_id: str | None = Field(default=None, max_length=120)
    changed_trait: str = Field(..., min_length=1, max_length=120)
    previous_value: str | None = Field(
        default=None,
        max_length=MAX_MEDIUM_TEXT,
        description="Prior canon/scene value; required for automated rollback availability.",
    )
    new_value: str = Field(
        ...,
        min_length=1,
        max_length=MAX_MEDIUM_TEXT,
        description="Proposed or accepted visual value after user feedback/review.",
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=MAX_MEDIUM_TEXT,
        description="Human-readable reason/provenance for the visual change.",
    )
    feedback_action: VisualFeedbackAction | None = None
    canon_status: VisualChangeCanonStatus = VisualChangeCanonStatus.proposed
    rollback_id: str | None = Field(
        default=None,
        max_length=120,
        description="Identifier of the event/receipt this event rolls back, or a receipt to use for future rollback.",
    )
    rollback_available: bool = Field(
        default=True,
        description="False when the event lacks enough previous-value data for an automated rollback.",
    )
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_rollback_metadata(self) -> "VisualChangeEvent":
        if (
            self.canon_status == VisualChangeCanonStatus.rolled_back
            and not self.rollback_id
        ):
            raise ValueError("Rolled-back visual changes require rollback_id.")
        if self.previous_value is None:
            self.rollback_available = False
        return self
