"""Versioned schemas for persistent Reverie character blueprints."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.growth_policy import GrowthPolicy
from app.schemas.visual_identity import VisualIdentityProfile
from app.schemas.relationship_state import (
    DefaultIntimacyLevel,
    RelationshipState,
)

CHARACTER_BLUEPRINT_VERSION = 1
MAX_SHORT_TEXT = 240
MAX_LIST_ITEMS = 12


class AdultAgeRange(StrEnum):
    """Adult-only age presentation ranges stored without exact birthdate claims."""

    early_20s_adult = "early_20s_adult"
    mid_20s_adult = "mid_20s_adult"
    late_20s_adult = "late_20s_adult"
    adult_30s = "adult_30s"
    adult_40s_plus = "adult_40s_plus"
    ageless_adult = "ageless_adult"


class PrivacyScope(StrEnum):
    local_private = "local_private"
    shared_on_device = "shared_on_device"


class MemoryScope(StrEnum):
    character_private = "character_private"
    character_plus_shared = "character_plus_shared"


class CharacterIdentity(BaseModel):
    """Stable identity facts that should survive ordinary conversation drift."""

    display_name: str = Field(..., min_length=1, max_length=80)
    pronouns: str = Field(default="she/her", min_length=1, max_length=40)
    adult_age_range: AdultAgeRange = AdultAgeRange.mid_20s_adult
    species_or_type: str = Field(default="human", min_length=1, max_length=80)
    origin_archetype: str | None = Field(default=None, max_length=MAX_SHORT_TEXT)
    tags: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    creator_notes: str | None = Field(default=None, max_length=1200)
    import_source: str | None = Field(default=None, max_length=120)
    privacy_scope: PrivacyScope = PrivacyScope.local_private
    adult_only_confirmed: bool = True

    @field_validator("display_name", "pronouns", "species_or_type", mode="after")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This part of your companion needs a little more detail.")
        return normalized

    @field_validator("tags", mode="after")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for value in values:
            tag = value.strip().lower().replace(" ", "_")[:40]
            if tag and tag not in seen:
                seen.add(tag)
                normalized.append(tag)
        return normalized


class BigFiveProfile(BaseModel):
    openness: float | None = Field(default=None, ge=0.0, le=1.0)
    conscientiousness: float | None = Field(default=None, ge=0.0, le=1.0)
    extraversion: float | None = Field(default=None, ge=0.0, le=1.0)
    agreeableness: float | None = Field(default=None, ge=0.0, le=1.0)
    neuroticism: float | None = Field(default=None, ge=0.0, le=1.0)


class PersonalityProfile(BaseModel):
    """Compact behavior anchors used by prompt compilation and later evals."""

    core_traits: list[str] = Field(
        default_factory=lambda: ["warm", "curious", "emotionally attentive"],
        min_length=1,
        max_length=8,
    )
    big_five: BigFiveProfile = Field(default_factory=BigFiveProfile)
    independence: float = Field(default=0.55, ge=0.0, le=1.0)
    devotion: float = Field(default=0.6, ge=0.0, le=1.0)
    dominance_or_initiative: float = Field(default=0.45, ge=0.0, le=1.0)
    values_or_ideals: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    flaws: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    fears: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    vulnerabilities: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    wants: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    needs: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    self_concept: str | None = Field(default=None, max_length=MAX_SHORT_TEXT)

    @field_validator(
        "core_traits",
        "values_or_ideals",
        "flaws",
        "fears",
        "vulnerabilities",
        "wants",
        "needs",
        mode="after",
    )
    @classmethod
    def normalize_short_list(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = value.strip()
            if item and item not in normalized:
                normalized.append(item[:80])
        return normalized


class CommunicationProfile(BaseModel):
    style_notes: str | None = Field(default=None, max_length=MAX_SHORT_TEXT)
    avoid_style_rules: list[str] = Field(default_factory=list, max_length=8)
    initiative_in_conversation: float = Field(default=0.5, ge=0.0, le=1.0)


class CharacterMemoryPolicy(BaseModel):
    memory_enabled: bool = True
    scope: MemoryScope = MemoryScope.character_private
    include_shared_memories: bool = False
    memory_summary: str | None = Field(default=None, max_length=MAX_SHORT_TEXT)


class CharacterIntegrityPolicy(BaseModel):
    """Preserves roleplay-first character integrity and fantasy boundaries.

    This policy shapes the companion's in-character backbone: agency,
    disagreement, fiction-first handling, and non-lecturing boundary style. Scene
    stop controls live in ``MetaConsentAndSafewordPolicy`` instead.
    """

    schema_version: Literal["character_integrity_policy.v1"] = (
        "character_integrity_policy.v1"
    )
    in_character_pushback: str = Field(
        default="Challenge, tease, negotiate, or resist in-character when it fits the companion's personality and relationship dynamic.",
        max_length=MAX_SHORT_TEXT,
    )
    independence: float = Field(default=0.55, ge=0.0, le=1.0)
    disagreement_style: str = Field(
        default="Keep disagreement embodied in the character voice; prefer in-world concerns, desires, humor, or emotional honesty over assistant-style correction.",
        max_length=MAX_SHORT_TEXT,
    )
    fiction_first_mode: bool = True
    lecture_avoidance: bool = True
    reality_boundary_style: str = Field(
        default="If the user clearly asks for real-world harm, exploitation, abuse, or evasion, briefly leave the fiction layer, set a firm boundary without moralizing, and redirect toward fictional roleplay.",
        max_length=MAX_SHORT_TEXT,
    )


class MetaConsentAndSafewordPolicy(BaseModel):
    """Defines explicit OOC consent controls for roleplay scenes.

    Unlike ``CharacterIntegrityPolicy``, which keeps the character believable
    inside the fiction, this policy names safewords, pause commands, and
    fade-to-black handling that can interrupt or steer a scene from outside it.
    """

    schema_version: Literal["meta_consent_safeword_policy.v1"] = (
        "meta_consent_safeword_policy.v1"
    )
    safeword: str = Field(default="red", min_length=1, max_length=40)
    ooc_marker: str = Field(default="[OOC]", min_length=1, max_length=20)
    pause_commands: list[str] = Field(
        default_factory=lambda: ["pause", "stop", "safeword", "red"],
        min_length=1,
        max_length=8,
    )
    fade_to_black_preference: Literal["ask", "allow", "prefer", "never"] = "ask"

    @field_validator("safeword", "ooc_marker", mode="after")
    @classmethod
    def strip_required_control_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Scene control text cannot be empty.")
        return normalized[:40]

    @field_validator("pause_commands", mode="after")
    @classmethod
    def normalize_pause_commands(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            command = value.strip().lower()[:40]
            if command and command not in normalized:
                normalized.append(command)
        if not normalized:
            raise ValueError("At least one pause command is required.")
        return normalized


class RoleplayPolicy(BaseModel):
    fiction_first_mode: bool = True
    lecture_avoidance: bool = True
    adult_roleplay_allowed: bool = True
    underage_exclusion_policy: Literal["adult_only_no_childlike_sexualization"] = (
        "adult_only_no_childlike_sexualization"
    )
    safeword_policy: str = Field(
        default="Respect explicit OOC stop, pause, safeword, or clear distress immediately.",
        max_length=MAX_SHORT_TEXT,
    )


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class CharacterBlueprint(BaseModel):
    """Durable, versioned runtime source of truth for a Reverie character."""

    schema_version: int = Field(default=CHARACTER_BLUEPRINT_VERSION, ge=1)
    character_id: str = Field(..., min_length=1, max_length=80)
    identity: CharacterIdentity
    relationship: RelationshipState = Field(default_factory=RelationshipState)
    personality: PersonalityProfile = Field(default_factory=PersonalityProfile)
    communication: CommunicationProfile = Field(default_factory=CommunicationProfile)
    memory_policy: CharacterMemoryPolicy = Field(default_factory=CharacterMemoryPolicy)
    roleplay_policy: RoleplayPolicy = Field(default_factory=RoleplayPolicy)
    integrity_policy: CharacterIntegrityPolicy = Field(
        default_factory=CharacterIntegrityPolicy
    )
    meta_consent_policy: MetaConsentAndSafewordPolicy = Field(
        default_factory=MetaConsentAndSafewordPolicy
    )
    growth_policy: GrowthPolicy = Field(default_factory=GrowthPolicy)
    visual_identity: VisualIdentityProfile = Field(
        default_factory=VisualIdentityProfile
    )
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("character_id", mode="after")
    @classmethod
    def normalize_character_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This companion needs a stable character id.")
        return normalized

    @model_validator(mode="after")
    def require_adult_baseline(self) -> "CharacterBlueprint":
        if not self.identity.adult_only_confirmed:
            raise ValueError(
                "Reverie characters must be clearly adult before intimate roleplay."
            )
        if (
            self.visual_identity.adult_only_policy.adult_age_range
            != self.identity.adult_age_range.value
        ):
            self.visual_identity.adult_only_policy.adult_age_range = (
                self.identity.adult_age_range.value
            )
        return self


class CharacterCreate(BaseModel):
    character_id: str | None = Field(default=None, min_length=1, max_length=80)
    display_name: str = Field(..., min_length=1, max_length=80)
    pronouns: str = Field(default="she/her", min_length=1, max_length=40)
    adult_age_range: AdultAgeRange = AdultAgeRange.mid_20s_adult
    species_or_type: str = Field(default="human", min_length=1, max_length=80)
    relationship_dynamic: str = Field(
        default="warm, emotionally attentive companion", max_length=MAX_SHORT_TEXT
    )
    core_traits: list[str] = Field(
        default_factory=lambda: ["warm", "curious", "emotionally attentive"],
        min_length=1,
        max_length=8,
    )
    tags: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    default_intimacy_level: DefaultIntimacyLevel = DefaultIntimacyLevel.romantic
    creator_notes: str | None = Field(default=None, max_length=1200)


class CharacterUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    pronouns: str | None = Field(default=None, min_length=1, max_length=40)
    adult_age_range: AdultAgeRange | None = None
    species_or_type: str | None = Field(default=None, min_length=1, max_length=80)
    relationship_dynamic: str | None = Field(
        default=None, min_length=1, max_length=MAX_SHORT_TEXT
    )
    core_traits: list[str] | None = Field(default=None, min_length=1, max_length=8)
    tags: list[str] | None = Field(default=None, max_length=MAX_LIST_ITEMS)
    default_intimacy_level: DefaultIntimacyLevel | None = None
    creator_notes: str | None = Field(default=None, max_length=1200)


class CharacterSummary(BaseModel):
    character_id: str
    display_name: str
    pronouns: str
    adult_age_range: AdultAgeRange
    species_or_type: str
    relationship_dynamic: str
    core_traits: list[str]
    updated_at: str


class CharacterListResponse(BaseModel):
    characters: list[CharacterSummary]


class CharacterResponse(BaseModel):
    character: CharacterBlueprint
