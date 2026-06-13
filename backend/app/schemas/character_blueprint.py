"""Versioned schemas for persistent Reverie character blueprints."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

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


class RelationshipPhase(StrEnum):
    strangers = "strangers"
    newly_met = "newly_met"
    friends = "friends"
    close = "close"
    romantic = "romantic"
    established_partners = "established_partners"


class RelationshipPacing(StrEnum):
    slow_burn = "slow_burn"
    natural = "natural"
    direct = "direct"
    user_led = "user_led"


class DefaultIntimacyLevel(StrEnum):
    sfw = "sfw"
    flirtatious = "flirtatious"
    romantic = "romantic"
    adult_roleplay = "adult_roleplay"


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


class RelationshipState(BaseModel):
    """Current relationship baseline consumed by chat, memory, and growth."""

    starting_relationship_phase: RelationshipPhase = RelationshipPhase.newly_met
    current_relationship_phase: RelationshipPhase | None = None
    relationship_dynamic: str = Field(
        default="warm, emotionally attentive companion", min_length=1, max_length=MAX_SHORT_TEXT
    )
    user_desired_experience: str | None = Field(default=None, max_length=MAX_SHORT_TEXT)
    relationship_pacing: RelationshipPacing = RelationshipPacing.natural
    default_intimacy_level: DefaultIntimacyLevel = DefaultIntimacyLevel.romantic
    user_role_in_story: str | None = Field(default=None, max_length=MAX_SHORT_TEXT)

    @model_validator(mode="after")
    def fill_current_phase(self) -> "RelationshipState":
        if self.current_relationship_phase is None:
            self.current_relationship_phase = self.starting_relationship_phase
        return self


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

    @field_validator("core_traits", "values_or_ideals", "flaws", "fears", "vulnerabilities", "wants", "needs", mode="after")
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
    scope: MemoryScope = MemoryScope.character_private
    include_shared_memories: bool = False
    memory_summary: str | None = Field(default=None, max_length=MAX_SHORT_TEXT)


class RoleplayPolicy(BaseModel):
    fiction_first_mode: bool = True
    lecture_avoidance: bool = True
    adult_roleplay_allowed: bool = True
    underage_exclusion_policy: Literal["adult_only_no_childlike_sexualization"] = "adult_only_no_childlike_sexualization"
    safeword_policy: str = Field(
        default="Respect explicit OOC stop, pause, safeword, or clear distress immediately.",
        max_length=MAX_SHORT_TEXT,
    )


class GrowthPolicy(BaseModel):
    character_scoped_growth: bool = True
    evidence_required_for_drift: bool = True
    allow_lora_candidates: bool = False


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
    growth_policy: GrowthPolicy = Field(default_factory=GrowthPolicy)
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
            raise ValueError("Reverie characters must be clearly adult before intimate roleplay.")
        return self


class CharacterCreate(BaseModel):
    character_id: str | None = Field(default=None, min_length=1, max_length=80)
    display_name: str = Field(..., min_length=1, max_length=80)
    pronouns: str = Field(default="she/her", min_length=1, max_length=40)
    adult_age_range: AdultAgeRange = AdultAgeRange.mid_20s_adult
    species_or_type: str = Field(default="human", min_length=1, max_length=80)
    relationship_dynamic: str = Field(default="warm, emotionally attentive companion", max_length=MAX_SHORT_TEXT)
    core_traits: list[str] = Field(default_factory=lambda: ["warm", "curious", "emotionally attentive"], min_length=1, max_length=8)
    tags: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    default_intimacy_level: DefaultIntimacyLevel = DefaultIntimacyLevel.romantic
    creator_notes: str | None = Field(default=None, max_length=1200)


class CharacterUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    pronouns: str | None = Field(default=None, min_length=1, max_length=40)
    adult_age_range: AdultAgeRange | None = None
    species_or_type: str | None = Field(default=None, min_length=1, max_length=80)
    relationship_dynamic: str | None = Field(default=None, min_length=1, max_length=MAX_SHORT_TEXT)
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
