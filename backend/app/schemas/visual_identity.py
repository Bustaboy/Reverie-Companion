"""Versioned visual identity canon for Reverie characters."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from datetime import UTC, datetime

MAX_SHORT_TEXT = 240
MAX_LIST_ITEMS = 12
AdultAgeRangeValue = Literal[
    "early_20s_adult",
    "mid_20s_adult",
    "late_20s_adult",
    "adult_30s",
    "adult_40s_plus",
    "ageless_adult",
]


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


VISUAL_IDENTITY_PROFILE_VERSION: Literal["visual_identity_profile.v1"] = (
    "visual_identity_profile.v1"
)


class AdultOnlyVisualPolicy(BaseModel):
    """Minimal adult baseline validation for visual canon.

    This is not a generic censorship layer. It stores the hard runtime boundary
    that character visuals must remain clearly adult and must not use deliberately
    childlike sexual presentation.
    """

    schema_version: Literal["adult_only_visual_policy.v1"] = (
        "adult_only_visual_policy.v1"
    )
    clearly_adult: bool = True
    adult_age_range: AdultAgeRangeValue = "mid_20s_adult"
    adult_baseline_note: str = Field(
        default="clearly adult presentation; no underage or deliberately childlike sexual presentation",
        max_length=MAX_SHORT_TEXT,
    )
    disallow_underage_or_childlike_sexualization: bool = True

    @model_validator(mode="after")
    def validate_adult_boundary(self) -> "AdultOnlyVisualPolicy":
        if not self.clearly_adult:
            raise ValueError("Visual identity must remain clearly adult.")
        if not self.disallow_underage_or_childlike_sexualization:
            raise ValueError(
                "Visual identity must exclude underage or deliberately childlike sexual presentation."
            )
        return self


class VisualTrait(BaseModel):
    """A visual trait with provenance for mutable/evolving canon."""

    name: str = Field(..., min_length=1, max_length=80)
    value: str = Field(..., min_length=1, max_length=MAX_SHORT_TEXT)
    provenance: str = Field(
        default="creator_seed", min_length=1, max_length=MAX_SHORT_TEXT
    )
    updated_at: str = Field(default_factory=utc_now_iso)

    @field_validator("name", "value", "provenance", mode="after")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Visual trait fields cannot be empty.")
        return normalized

    def prompt_fragment(self) -> str:
        return f"{self.name}: {self.value}"


class VisualIdentityProfile(BaseModel):
    """Character-scoped visual canon and compact prompt source."""

    schema_version: Literal["visual_identity_profile.v1"] = (
        VISUAL_IDENTITY_PROFILE_VERSION
    )
    identity_anchors: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    evolving_traits: list[VisualTrait] = Field(
        default_factory=list, max_length=MAX_LIST_ITEMS
    )
    scene_mutable_traits: list[str] = Field(
        default_factory=list, max_length=MAX_LIST_ITEMS
    )
    rejected_traits: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    current_appearance: str | None = Field(default=None, max_length=480)
    adult_only_policy: AdultOnlyVisualPolicy = Field(
        default_factory=AdultOnlyVisualPolicy
    )
    updated_at: str = Field(default_factory=utc_now_iso)

    @field_validator(
        "identity_anchors", "scene_mutable_traits", "rejected_traits", mode="after"
    )
    @classmethod
    def normalize_trait_list(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = " ".join(str(value).strip().split())[:120]
            if item and item not in normalized:
                normalized.append(item)
        return normalized

    def with_evolving_trait(
        self, name: str, value: str, *, provenance: str, updated_at: str | None = None
    ) -> "VisualIdentityProfile":
        """Return a copy with one evolving trait updated with provenance."""

        replacement = VisualTrait(
            name=name,
            value=value,
            provenance=provenance,
            updated_at=updated_at or utc_now_iso(),
        )
        traits = [
            trait for trait in self.evolving_traits if trait.name != replacement.name
        ]
        traits.append(replacement)
        return self.model_copy(
            update={"evolving_traits": traits, "updated_at": replacement.updated_at}
        )

    def compact_prompt_summary(
        self, *, include_scene_mutable: bool = False, max_items: int = 4
    ) -> list[str]:
        """Bounded prompt-safe visual summary lines, never raw JSON."""

        lines: list[str] = [
            f"Adult visual baseline: clearly adult {self.adult_only_policy.adult_age_range}; no underage or deliberately childlike sexual presentation."
        ]
        if self.identity_anchors:
            lines.append(
                "Identity anchors: "
                + ", ".join(self.identity_anchors[:max_items])
                + "."
            )
        if self.current_appearance:
            lines.append(
                "Current appearance: "
                + " ".join(self.current_appearance.split())[:240]
                + "."
            )
        if self.evolving_traits:
            lines.append(
                "Evolving traits: "
                + ", ".join(
                    trait.prompt_fragment()
                    for trait in self.evolving_traits[:max_items]
                )
                + "."
            )
        if include_scene_mutable and self.scene_mutable_traits:
            lines.append(
                "Scene-mutable traits: "
                + ", ".join(self.scene_mutable_traits[:max_items])
                + "."
            )
        if self.rejected_traits:
            lines.append(
                "Avoid rejected visual traits: "
                + ", ".join(self.rejected_traits[:max_items])
                + "."
            )
        return lines[:6]
