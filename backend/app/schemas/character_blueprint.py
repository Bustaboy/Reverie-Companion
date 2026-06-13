"""Versioned character blueprint schemas for Reverie's runtime foundation."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

BLUEPRINT_SCHEMA_VERSION = 1
_MAX_SHORT_TEXT = 160
_MAX_LIST_ITEMS = 12


class AdultAgeRange(StrEnum):
    """Adult-only age bands used for identity without storing exact age by default."""

    early_20s = "early_20s"
    mid_20s = "mid_20s"
    late_20s = "late_20s"
    thirties = "thirties"
    forties_plus = "forties_plus"
    ageless_adult = "ageless_adult"


class RelationshipDynamic(StrEnum):
    """High-level relationship modes consumed by chat and growth."""

    warm_companion = "warm_companion"
    romantic_partner = "romantic_partner"
    flirty_muse = "flirty_muse"
    devoted_partner = "devoted_partner"
    slow_burn = "slow_burn"
    power_exchange = "power_exchange"
    dark_romance = "dark_romance"


class RelationshipPhase(StrEnum):
    """Mutable relationship phase, intentionally compact for prompt use."""

    first_meeting = "first_meeting"
    getting_close = "getting_close"
    trusted = "trusted"
    intimate = "intimate"
    established = "established"


class CharacterIdentity(BaseModel):
    """Stable identity fields that should remain recognizable unless edited."""

    display_name: str = Field(..., min_length=1, max_length=80)
    pronouns: str = Field(default="she/her", min_length=1, max_length=40)
    adult_age_range: AdultAgeRange = AdultAgeRange.mid_20s
    species_or_type: str = Field(default="human adult", min_length=1, max_length=80)
    short_description: str | None = Field(default=None, max_length=240)
    identity_anchors: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("display_name", "pronouns", "species_or_type", "short_description")
    @classmethod
    def _clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError(
                "This field needs a little detail before she can remember it."
            )
        return cleaned

    @field_validator("identity_anchors")
    @classmethod
    def _clean_anchors(cls, values: list[str]) -> list[str]:
        return _clean_string_list(values, max_items=8)


class CharacterPersonalityProfile(BaseModel):
    """Personality basics consumed by the prompt compiler from day one."""

    core_traits: list[str] = Field(default_factory=list, max_length=_MAX_LIST_ITEMS)
    values: list[str] = Field(default_factory=list, max_length=8)
    likes: list[str] = Field(default_factory=list, max_length=10)
    dislikes: list[str] = Field(default_factory=list, max_length=10)
    speaking_style: str | None = Field(default=None, max_length=220)

    @field_validator("core_traits", "values", "likes", "dislikes")
    @classmethod
    def _clean_lists(cls, values: list[str]) -> list[str]:
        return _clean_string_list(values, max_items=_MAX_LIST_ITEMS)

    @field_validator("speaking_style")
    @classmethod
    def _clean_speaking_style(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)


class RelationshipState(BaseModel):
    """Current bond state for scoped growth and runtime continuity."""

    dynamic: RelationshipDynamic = RelationshipDynamic.warm_companion
    phase: RelationshipPhase = RelationshipPhase.first_meeting
    trust_level: float = Field(default=0.2, ge=0.0, le=1.0)
    intimacy_level: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str | None = Field(default=None, max_length=260)

    @field_validator("summary")
    @classmethod
    def _clean_summary(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)


class CharacterMemoryPolicy(BaseModel):
    """Memory scoping defaults for a character."""

    scope: str = Field(
        default="character_private", pattern="^(character_private|shared_when_marked)$"
    )
    remember_user_preferences: bool = True
    remember_relationship_moments: bool = True
    allow_training_candidates: bool = False


class GrowthPolicy(BaseModel):
    """Reviewable growth scope; no heavy training is triggered by this schema."""

    journal_enabled: bool = True
    reflection_enabled: bool = True
    relationship_growth_enabled: bool = True
    training_candidates_enabled: bool = False


class RoleplayPolicy(BaseModel):
    """Roleplay-first fantasy policy consumed by prompts without hidden filtering."""

    fiction_first_mode: bool = True
    adult_fantasy_allowed: bool = True
    dark_fantasy_allowed: bool = False
    power_exchange_allowed: bool = False
    cnc_fantasy_allowed: bool = False
    in_scene_resistance_allowed: bool = False
    lecture_avoidance: bool = True
    ooc_marker: str = Field(default="[OOC]", min_length=1, max_length=24)
    safeword: str = Field(default="red", min_length=1, max_length=40)
    aftercare_style: str | None = Field(default=None, max_length=160)

    @field_validator("ooc_marker", "safeword", "aftercare_style")
    @classmethod
    def _clean_policy_text(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)


class CharacterBlueprint(BaseModel):
    """Durable, versioned runtime blueprint for one Reverie character."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=BLUEPRINT_SCHEMA_VERSION, ge=1)
    identity: CharacterIdentity
    personality: CharacterPersonalityProfile = Field(
        default_factory=CharacterPersonalityProfile
    )
    relationship: RelationshipState = Field(default_factory=RelationshipState)
    memory_policy: CharacterMemoryPolicy = Field(default_factory=CharacterMemoryPolicy)
    growth_policy: GrowthPolicy = Field(default_factory=GrowthPolicy)
    roleplay_policy: RoleplayPolicy = Field(default_factory=RoleplayPolicy)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _align_relationship_roleplay(self) -> "CharacterBlueprint":
        if self.relationship.dynamic == RelationshipDynamic.power_exchange:
            self.roleplay_policy.power_exchange_allowed = True
        if self.relationship.dynamic == RelationshipDynamic.dark_romance:
            self.roleplay_policy.dark_fantasy_allowed = True
        return self


class CharacterCreate(BaseModel):
    """Create payload accepted by service/API callers."""

    blueprint: CharacterBlueprint
    character_id: str | None = Field(default=None, min_length=1, max_length=80)


class CharacterUpdate(BaseModel):
    """Patch payload for replacing a blueprint while keeping the same character id."""

    blueprint: CharacterBlueprint


class CharacterRecord(BaseModel):
    """Read model returned by the repository/service/API."""

    character_id: str
    blueprint: CharacterBlueprint
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @property
    def display_name(self) -> str:
        return self.blueprint.identity.display_name


def utc_now() -> datetime:
    """Return an aware UTC timestamp for character persistence."""

    return datetime.now(UTC)


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None
    return cleaned[:_MAX_SHORT_TEXT]


def _clean_string_list(values: list[str], *, max_items: int) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        normalized = " ".join(str(item).strip().split())[:_MAX_SHORT_TEXT]
        key = normalized.lower()
        if normalized and key not in seen:
            cleaned.append(normalized)
            seen.add(key)
        if len(cleaned) >= max_items:
            break
    return cleaned
