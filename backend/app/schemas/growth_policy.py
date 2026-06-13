"""Versioned character-scoped growth policy schemas."""

from __future__ import annotations

from enum import StrEnum
from pydantic import BaseModel, Field, field_validator

GROWTH_POLICY_SCHEMA_VERSION = "growth_policy.v1"


class ReflectionFrequency(StrEnum):
    low = "low"
    balanced = "balanced"
    high = "high"


class GrowthPace(StrEnum):
    slow = "slow"
    balanced = "balanced"
    responsive = "responsive"


class GrowthPolicy(BaseModel):
    schema_version: str = GROWTH_POLICY_SCHEMA_VERSION
    character_id: str | None = Field(default=None, max_length=80)
    character_scoped_growth: bool = True
    learning_rate: float = Field(default=0.35, ge=0.0, le=1.0)
    growth_pace: GrowthPace = GrowthPace.balanced
    reflection_frequency: ReflectionFrequency = ReflectionFrequency.balanced
    reflection_after_significant_turns: int = Field(default=6, ge=1, le=100)
    evidence_required_for_drift: bool = True
    major_change_requires_approval: bool = True
    journal_visibility: str = Field(default="private_inspectable", max_length=80)
    growth_notifications_enabled: bool = True
    allowed_growth_domains: list[str] = Field(default_factory=lambda: ["preferences", "relationship", "rituals", "communication_style"], max_length=16)
    blocked_growth_domains: list[str] = Field(default_factory=lambda: ["stable_identity_without_user_edit", "underage_or_childlike_sexualization"], max_length=16)
    allow_lora_candidates: bool = False

    @field_validator("allowed_growth_domains", "blocked_growth_domains", mode="after")
    @classmethod
    def normalize_domains(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = value.strip().lower().replace(" ", "_")[:80]
            if item and item not in normalized:
                normalized.append(item)
        return normalized
