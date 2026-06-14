"""Minimal runtime wiring for future M6 character creator flows.

This module intentionally does not persist drafts or save new characters. It maps
an in-flight creator draft into a valid ``CharacterBlueprint`` and can submit a
first-portrait Moment Capture through the existing non-blocking capture service.

Persistence/migration note: ``CharacterCreatorDraft`` is API-only for P00A. If
later milestones persist drafts, store the draft schema version alongside the
mapped blueprint ID and preserve ``metadata`` losslessly for forward migration.
Draft first-portrait captures add lightweight provenance fields to request,
record, image-job context, and follow-up visual-change events. Capture-specific
fields use the ``draft_`` prefix consistently: ``draft_capture``, ``draft_id``,
``draft_character_id``, ``draft_source_context``, ``draft_capture_intent``,
``draft_rollback_note``, ``draft_provenance``, ``draft_evidence_only``, and
``draft_canonical_mutation_allowed``. These fields identify creator-draft output
for filtering, explain provenance, and make rollback/review paths explicit before
the draft is saved as canonical character data.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from pathlib import Path
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
    utc_now_iso,
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


class DraftMomentSource(StrEnum):
    chat = "chat"
    visual_novel = "visual_novel"


class CreatorDraftStatus(StrEnum):
    draft = "draft"
    deleted = "deleted"


CREATOR_DRAFT_SCHEMA_VERSION = 1


class CharacterCreatorDraft(BaseModel):
    """Persistable creator draft shape for basic M6 runtime validation.

    Drafts are intentionally lifecycle-marked and stored in a separate draft table
    so they cannot be mistaken for finalized CharacterBlueprint records.
    """

    schema_version: int = Field(default=CREATOR_DRAFT_SCHEMA_VERSION, ge=1)
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
    status: CreatorDraftStatus = CreatorDraftStatus.draft
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    @field_validator("character_id", "draft_id", mode="after")
    @classmethod
    def strip_optional_ids(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CharacterCreatorDraftUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    pronouns: str | None = Field(default=None, min_length=1, max_length=40)
    adult_age_range: AdultAgeRange | None = None
    adult_only_confirmed: bool | None = None
    species_or_type: str | None = Field(default=None, min_length=1, max_length=80)
    relationship_dynamic: str | None = Field(default=None, min_length=1, max_length=240)
    starting_relationship_phase: RelationshipPhase | None = None
    default_intimacy_level: DefaultIntimacyLevel | None = None
    user_desired_experience: str | None = Field(default=None, max_length=240)
    core_traits: list[str] | None = Field(default=None, min_length=1, max_length=8)
    communication_style: str | None = Field(default=None, max_length=240)
    visual_identity: VisualIdentityProfile | None = None
    tags: list[str] | None = Field(default=None, max_length=12)
    creator_notes: str | None = Field(default=None, max_length=1200)
    metadata: dict[str, Any] | None = None


class CharacterCreatorDraftResponse(BaseModel):
    draft: CharacterCreatorDraft


class CharacterCreatorDraftListResponse(BaseModel):
    drafts: list[CharacterCreatorDraft]


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
        self,
        moment_capture_service: MomentCaptureService | None = None,
        draft_repository: Any | None = None,
        draft_db_path: str | Path | None = None,
    ) -> None:
        self._moment_capture_service = moment_capture_service
        if draft_repository is not None:
            self._draft_repository = draft_repository
        else:
            from app.repositories.character_creator_draft_repo import (
                CharacterCreatorDraftRepository,
            )

            self._draft_repository = CharacterCreatorDraftRepository(
                draft_db_path or "./data/characters/creator_drafts.sqlite3"
            )

    def create_draft(self, draft: CharacterCreatorDraft) -> CharacterCreatorDraft:
        draft_id = draft.draft_id or f"draft_{uuid4().hex[:12]}"
        now = utc_now_iso()
        persisted = CharacterCreatorDraft.model_validate(
            draft.model_copy(
                update={
                    "draft_id": draft_id,
                    "status": CreatorDraftStatus.draft,
                    "created_at": draft.created_at or now,
                    "updated_at": now,
                    "metadata": self._with_draft_metadata(
                        draft.metadata, draft_id=draft_id
                    ),
                }
            ).model_dump()
        )
        return self._draft_repository.upsert(persisted)

    def load_draft(self, draft_id: str) -> CharacterCreatorDraft:
        draft = self._draft_repository.get(draft_id)
        if draft is None:
            raise KeyError(draft_id)
        return draft

    def list_drafts(self) -> list[CharacterCreatorDraft]:
        return self._draft_repository.list()

    def update_draft(
        self, draft_id: str, update: CharacterCreatorDraftUpdate
    ) -> CharacterCreatorDraft:
        draft = self.load_draft(draft_id)
        changes = update.model_dump(exclude_unset=True)
        if "metadata" in changes and changes["metadata"] is not None:
            changes["metadata"] = self._with_draft_metadata(
                {**draft.metadata, **changes["metadata"]}, draft_id=draft_id
            )
        elif "metadata" not in changes:
            changes["metadata"] = self._with_draft_metadata(
                draft.metadata, draft_id=draft_id
            )
        changes.update(
            {"updated_at": utc_now_iso(), "status": CreatorDraftStatus.draft}
        )
        persisted = CharacterCreatorDraft.model_validate(
            draft.model_copy(update=changes).model_dump()
        )
        return self._draft_repository.upsert(persisted)

    def delete_draft(self, draft_id: str) -> bool:
        return self._draft_repository.delete(draft_id)

    def validate_persisted_draft(self, draft_id: str) -> DraftValidationResponse:
        return self.validate_draft(self.load_draft(draft_id))

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
                    "source": "m6_p01_persisted_creator_draft",
                    "migration_note": (
                        "Persisted creator draft; remains separate from finalized "
                        "CharacterBlueprint rows until a later publishing flow."
                    ),
                },
                **self._with_draft_metadata(draft.metadata, draft_id=draft.draft_id),
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
            metadata=self._build_draft_capture_metadata(
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

    @staticmethod
    def _with_draft_metadata(
        metadata: dict[str, Any], *, draft_id: str | None
    ) -> dict[str, Any]:
        return {
            **metadata,
            "creator_lifecycle": "draft",
            "draft_id": draft_id,
            "draft_schema_version": CREATOR_DRAFT_SCHEMA_VERSION,
            "finalized_character_id": metadata.get("finalized_character_id"),
        }

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
                "draft_rollback_note": self._build_draft_rollback_note(),
            },
        )

    def _with_draft_scene_metadata(
        self, scene_state: SceneState, *, source: DraftMomentSource
    ) -> SceneState:
        """Attach draft capture markers to SceneState without changing scene intent.

        Draft-triggered SceneState metadata is expected to include
        ``draft_capture``, ``draft_source_context``, ``draft_first_portrait``,
        and ``draft_rollback_note``. These fields travel into prompt/job context
        for filtering and provenance, while continuity notes make the
        evidence-only rollback expectation visible during review.
        """

        metadata = {
            **scene_state.metadata,
            "draft_capture": True,
            "draft_source_context": source.value,
            "draft_first_portrait": True,
            "draft_rollback_note": self._build_draft_rollback_note(),
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

    def _build_draft_capture_metadata(
        self, *, request: DraftMomentCaptureRequest, character_id: str
    ) -> dict[str, Any]:
        """Return filterable provenance for evidence-only draft captures.

        Draft-triggered MomentCaptureRequest metadata is expected to include the
        complete standardized ``draft_`` field set returned here. These fields
        are intentionally duplicated at the top level of capture records and
        image-job context so future gallery/review migration tasks can filter
        draft captures without parsing nested draft structures.

        Filtering: ``draft_capture``, ``draft_id``, ``draft_character_id``, and
        ``draft_source_context`` identify draft-originated captures. Provenance:
        ``draft_capture_intent``, ``draft_provenance``, and
        ``draft_queue_policy`` explain why/how the capture was queued. Rollback:
        ``draft_rollback_note``, ``draft_evidence_only``, and
        ``draft_canonical_mutation_allowed`` document that draft captures cannot
        mutate canon until an explicit later review flow permits it.
        """

        return {
            "draft_capture": True,
            "draft_id": request.draft.draft_id,
            "draft_character_id": character_id,
            "draft_source_context": request.source.value,
            "draft_capture_intent": request.capture_intent,
            "draft_rollback_note": self._build_draft_rollback_note(),
            "draft_provenance": "character_creator_draft_first_portrait",
            "draft_queue_policy": "non_blocking_preview_8gb",
            "draft_evidence_only": True,
            "draft_canonical_mutation_allowed": False,
        }

    @staticmethod
    def _build_draft_rollback_note() -> str:
        return (
            "Creator draft capture is evidence-only for first-portrait review; "
            "it does not mutate canonical character data unless a later explicit "
            "review/canon approval flow applies changes."
        )
