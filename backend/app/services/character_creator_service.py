"""Minimal M6 creator runtime wiring for draft validation and first portraits.

This module intentionally does not persist creator drafts or implement a full
creation flow. It maps a caller-provided draft into a transient
``CharacterBlueprint`` and can pass that transient blueprint into Moment Capture
so future creator UI can validate a first portrait without duplicating image
logic or silently mutating canon.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

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
from app.schemas.relationship_state import DefaultIntimacyLevel, RelationshipState
from app.schemas.visual_identity import AdultOnlyVisualPolicy, VisualIdentityProfile
from app.services.moment_capture_service import (
    MomentCaptureResponse,
    MomentCaptureService,
)


class CharacterCreatorDraft(BaseModel):
    """Small runtime draft shape for M6 foundation work.

    Migration note: drafts are request-scoped in P00A. If later milestones add
    persistence, store this model with a schema/version field and keep
    ``draft_id`` separate from final ``character_id`` so rollback/review records
    can distinguish draft evidence from committed canon.
    """

    draft_id: str | None = Field(default=None, max_length=120)
    character_id: str | None = Field(default=None, min_length=1, max_length=80)
    display_name: str = Field(..., min_length=1, max_length=80)
    pronouns: str = Field(default="she/her", min_length=1, max_length=40)
    adult_age_range: AdultAgeRange = AdultAgeRange.mid_20s_adult
    adult_only_confirmed: bool = True
    species_or_type: str = Field(default="human", min_length=1, max_length=80)
    relationship_dynamic: str = Field(
        default="warm, emotionally attentive companion", max_length=240
    )
    default_intimacy_level: DefaultIntimacyLevel = DefaultIntimacyLevel.romantic
    core_traits: list[str] = Field(
        default_factory=lambda: ["warm", "curious", "emotionally attentive"],
        min_length=1,
        max_length=8,
    )
    communication_style: str | None = Field(default=None, max_length=240)
    identity_anchors: list[str] = Field(default_factory=list, max_length=12)
    current_appearance: str | None = Field(default=None, max_length=480)
    scene_mutable_traits: list[str] = Field(default_factory=list, max_length=12)
    tags: list[str] = Field(default_factory=list, max_length=12)
    creator_notes: str | None = Field(default=None, max_length=1200)
    metadata: dict[str, object] = Field(default_factory=dict)


class CharacterDraftValidationResponse(BaseModel):
    valid: bool
    blueprint: CharacterBlueprint | None = None
    errors: list[str] = Field(default_factory=list)


class CreatorMomentCaptureRequest(BaseModel):
    draft: CharacterCreatorDraft
    source_context: Literal["chat", "visual_novel"]
    conversation_id: str = Field(default="creator_draft", min_length=1, max_length=120)
    session_id: str = Field(default="creator_session", min_length=1, max_length=120)
    source_message_id: str = Field(
        default="creator_draft", min_length=1, max_length=120
    )
    source_turn_index: int = Field(default=0, ge=0)
    scene_state: SceneState | None = None
    quality_preset: ImageQualityPreset = ImageQualityPreset.preview_8gb
    capture_intent: str = Field(
        default="generate first portrait from creator draft", max_length=240
    )


class CharacterCreatorService:
    """Draft-to-blueprint mapper and Moment Capture bridge."""

    def __init__(self, *, moment_capture_service: MomentCaptureService) -> None:
        self._moment_capture_service = moment_capture_service

    def draft_to_blueprint(self, draft: CharacterCreatorDraft) -> CharacterBlueprint:
        character_id = (
            draft.character_id
            or f"draft_{draft.draft_id or stable_prompt_hash(draft.display_name, draft.species_or_type)}"
        )
        visual = VisualIdentityProfile(
            identity_anchors=draft.identity_anchors,
            scene_mutable_traits=draft.scene_mutable_traits,
            current_appearance=draft.current_appearance,
            adult_only_policy=AdultOnlyVisualPolicy(
                adult_age_range=draft.adult_age_range.value,
            ),
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
                relationship_dynamic=draft.relationship_dynamic,
                default_intimacy_level=draft.default_intimacy_level,
            ),
            personality=PersonalityProfile(core_traits=draft.core_traits),
            communication=CommunicationProfile(style_notes=draft.communication_style),
            visual_identity=visual,
            metadata={
                "creator_draft": True,
                "draft_id": draft.draft_id,
                "draft_metadata": draft.metadata,
                "migration_note": "P00A drafts are request-scoped; persist with a separate draft_id in later M6 tasks.",
            },
        )

    def validate_draft(
        self, draft: CharacterCreatorDraft
    ) -> CharacterDraftValidationResponse:
        try:
            blueprint = self.draft_to_blueprint(draft)
        except ValueError as exc:
            return CharacterDraftValidationResponse(valid=False, errors=[str(exc)])
        return CharacterDraftValidationResponse(valid=True, blueprint=blueprint)

    async def capture_first_portrait(
        self, request: CreatorMomentCaptureRequest
    ) -> MomentCaptureResponse:
        blueprint = self.draft_to_blueprint(request.draft)
        scene_state = request.scene_state or self._default_scene(
            request.source_context, blueprint
        )
        moment_request = MomentCaptureRequest.from_chat_turn(
            character_id=blueprint.character_id,
            conversation_id=request.conversation_id,
            session_id=request.session_id,
            source_message_id=request.source_message_id,
            source_turn_index=request.source_turn_index,
            scene_state=scene_state,
            visual_identity=blueprint.visual_identity,
            relationship_state=blueprint.relationship,
            quality_preset=request.quality_preset,
            metadata={
                "creator_draft": True,
                "draft_id": request.draft.draft_id,
                "source_context": request.source_context,
                "capture_intent": request.capture_intent,
                "queued_resource_class": "exclusive_media_low_priority",
                "non_blocking": True,
                "provenance": {
                    "source": f"creator_draft_{request.source_context}",
                    "draft_id": request.draft.draft_id,
                    "created_at": utc_now_iso(),
                },
                "rollback_note": "First portrait evidence only; no visual canon mutation without existing feedback/review flow.",
            },
        )
        return await self._moment_capture_service.capture_for_blueprint(
            moment_request, blueprint
        )

    def _default_scene(
        self, source_context: str, blueprint: CharacterBlueprint
    ) -> SceneState:
        return SceneState(
            location=(
                "neutral creator portrait space"
                if source_context == "chat"
                else "visual novel portrait stage"
            ),
            mood="calm, recognizable first portrait",
            emotional_tone="warm introduction",
            character_appearance=blueprint.visual_identity.compact_prompt_summary(
                include_scene_mutable=True
            ),
            pose="clear face, relaxed front-facing portrait",
            background_details=["simple background", "identity anchors visible"],
            continuity_notes=[
                "first portrait validation",
                "evidence only, not automatic canon",
            ],
            metadata={"source_context": source_context, "creator_default_scene": True},
        )
