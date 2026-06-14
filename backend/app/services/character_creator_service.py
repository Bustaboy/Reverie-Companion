"""Minimal runtime wiring for future M6 character creator flows.

This module intentionally does not persist drafts or save new characters. It maps
an in-flight creator draft into a valid ``CharacterBlueprint`` and can submit a
first-portrait Moment Capture through the existing non-blocking capture service.

Persistence/migration note: ``CharacterCreatorDraft`` is API-only for P00A. If
later milestones persist drafts, store the draft schema version alongside the
mapped blueprint ID and preserve ``metadata`` losslessly for forward migration.
Draft first-portrait captures add lightweight provenance fields to request,
record, image-job context, and follow-up visual-change events. The draft-capture
metadata contract intentionally uses a ``draft_`` prefix for draft-specific keys:
``draft_capture``, ``draft_id``, ``draft_character_id``,
``draft_source_context``, ``draft_capture_intent``, and
``draft_rollback_note``. Non-prefixed fields such as ``provenance``,
``evidence_only``, and ``canonical_mutation_allowed`` describe generic review and
rollback semantics shared with non-draft capture metadata.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.models.image import ImageQualityPreset
from app.schemas.character_blueprint import (
    AdultAgeRange,
    CharacterBlueprint,
    CharacterIdentity,
    CommunicationProfile,
    PersonalityProfile,
)
from app.schemas.moment_capture import (
    MomentCaptureRequest,
    SceneState,
    stable_prompt_hash,
)
from app.schemas.relationship_state import (
    DefaultIntimacyLevel,
    RelationshipPhase,
    RelationshipState,
)
from app.schemas.visual_identity import VisualIdentityProfile
from app.services.character_service import CharacterNotFoundError
from app.services.moment_capture_service import (
    MomentCaptureResponse,
    MomentCaptureService,
)


LOGGER = logging.getLogger(__name__)

# Draft capture metadata contract
# --------------------------------
# These keys are duplicated onto MomentCaptureRequest.metadata, SceneState.metadata,
# MomentCaptureRecord.metadata, image-job context, and VisualChangeEvent.metadata.
# Keeping the draft-specific keys under a consistent ``draft_`` prefix makes them
# cheap to filter in gallery/review views, keeps provenance visible while the
# CharacterBlueprint is still unsaved, and gives rollback/review flows enough
# context to avoid mutating canonical character data by accident.
DRAFT_CAPTURE_METADATA_KEYS: tuple[str, ...] = (
    "draft_capture",
    "draft_id",
    "draft_character_id",
    "draft_source_context",
    "draft_capture_intent",
    "draft_rollback_note",
    "provenance",
    "evidence_only",
    "canonical_mutation_allowed",
)


class DraftMomentSource(StrEnum):
    chat = "chat"
    visual_novel = "visual_novel"


class CharacterCreatorDraft(BaseModel):
    """API-only creator draft shape for basic M6 runtime validation."""

    draft_id: str | None = Field(default=None, max_length=120)
    character_id: str | None = Field(default=None, max_length=80)
    display_name: str = Field(..., min_length=1, max_length=80)
    pronouns: str = Field(default="she/her", min_length=1, max_length=40)
    adult_age_range: AdultAgeRange = AdultAgeRange.mid_20s_adult
    adult_only_confirmed: bool = True
    species_or_type: str = Field(default="human", min_length=1, max_length=80)
    relationship_dynamic: str = Field(
        default="warm, emotionally attentive companion", min_length=1, max_length=240
    )
    starting_relationship_phase: RelationshipPhase = RelationshipPhase.newly_met
    default_intimacy_level: DefaultIntimacyLevel = DefaultIntimacyLevel.romantic
    user_desired_experience: str | None = Field(default=None, max_length=240)
    core_traits: list[str] = Field(
        default_factory=lambda: ["warm", "curious", "emotionally attentive"],
        min_length=1,
        max_length=8,
    )
    communication_style: str | None = Field(default=None, max_length=240)
    visual_identity: VisualIdentityProfile = Field(
        default_factory=VisualIdentityProfile
    )
    tags: list[str] = Field(default_factory=list, max_length=12)
    creator_notes: str | None = Field(default=None, max_length=1200)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("character_id", "draft_id", mode="after")
    @classmethod
    def strip_optional_ids(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class DraftValidationResponse(BaseModel):
    valid: bool
    blueprint: CharacterBlueprint | None = None
    errors: list[str] = Field(default_factory=list)


class DraftMomentCaptureRequest(BaseModel):
    draft: CharacterCreatorDraft
    source: DraftMomentSource
    conversation_id: str = Field(default="creator-draft", min_length=1, max_length=120)
    session_id: str | None = Field(default=None, max_length=120)
    source_message_id: str | None = Field(default=None, max_length=120)
    source_turn_index: int = Field(default=0, ge=0)
    scene_state: SceneState | None = None
    capture_intent: str = Field(
        default="first portrait from creator draft", max_length=240
    )
    quality_preset: ImageQualityPreset = ImageQualityPreset.preview_8gb


class DraftCharacterService:
    """Read-only character service adapter for draft Moment Capture.

    It lets ``MomentCaptureService`` reuse its normal prompt, provenance, record,
    rollback, and queueing paths without requiring the draft to be saved first.
    """

    def __init__(self, blueprint: CharacterBlueprint) -> None:
        self._blueprint = blueprint

    def load_by_id(self, character_id: str) -> CharacterBlueprint:
        if character_id != self._blueprint.character_id:
            raise CharacterNotFoundError(character_id)
        return self._blueprint

    def get_visual_identity(self, character_id: str) -> VisualIdentityProfile:
        return self.load_by_id(character_id).visual_identity


class CharacterCreatorService:
    """Service boundary used by future creator UI/backend flows."""

    def __init__(
        self, moment_capture_service: MomentCaptureService | None = None
    ) -> None:
        self._moment_capture_service = moment_capture_service

    def draft_to_blueprint(self, draft: CharacterCreatorDraft) -> CharacterBlueprint:
        character_id = (
            draft.character_id or f"draft_{draft.draft_id or uuid4().hex[:12]}"
        )
        return CharacterBlueprint(
            character_id=character_id,
            identity=CharacterIdentity(
                display_name=draft.display_name,
                pronouns=draft.pronouns,
                adult_age_range=draft.adult_age_range,
                species_or_type=draft.species_or_type,
                tags=draft.tags,
                creator_notes=draft.creator_notes,
                adult_only_confirmed=draft.adult_only_confirmed,
            ),
            relationship=RelationshipState(
                character_id=character_id,
                starting_relationship_phase=draft.starting_relationship_phase,
                current_relationship_phase=draft.starting_relationship_phase,
                phase=draft.starting_relationship_phase,
                relationship_dynamic=draft.relationship_dynamic,
                default_intimacy_level=draft.default_intimacy_level,
                user_desired_experience=draft.user_desired_experience,
            ),
            personality=PersonalityProfile(core_traits=draft.core_traits),
            communication=CommunicationProfile(style_notes=draft.communication_style),
            visual_identity=draft.visual_identity,
            metadata={
                "creator_draft": {
                    "draft_id": draft.draft_id,
                    "source": "m6_p00a_runtime_draft",
                    "migration_note": (
                        "API-only draft; persist explicitly in a later draft "
                        "repository before save flows."
                    ),
                },
                **draft.metadata,
            },
        )

    def validate_draft(self, draft: CharacterCreatorDraft) -> DraftValidationResponse:
        try:
            blueprint = self.draft_to_blueprint(draft)
        except ValidationError as exc:
            return DraftValidationResponse(
                valid=False,
                errors=[
                    f"{'.'.join(str(p) for p in error['loc'])}: {error['msg']}"
                    for error in exc.errors()
                ],
            )
        except ValueError as exc:
            return DraftValidationResponse(valid=False, errors=[str(exc)])
        return DraftValidationResponse(valid=True, blueprint=blueprint)

    async def capture_first_portrait(
        self, request: DraftMomentCaptureRequest
    ) -> MomentCaptureResponse:
        blueprint = self.draft_to_blueprint(request.draft)
        scene_state = self._with_draft_scene_metadata(
            request.scene_state
            or self._default_scene_state(blueprint, source=request.source),
            source=request.source,
        )
        capture_request = MomentCaptureRequest.from_chat_turn(
            character_id=blueprint.character_id,
            conversation_id=request.conversation_id,
            session_id=(
                request.session_id
                or f"creator-{request.draft.draft_id or blueprint.character_id}"
            ),
            source_message_id=(
                request.source_message_id or f"creator-{request.source.value}-draft"
            ),
            source_turn_index=request.source_turn_index,
            scene_state=scene_state,
            visual_identity=blueprint.visual_identity,
            relationship_state=blueprint.relationship,
            prompt_hash=stable_prompt_hash(
                blueprint.character_id,
                request.source.value,
                scene_state.model_dump(mode="json"),
                blueprint.visual_identity.updated_at,
            ),
            quality_preset=request.quality_preset,
            metadata=self._draft_capture_metadata(
                request=request, character_id=blueprint.character_id
            ),
        )
        LOGGER.info(
            "Queued creator draft first-portrait Moment Capture",
            extra={
                "draft_capture": True,
                "draft_id": request.draft.draft_id,
                "character_id": blueprint.character_id,
                "draft_source_context": request.source.value,
            },
        )
        service = self._moment_capture_service
        draft_character_service = DraftCharacterService(blueprint)
        if service is None:
            service = MomentCaptureService(
                character_service=draft_character_service  # type: ignore[arg-type]
            )
        else:
            # Draft captures reuse the existing Moment Capture instance so follow-up
            # validation feedback in the same runtime can use the same VisualChange
            # and rollback paths before the draft is saved. No blueprint is persisted.
            service._character_service = draft_character_service  # type: ignore[attr-defined]
        return await service.capture(capture_request)

    def _default_scene_state(
        self, blueprint: CharacterBlueprint, *, source: DraftMomentSource
    ) -> SceneState:
        return SceneState(
            location=(
                "soft neutral portrait setting"
                if source == DraftMomentSource.chat
                else "visual novel character introduction scene"
            ),
            mood=blueprint.relationship.relationship_dynamic,
            emotional_tone=(
                blueprint.relationship.user_desired_experience
                or "warm first impression"
            ),
            character_appearance=blueprint.visual_identity.compact_prompt_summary(
                include_scene_mutable=True
            ),
            pose="front-facing first portrait",
            continuity_notes=[
                "first portrait validation",
                "creator draft capture",
                "evidence-only; does not mutate canonical character data",
                "draft image is not canon until reviewed",
            ],
            wrong_appearance=list(blueprint.visual_identity.rejected_traits),
            metadata={
                "source": source.value,
                "draft_capture": True,
                "draft_source_context": source.value,
                "draft_first_portrait": True,
                "draft_rollback_note": self._draft_capture_rollback_note(),
            },
        )

    def _with_draft_scene_metadata(
        self, scene_state: SceneState, *, source: DraftMomentSource
    ) -> SceneState:
        metadata = {
            **scene_state.metadata,
            "draft_capture": True,
            "draft_source_context": source.value,
            "draft_first_portrait": True,
            "draft_rollback_note": self._draft_capture_rollback_note(),
        }
        continuity_notes = list(scene_state.continuity_notes)
        for note in (
            "creator draft capture",
            "evidence-only; does not mutate canonical character data",
        ):
            if note not in continuity_notes:
                continuity_notes.append(note)
        return scene_state.model_copy(
            update={"metadata": metadata, "continuity_notes": continuity_notes}
        )

    def _draft_capture_metadata(
        self, *, request: DraftMomentCaptureRequest, character_id: str
    ) -> dict[str, Any]:
        """Return the standardized draft-capture metadata contract.

        Expected draft-triggered captures carry the ``draft_``-prefixed fields
        below on the ``MomentCaptureRequest`` and resulting ``MomentCaptureRecord``.
        ``SceneState.metadata`` carries the scene-relevant subset
        (``draft_capture``, ``draft_source_context``, ``draft_first_portrait``,
        and ``draft_rollback_note``). ``VisualChangeEvent.metadata`` copies the
        fields listed in ``DRAFT_CAPTURE_METADATA_KEYS`` so feedback, provenance,
        filtering, and rollback review can distinguish evidence-only draft images
        from canonical character captures without opening nested draft payloads.
        """

        return {
            "draft_capture": True,
            "draft_id": request.draft.draft_id,
            "draft_character_id": character_id,
            "draft_source_context": request.source.value,
            "draft_capture_intent": request.capture_intent,
            "draft_rollback_note": self._draft_capture_rollback_note(),
            "provenance": "character_creator_draft_first_portrait",
            "queue_policy": "non_blocking_preview_8gb",
            "evidence_only": True,
            "canonical_mutation_allowed": False,
        }

    @staticmethod
    def _draft_capture_rollback_note() -> str:
        return (
            "Creator draft capture is evidence-only for first-portrait review; "
            "it does not mutate canonical character data unless a later explicit "
            "review/canon approval flow applies changes."
        )
