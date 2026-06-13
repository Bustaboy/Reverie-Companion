"""Versioned growth policy schema for character-scoped self-learning."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GROWTH_POLICY_VERSION = "growth_policy.v1"
ReflectionFrequency = Literal["low", "balanced", "high"]
ReflectionSensitivity = Literal["conservative", "balanced", "responsive"]


class GrowthPolicy(BaseModel):
    """Per-character controls for lightweight growth and reflection cadence."""

    schema_version: str = GROWTH_POLICY_VERSION
    character_scoped_growth: bool = True
    evidence_required_for_drift: bool = True
    learning_rate: float = Field(default=0.35, ge=0.0, le=1.0)
    reflection_frequency: ReflectionFrequency = "balanced"
    reflection_sensitivity: ReflectionSensitivity = "balanced"
    journal_enabled: bool = True
    memory_promotion_enabled: bool = True
    allow_lora_candidates: bool = False
    max_growth_context_items: int = Field(default=3, ge=0, le=8)
