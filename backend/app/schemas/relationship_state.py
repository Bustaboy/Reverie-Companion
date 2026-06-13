"""Versioned character-scoped relationship state schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

RELATIONSHIP_STATE_SCHEMA_VERSION = "relationship_state.v1"
MAX_RELATIONSHIP_ITEMS = 24


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


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


class RelationshipMilestone(BaseModel):
    milestone_id: str = Field(..., min_length=1, max_length=80)
    title: str = Field(..., min_length=1, max_length=160)
    occurred_at: str = Field(default_factory=utc_now_iso)
    linked_memory_id: str | None = Field(default=None, max_length=120)
    linked_journal_id: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class RelationshipState(BaseModel):
    """Durable bond state for one character and one local user."""

    schema_version: str = RELATIONSHIP_STATE_SCHEMA_VERSION
    character_id: str | None = Field(default=None, max_length=80)
    user_id: str = Field(default="local_user", min_length=1, max_length=80)
    starting_relationship_phase: RelationshipPhase = RelationshipPhase.newly_met
    current_relationship_phase: RelationshipPhase | None = None
    phase: RelationshipPhase | None = None
    relationship_dynamic: str = Field(default="warm, emotionally attentive companion", min_length=1, max_length=240)
    trust_level: float = Field(default=0.25, ge=0.0, le=1.0)
    affection_level: float = Field(default=0.3, ge=0.0, le=1.0)
    comfort_with_closeness: float = Field(default=0.3, ge=0.0, le=1.0)
    playful_familiarity: float = Field(default=0.25, ge=0.0, le=1.0)
    romantic_pacing: RelationshipPacing = RelationshipPacing.natural
    nsfw_pacing: RelationshipPacing = RelationshipPacing.user_led
    relationship_pacing: RelationshipPacing = RelationshipPacing.natural
    default_intimacy_level: DefaultIntimacyLevel = DefaultIntimacyLevel.romantic
    user_desired_experience: str | None = Field(default=None, max_length=240)
    user_role_in_story: str | None = Field(default=None, max_length=240)
    dynamic_tags: list[str] = Field(default_factory=list, max_length=MAX_RELATIONSHIP_ITEMS)
    milestones: list[RelationshipMilestone] = Field(default_factory=list, max_length=MAX_RELATIONSHIP_ITEMS)
    unresolved_threads: list[str] = Field(default_factory=list, max_length=MAX_RELATIONSHIP_ITEMS)
    promises: list[str] = Field(default_factory=list, max_length=MAX_RELATIONSHIP_ITEMS)
    rituals: list[str] = Field(default_factory=list, max_length=MAX_RELATIONSHIP_ITEMS)
    last_interaction: str | None = None
    last_updated_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_phase_aliases(self) -> "RelationshipState":
        selected = self.phase or self.current_relationship_phase or self.starting_relationship_phase
        self.phase = selected
        self.current_relationship_phase = selected
        return self

    @field_validator("dynamic_tags", "unresolved_threads", "promises", "rituals", mode="after")
    @classmethod
    def normalize_lists(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = value.strip()
            if item and item not in normalized:
                normalized.append(item[:160])
        return normalized

    def prompt_summary(self) -> str:
        phase = self.phase or self.current_relationship_phase or self.starting_relationship_phase
        tags = f"; tags: {', '.join(self.dynamic_tags[:4])}" if self.dynamic_tags else ""
        return (
            f"{phase.value}; trust={self.trust_level:.2f}; affection={self.affection_level:.2f}; "
            f"closeness={self.comfort_with_closeness:.2f}; romantic pacing={self.romantic_pacing.value}; "
            f"NSFW pacing={self.nsfw_pacing.value}{tags}"
        )
