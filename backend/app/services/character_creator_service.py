"""Minimal runtime wiring for future M6 character creator flows.

This module persists creator drafts separately from finalized
``CharacterBlueprint`` records, maps a draft into a valid runtime blueprint for
validation/preview, and can submit a first-portrait Moment Capture through the
existing non-blocking capture service.

Persistence/migration note: ``CharacterCreatorDraftRecord`` stores a durable
draft schema version and preserves ``metadata`` losslessly for forward migration.
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
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.models.image import ImageQualityPreset
from app.schemas.character_blueprint import (
    AdultAgeRange,
    CharacterBlueprint,
    CharacterIdentity,
    CharacterIntegrityPolicy,
    MetaConsentAndSafewordPolicy,
    CommunicationProfile,
    MAX_LIST_ITEMS,
    MAX_SHORT_TEXT,
    PersonalityProfile,
    RoleplayPolicy,
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
    RelationshipPacing,
    RelationshipState,
)
from app.schemas.visual_identity import VisualIdentityProfile
from app.services.character_service import CharacterNotFoundError
from app.services.moment_capture_service import (
    MomentCaptureResponse,
    MomentCaptureService,
)

LOGGER = logging.getLogger(__name__)
DRAFT_SCHEMA_VERSION = 5

UNDERAGE_PRESENTATION_TERMS = (
    "underage",
    "minor",
    "childlike",
    "teen",
    "teenage",
    "schoolgirl",
    "schoolboy",
    "loli",
    "shota",
)


def _normalize_optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    _reject_underage_or_childlike_presentation(normalized, field_name)
    return normalized


def _normalize_creator_list(
    values: list[str],
    *,
    field_name: str,
    required: bool = False,
    max_items: int = MAX_LIST_ITEMS,
    max_item_length: int = 80,
) -> list[str]:
    normalized: list[str] = []
    for value in values:
        item = " ".join(str(value).strip().split())[:max_item_length]
        if item and item not in normalized:
            _reject_underage_or_childlike_presentation(item, field_name)
            normalized.append(item)
    if required and not normalized:
        raise ValueError(f"At least one {field_name.lower()} entry is required.")
    return normalized[:max_items]


def _normalize_required_policy_text(value: str, field_name: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty.")
    _reject_underage_or_childlike_presentation(normalized, field_name)
    lowered = normalized.lower()
    blocked_fragments = ("as an ai", "moral lecture", "kink shame", "kink-shame")
    if any(fragment in lowered for fragment in blocked_fragments):
        raise ValueError(
            f"{field_name} must preserve roleplay-first, in-character boundaries without assistant-style moralizing."
        )
    return normalized


def _reject_underage_or_childlike_presentation(value: str, field_name: str) -> None:
    """Enforce the creator matrix adult-only baseline without over-policing adults."""

    normalized = value.lower()
    for term in UNDERAGE_PRESENTATION_TERMS:
        if term in normalized:
            raise ValueError(
                f"{field_name} must describe a clearly adult companion; "
                "underage or deliberately childlike sexual presentation is not allowed."
            )


class CreatorDraftIntegrityPolicy(BaseModel):
    """Draft-scoped character integrity controls consumed by runtime prompts."""

    in_character_pushback: str = Field(
        default=(
            "Challenge, tease, negotiate, or resist in-character when it fits "
            "the companion's personality and relationship dynamic."
        ),
        min_length=1,
        max_length=MAX_SHORT_TEXT,
    )
    disagreement_style: str = Field(
        default=(
            "Keep disagreement embodied in the character voice; use in-world "
            "concerns, desires, humor, or emotional honesty instead of assistant-style correction."
        ),
        min_length=1,
        max_length=MAX_SHORT_TEXT,
    )

    @field_validator("in_character_pushback", "disagreement_style", mode="after")
    @classmethod
    def normalize_integrity_text(cls, value: str) -> str:
        return _normalize_required_policy_text(value, "Integrity policy")


class CreatorDraftRoleplayPolicy(BaseModel):
    """Draft-scoped fiction-first roleplay switches that current runtime consumes."""

    fiction_first_mode: bool = True


class CreatorDraftSafewordPolicy(BaseModel):
    """Draft-scoped OOC/safeword controls mapped to MetaConsentAndSafewordPolicy."""

    safeword: str = Field(default="red", min_length=1, max_length=40)
    ooc_marker: str = Field(default="[OOC]", min_length=1, max_length=20)
    pause_commands: list[str] = Field(
        default_factory=lambda: ["pause", "stop", "safeword", "red"],
        min_length=1,
        max_length=8,
    )
    fade_to_black_preference: str = Field(default="ask")
    policy_note: str = Field(
        default="Respect explicit OOC stop, pause, safeword, or clear distress immediately.",
        min_length=1,
        max_length=MAX_SHORT_TEXT,
    )

    @field_validator("safeword", "ooc_marker", "policy_note", mode="after")
    @classmethod
    def normalize_control_text(cls, value: str) -> str:
        return _normalize_required_policy_text(value, "Safeword policy")

    @field_validator("pause_commands", mode="after")
    @classmethod
    def normalize_pause_commands(cls, values: list[str]) -> list[str]:
        return _normalize_creator_list(
            values,
            field_name="Safeword pause commands",
            required=True,
            max_items=8,
            max_item_length=40,
        )

    @field_validator("fade_to_black_preference", mode="after")
    @classmethod
    def validate_fade_to_black(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"ask", "allow", "prefer", "never"}
        if normalized not in allowed:
            raise ValueError(
                "Fade-to-black preference must be ask, allow, prefer, or never."
            )
        return normalized


class CreatorDraftMetaPolicy(BaseModel):
    safeword_policy: CreatorDraftSafewordPolicy = Field(
        default_factory=CreatorDraftSafewordPolicy
    )


class CreatorDraftContentBoundaries(BaseModel):
    """Draft-only boundary summary for hard limits and roleplay steering."""

    hard_limits: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    soft_limits: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    preferred_intensity: str | None = Field(default=None, max_length=80)
    aftercare_style: str | None = Field(default=None, max_length=MAX_SHORT_TEXT)

    @field_validator("hard_limits", "soft_limits", mode="after")
    @classmethod
    def normalize_boundary_lists(cls, values: list[str]) -> list[str]:
        return _normalize_creator_list(values, field_name="Content boundaries")

    @field_validator("preferred_intensity", "aftercare_style", mode="after")
    @classmethod
    def normalize_boundary_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, "Content boundaries")


class CreatorDraftVisualIdentity(BaseModel):
    """Creator-facing visual fields with stable anchors separated from scene state.

    These fields are intentionally explicit so the creator can persist user
    choices without asking users to hand-author ``VisualIdentityProfile`` JSON.
    Stable identity anchors map to ``VisualIdentityProfile.identity_anchors``;
    hair/accessory/fashion details map to evolving traits; outfit/pose/expression
    map only to scene-mutable traits.
    """

    eye_color: str | None = Field(default=None, max_length=80)
    skin_tone: str | None = Field(default=None, max_length=120)
    face_structure: str | None = Field(default=None, max_length=160)
    body_baseline: str | None = Field(default=None, max_length=160)
    species_features: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    permanent_marks: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    hair: str | None = Field(default=None, max_length=160)
    accessories: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    fashion_identity: str | None = Field(default=None, max_length=160)
    outfit: str | None = Field(default=None, max_length=160)
    pose: str | None = Field(default=None, max_length=160)
    expression: str | None = Field(default=None, max_length=160)
    rejected_visual_traits: list[str] = Field(
        default_factory=list, max_length=MAX_LIST_ITEMS
    )

    @field_validator(
        "eye_color",
        "skin_tone",
        "face_structure",
        "body_baseline",
        "hair",
        "fashion_identity",
        "outfit",
        "pose",
        "expression",
        mode="after",
    )
    @classmethod
    def normalize_visual_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, "Visual identity")

    @field_validator(
        "species_features",
        "permanent_marks",
        "accessories",
        "rejected_visual_traits",
        mode="after",
    )
    @classmethod
    def normalize_visual_lists(cls, values: list[str]) -> list[str]:
        return _normalize_creator_list(values, field_name="Visual identity")

    @model_validator(mode="after")
    def validate_anchor_scene_separation(self) -> "CreatorDraftVisualIdentity":
        scene_words = ("outfit", "clothes", "dress", "pose", "expression", "smile")
        stable_values = {
            "eye_color": self.eye_color,
            "skin_tone": self.skin_tone,
            "face_structure": self.face_structure,
            "body_baseline": self.body_baseline,
        }
        for field_name, value in stable_values.items():
            if value and any(word in value.lower() for word in scene_words):
                raise ValueError(
                    f"{field_name} must describe stable identity, not scene-mutable outfit, pose, or expression details."
                )
        return self

    def to_profile(
        self, base: VisualIdentityProfile | None = None
    ) -> VisualIdentityProfile:
        profile = base or VisualIdentityProfile()
        anchors = list(profile.identity_anchors)
        for label, value in (
            ("eye color", self.eye_color),
            ("skin tone", self.skin_tone),
            ("face structure", self.face_structure),
            ("body baseline", self.body_baseline),
        ):
            if value:
                fragment = f"{label}: {value}"
                if fragment not in anchors:
                    anchors.append(fragment)
        for label, values in (
            ("species features", self.species_features),
            ("permanent marks", self.permanent_marks),
        ):
            for value in values:
                fragment = f"{label}: {value}"
                if fragment not in anchors:
                    anchors.append(fragment)

        scene_traits = list(profile.scene_mutable_traits)
        for label, value in (
            ("outfit", self.outfit),
            ("pose", self.pose),
            ("expression", self.expression),
        ):
            if value:
                fragment = f"{label}: {value}"
                if fragment not in scene_traits:
                    scene_traits.append(fragment)

        rejected = list(profile.rejected_traits)
        for value in self.rejected_visual_traits:
            if value not in rejected:
                rejected.append(value)

        profile = profile.model_copy(
            update={
                "identity_anchors": anchors[:MAX_LIST_ITEMS],
                "scene_mutable_traits": scene_traits[:MAX_LIST_ITEMS],
                "rejected_traits": rejected[:MAX_LIST_ITEMS],
                "updated_at": utc_now_iso(),
            }
        )
        for name, value in (
            ("hair", self.hair),
            ("fashion_identity", self.fashion_identity),
        ):
            if value:
                profile = profile.with_evolving_trait(
                    name, value, provenance="creator_draft_visual_identity"
                )
        for accessory in self.accessories:
            profile = profile.with_evolving_trait(
                "accessory", accessory, provenance="creator_draft_visual_identity"
            )
        return profile


class DraftMomentSource(StrEnum):
    chat = "chat"
    visual_novel = "visual_novel"


class CharacterCreatorDraft(BaseModel):
    """Creator draft shape for basic M6 runtime validation and persistence."""

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
    relationship_pacing: RelationshipPacing = RelationshipPacing.natural
    romantic_pacing: RelationshipPacing = RelationshipPacing.natural
    nsfw_pacing: RelationshipPacing = RelationshipPacing.user_led
    default_intimacy_level: DefaultIntimacyLevel = DefaultIntimacyLevel.romantic
    user_desired_experience: str | None = Field(default=None, max_length=240)
    core_traits: list[str] = Field(
        default_factory=lambda: ["warm", "curious", "emotionally attentive"],
        min_length=1,
        max_length=8,
    )
    independence: float = Field(default=0.55, ge=0.0, le=1.0)
    devotion: float = Field(default=0.6, ge=0.0, le=1.0)
    dominance_or_initiative: float = Field(default=0.45, ge=0.0, le=1.0)
    values_or_ideals: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    flaws: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    fears: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    vulnerabilities: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    communication_style: str | None = Field(default=None, max_length=240)
    integrity: CreatorDraftIntegrityPolicy = Field(
        default_factory=CreatorDraftIntegrityPolicy
    )
    roleplay: CreatorDraftRoleplayPolicy = Field(
        default_factory=CreatorDraftRoleplayPolicy
    )
    meta: CreatorDraftMetaPolicy = Field(default_factory=CreatorDraftMetaPolicy)
    content_boundaries: CreatorDraftContentBoundaries = Field(
        default_factory=CreatorDraftContentBoundaries
    )
    avoid_style: list[str] = Field(default_factory=list, max_length=8)
    initiative_in_conversation: float = Field(default=0.5, ge=0.0, le=1.0)
    visual: CreatorDraftVisualIdentity = Field(
        default_factory=CreatorDraftVisualIdentity
    )
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

    @field_validator(
        "display_name",
        "pronouns",
        "species_or_type",
        "relationship_dynamic",
        mode="after",
    )
    @classmethod
    def strip_required_creator_text(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("This part of your companion needs a little more detail.")
        _reject_underage_or_childlike_presentation(normalized, "Creator draft")
        return normalized

    @field_validator("user_desired_experience", "communication_style", mode="after")
    @classmethod
    def strip_optional_creator_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, "Creator draft")

    @field_validator("core_traits", mode="after")
    @classmethod
    def normalize_core_traits(cls, values: list[str]) -> list[str]:
        return _normalize_creator_list(
            values, field_name="Core traits", required=True, max_items=8
        )

    @field_validator(
        "values_or_ideals",
        "flaws",
        "fears",
        "vulnerabilities",
        "avoid_style",
        mode="after",
    )
    @classmethod
    def normalize_creator_lists(cls, values: list[str]) -> list[str]:
        return _normalize_creator_list(values, field_name="Creator draft")


class DraftValidationResponse(BaseModel):
    valid: bool
    blueprint: CharacterBlueprint | None = None
    errors: list[str] = Field(default_factory=list)


class CharacterCreatorDraftCreate(BaseModel):
    draft: CharacterCreatorDraft


class CharacterCreatorDraftUpdate(BaseModel):
    """Partial draft patch. Omitted fields are left unchanged."""

    character_id: str | None = Field(default=None, max_length=80)
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    pronouns: str | None = Field(default=None, min_length=1, max_length=40)
    adult_age_range: AdultAgeRange | None = None
    adult_only_confirmed: bool | None = None
    species_or_type: str | None = Field(default=None, min_length=1, max_length=80)
    relationship_dynamic: str | None = Field(default=None, min_length=1, max_length=240)
    starting_relationship_phase: RelationshipPhase | None = None
    relationship_pacing: RelationshipPacing | None = None
    romantic_pacing: RelationshipPacing | None = None
    nsfw_pacing: RelationshipPacing | None = None
    default_intimacy_level: DefaultIntimacyLevel | None = None
    user_desired_experience: str | None = Field(default=None, max_length=240)
    core_traits: list[str] | None = Field(default=None, min_length=1, max_length=8)
    independence: float | None = Field(default=None, ge=0.0, le=1.0)
    devotion: float | None = Field(default=None, ge=0.0, le=1.0)
    dominance_or_initiative: float | None = Field(default=None, ge=0.0, le=1.0)
    values_or_ideals: list[str] | None = Field(default=None, max_length=MAX_LIST_ITEMS)
    flaws: list[str] | None = Field(default=None, max_length=MAX_LIST_ITEMS)
    fears: list[str] | None = Field(default=None, max_length=MAX_LIST_ITEMS)
    vulnerabilities: list[str] | None = Field(default=None, max_length=MAX_LIST_ITEMS)
    communication_style: str | None = Field(default=None, max_length=240)
    integrity: CreatorDraftIntegrityPolicy = Field(
        default_factory=CreatorDraftIntegrityPolicy
    )
    roleplay: CreatorDraftRoleplayPolicy = Field(
        default_factory=CreatorDraftRoleplayPolicy
    )
    meta: CreatorDraftMetaPolicy = Field(default_factory=CreatorDraftMetaPolicy)
    content_boundaries: CreatorDraftContentBoundaries = Field(
        default_factory=CreatorDraftContentBoundaries
    )
    avoid_style: list[str] | None = Field(default=None, max_length=8)
    initiative_in_conversation: float | None = Field(default=None, ge=0.0, le=1.0)
    visual: CreatorDraftVisualIdentity | None = None
    visual_identity: VisualIdentityProfile | None = None
    tags: list[str] | None = Field(default=None, max_length=12)
    creator_notes: str | None = Field(default=None, max_length=1200)
    metadata: dict[str, Any] | None = None


class CharacterCreatorDraftRecord(BaseModel):
    """Durable draft envelope kept distinct from canonical characters."""

    schema_version: int = Field(default=DRAFT_SCHEMA_VERSION, ge=1)
    draft_id: str = Field(..., min_length=1, max_length=120)
    lifecycle_state: str = Field(default="draft", pattern="^draft$")
    draft: CharacterCreatorDraft
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    provenance: dict[str, Any] = Field(default_factory=dict)


class CharacterCreatorDraftResponse(BaseModel):
    record: CharacterCreatorDraftRecord
    validation: DraftValidationResponse


class CharacterCreatorDraftListResponse(BaseModel):
    drafts: list[CharacterCreatorDraftRecord]


class CreatorDraftNotFoundError(LookupError):
    def __init__(self, draft_id: str) -> None:
        self.draft_id = draft_id
        super().__init__(f"Creator draft '{draft_id}' was not found.")


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


class PersistedDraftMomentCaptureRequest(BaseModel):
    source: DraftMomentSource
    conversation_id: str = Field(default="creator-draft", min_length=1, max_length=120)
    session_id: str | None = Field(default=None, max_length=120)
    source_message_id: str | None = Field(default=None, max_length=120)
    source_turn_index: int = Field(default=0, ge=0)
    scene_state: SceneState | None = None
    capture_intent: str = Field(
        default="first portrait from persisted creator draft", max_length=240
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
    ) -> None:
        self._moment_capture_service = moment_capture_service
        self._draft_repository = draft_repository

    @classmethod
    def from_settings(cls, settings: Any) -> "CharacterCreatorService":
        from app.repositories.creator_draft_repo import CreatorDraftRepository

        return cls(draft_repository=CreatorDraftRepository(settings.character_db_path))

    def create_draft(
        self, request: CharacterCreatorDraftCreate | CharacterCreatorDraft
    ) -> CharacterCreatorDraftResponse:
        self._require_repository()
        draft = request if isinstance(request, CharacterCreatorDraft) else request.draft
        draft_id = draft.draft_id or f"draft_{uuid4().hex[:12]}"
        stored_draft = draft.model_copy(update={"draft_id": draft_id})
        now = utc_now_iso()
        record = CharacterCreatorDraftRecord(
            draft_id=draft_id,
            draft=stored_draft,
            created_at=now,
            updated_at=now,
            provenance={
                "source": "m6_p01_creator_draft_persistence",
                "state": "draft_not_finalized",
                "separation": "stored_in_character_creator_drafts_table",
            },
        )
        saved = self._draft_repository.upsert(record)
        return CharacterCreatorDraftResponse(
            record=saved, validation=self.validate_draft(saved.draft)
        )

    def load_draft(self, draft_id: str) -> CharacterCreatorDraftResponse:
        record = self._get_record_or_raise(draft_id)
        return CharacterCreatorDraftResponse(
            record=record, validation=self.validate_draft(record.draft)
        )

    def list_drafts(self) -> CharacterCreatorDraftListResponse:
        self._require_repository()
        return CharacterCreatorDraftListResponse(drafts=self._draft_repository.list())

    def update_draft(
        self, draft_id: str, patch: CharacterCreatorDraftUpdate
    ) -> CharacterCreatorDraftResponse:
        record = self._get_record_or_raise(draft_id)
        updates = patch.model_dump(exclude_unset=True, mode="json")
        if "metadata" in updates and updates["metadata"] is not None:
            updates["metadata"] = {**record.draft.metadata, **updates["metadata"]}
        draft_payload = {**record.draft.model_dump(mode="json"), **updates}
        # Re-validate copied updates because raw patch merging is intentionally permissive.
        updated_draft = CharacterCreatorDraft.model_validate(draft_payload)
        saved = self._draft_repository.upsert(
            record.model_copy(
                update={"draft": updated_draft, "updated_at": utc_now_iso()}
            )
        )
        return CharacterCreatorDraftResponse(
            record=saved, validation=self.validate_draft(saved.draft)
        )

    def delete_draft(self, draft_id: str) -> bool:
        self._require_repository()
        return self._draft_repository.delete(draft_id)

    def validate_persisted_draft(self, draft_id: str) -> DraftValidationResponse:
        return self.validate_draft(self._get_record_or_raise(draft_id).draft)

    def _require_repository(self) -> None:
        if self._draft_repository is None:
            raise RuntimeError(
                "Creator draft persistence repository is not configured."
            )

    def _get_record_or_raise(self, draft_id: str) -> CharacterCreatorDraftRecord:
        self._require_repository()
        record = self._draft_repository.get(draft_id)
        if record is None:
            raise CreatorDraftNotFoundError(draft_id)
        return record

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
                relationship_pacing=draft.relationship_pacing,
                romantic_pacing=draft.romantic_pacing,
                nsfw_pacing=draft.nsfw_pacing,
                default_intimacy_level=draft.default_intimacy_level,
                user_desired_experience=draft.user_desired_experience,
            ),
            personality=PersonalityProfile(
                core_traits=draft.core_traits,
                independence=draft.independence,
                devotion=draft.devotion,
                dominance_or_initiative=draft.dominance_or_initiative,
                values_or_ideals=draft.values_or_ideals,
                flaws=draft.flaws,
                fears=draft.fears,
                vulnerabilities=draft.vulnerabilities,
            ),
            communication=CommunicationProfile(
                style_notes=draft.communication_style,
                avoid_style_rules=draft.avoid_style,
                initiative_in_conversation=draft.initiative_in_conversation,
            ),
            roleplay_policy=RoleplayPolicy(
                fiction_first_mode=draft.roleplay.fiction_first_mode,
                lecture_avoidance=True,
                adult_roleplay_allowed=True,
                safeword_policy=draft.meta.safeword_policy.policy_note,
            ),
            integrity_policy=CharacterIntegrityPolicy(
                in_character_pushback=draft.integrity.in_character_pushback,
                independence=draft.independence,
                disagreement_style=draft.integrity.disagreement_style,
                fiction_first_mode=draft.roleplay.fiction_first_mode,
                lecture_avoidance=True,
            ),
            meta_consent_policy=MetaConsentAndSafewordPolicy(
                safeword=draft.meta.safeword_policy.safeword,
                ooc_marker=draft.meta.safeword_policy.ooc_marker,
                pause_commands=draft.meta.safeword_policy.pause_commands,
                fade_to_black_preference=draft.meta.safeword_policy.fade_to_black_preference,
            ),
            visual_identity=draft.visual.to_profile(draft.visual_identity),
            metadata={
                "creator_draft": {
                    "draft_id": draft.draft_id,
                    "source": "m6_p05_visual_identity_draft",
                    "migration_note": (
                        "API-only draft roleplay policy and visual identity fields "
                        "are mapped into runtime CharacterBlueprint structures "
                        "before final save."
                    ),
                },
                "content_boundaries": draft.content_boundaries.model_dump(mode="json"),
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

    async def capture_persisted_first_portrait(
        self, draft_id: str, request: PersistedDraftMomentCaptureRequest
    ) -> MomentCaptureResponse:
        record = self._get_record_or_raise(draft_id)
        return await self.capture_first_portrait(
            DraftMomentCaptureRequest(
                draft=record.draft,
                source=request.source,
                conversation_id=request.conversation_id,
                session_id=request.session_id,
                source_message_id=request.source_message_id,
                source_turn_index=request.source_turn_index,
                scene_state=request.scene_state,
                capture_intent=request.capture_intent,
                quality_preset=request.quality_preset,
            )
        )

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
