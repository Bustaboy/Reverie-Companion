"""Versioned relationship state schema for character-scoped runtime growth."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

RELATIONSHIP_STATE_VERSION = "relationship_state.v1"
MAX_SHORT_TEXT = 240
MAX_TAGS = 16


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


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class RelationshipState(BaseModel):
    """Current bond state consumed by prompt, memory, and growth systems."""

    schema_version: str = RELATIONSHIP_STATE_VERSION
    character_id: str | None = Field(default=None, max_length=80)
    affection_level: float = Field(default=0.35, ge=0.0, le=1.0)
    trust_level: float = Field(default=0.35, ge=0.0, le=1.0)
    familiarity_level: float = Field(default=0.2, ge=0.0, le=1.0)
    starting_relationship_phase: RelationshipPhase = RelationshipPhase.newly_met
    current_relationship_phase: RelationshipPhase | None = None
    relationship_dynamic: str = Field(
        default="warm, emotionally attentive companion",
        min_length=1,
        max_length=MAX_SHORT_TEXT,
    )
    user_desired_experience: str | None = Field(default=None, max_length=MAX_SHORT_TEXT)
    relationship_pacing: RelationshipPacing = RelationshipPacing.natural
    default_intimacy_level: DefaultIntimacyLevel = DefaultIntimacyLevel.romantic
    user_role_in_story: str | None = Field(default=None, max_length=MAX_SHORT_TEXT)
    dynamic_tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    active_promises: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    unresolved_threads: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    last_interaction: str | None = None
    updated_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def fill_current_phase(self) -> "RelationshipState":
        if self.current_relationship_phase is None:
            self.current_relationship_phase = self.starting_relationship_phase
        return self

    @field_validator(
        "dynamic_tags", "active_promises", "unresolved_threads", mode="after"
    )
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = value.strip().lower().replace(" ", "_")[:64]
            if item and item not in normalized:
                normalized.append(item)
        return normalized
