"""Versioned visual identity canon for Reverie characters."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

VISUAL_IDENTITY_PROFILE_VERSION = "visual_identity_profile.v1"
MAX_VISUAL_TEXT = 240
MAX_VISUAL_LIST_ITEMS = 16


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class VisualTraitRecord(BaseModel):
    """A mutable visual trait with evidence for when and why it changed."""

    value: str = Field(..., min_length=1, max_length=MAX_VISUAL_TEXT)
    provenance: str = Field(..., min_length=1, max_length=MAX_VISUAL_TEXT)
    updated_at: str = Field(default_factory=utc_now_iso)

    @field_validator("value", "provenance", mode="after")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("Visual trait records need a value and provenance.")
        return normalized


class AdultOnlyVisualPolicy(BaseModel):
    """Validation guard that keeps visual canon clearly adult without over-policing style."""

    confirmed_adult: bool = True
    adult_baseline: str = Field(
        default="clearly adult 18+ presentation",
        min_length=1,
        max_length=MAX_VISUAL_TEXT,
    )
    disallow_underage_or_childlike_sexualization: bool = True
    notes: str | None = Field(default=None, max_length=MAX_VISUAL_TEXT)

    @field_validator("adult_baseline", mode="after")
    @classmethod
    def require_adult_language(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        lowered = normalized.lower()
        if not any(marker in lowered for marker in ["adult", "18+", "mature"]):
            raise ValueError(
                "Visual adult baseline must clearly describe an adult character."
            )
        return normalized

    @model_validator(mode="after")
    def validate_policy(self) -> "AdultOnlyVisualPolicy":
        if not self.confirmed_adult:
            raise ValueError("Visual identity requires a clearly adult baseline.")
        if not self.disallow_underage_or_childlike_sexualization:
            raise ValueError(
                "Visual identity cannot allow underage or childlike sexualization."
            )
        return self


class VisualIdentityProfile(BaseModel):
    """Character-scoped visual canon used by runtime prompts and future media seams."""

    schema_version: Literal["visual_identity_profile.v1"] = (
        VISUAL_IDENTITY_PROFILE_VERSION
    )
    character_id: str | None = Field(default=None, max_length=80)
    identity_anchors: list[str] = Field(
        default_factory=list, max_length=MAX_VISUAL_LIST_ITEMS
    )
    evolving_traits: dict[str, VisualTraitRecord] = Field(default_factory=dict)
    scene_mutable_traits: list[str] = Field(
        default_factory=lambda: [
            "outfit",
            "pose",
            "expression",
            "makeup",
            "lighting",
            "location",
            "camera angle",
        ],
        max_length=MAX_VISUAL_LIST_ITEMS,
    )
    rejected_traits: list[str] = Field(
        default_factory=list, max_length=MAX_VISUAL_LIST_ITEMS
    )
    current_appearance: str = Field(default="No visual canon set yet.", max_length=600)
    adult_only_policy: AdultOnlyVisualPolicy = Field(
        default_factory=AdultOnlyVisualPolicy
    )
    updated_at: str = Field(default_factory=utc_now_iso)

    @field_validator(
        "identity_anchors", "scene_mutable_traits", "rejected_traits", mode="after"
    )
    @classmethod
    def normalize_trait_lists(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = " ".join(str(value).strip().split())[:MAX_VISUAL_TEXT]
            if item and item not in normalized:
                normalized.append(item)
        return normalized

    @model_validator(mode="after")
    def require_adult_anchor(self) -> "VisualIdentityProfile":
        anchors = " ".join(self.identity_anchors).lower()
        baseline = self.adult_only_policy.adult_baseline.lower()
        if self.identity_anchors and not any(
            marker in f"{anchors} {baseline}" for marker in ["adult", "18+", "mature"]
        ):
            raise ValueError(
                "Visual identity anchors must preserve a clearly adult baseline."
            )
        return self

    def with_evolving_trait(
        self, trait: str, value: str, *, provenance: str, updated_at: str | None = None
    ) -> "VisualIdentityProfile":
        """Return a copy with one evidence-backed evolving trait updated."""

        key = trait.strip().lower().replace(" ", "_")[:80]
        if not key:
            raise ValueError("Evolving trait name cannot be empty.")
        traits = dict(self.evolving_traits)
        traits[key] = VisualTraitRecord(
            value=value, provenance=provenance, updated_at=updated_at or utc_now_iso()
        )
        return self.model_copy(
            update={"evolving_traits": traits, "updated_at": utc_now_iso()}
        )
