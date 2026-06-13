"""Deterministic quality evals for Milestone 4 character runtime hardening.

These checks are intentionally lightweight: they validate prompt artifacts and
scoping without invoking a model, keeping the suite fast and 8GB-safe.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CharacterQualityEvalResult:
    name: str
    passed: bool
    details: str


class CharacterQualityEvaluator:
    """Run basic consistency, trait adherence, and growth coherence checks."""

    def evaluate_prompt(
        self,
        prompt: str,
        *,
        character_id: str,
        character_name: str,
        required_traits: list[str],
        forbidden_phrases: list[str] | None = None,
    ) -> list[CharacterQualityEvalResult]:
        lowered = prompt.lower()
        forbidden_phrases = forbidden_phrases or [
            "as an ai",
            "i cannot engage in fictional adult",
        ]
        return [
            CharacterQualityEvalResult(
                "basic_consistency",
                character_id in prompt
                and character_name.lower() in lowered
                and "clearly adult" in lowered,
                "Prompt includes scoped character id, display name, and adult baseline.",
            ),
            CharacterQualityEvalResult(
                "trait_adherence",
                all(trait.lower() in lowered for trait in required_traits[:5]),
                "Prompt includes the selected companion's core trait anchors.",
            ),
            CharacterQualityEvalResult(
                "growth_coherence",
                "subordinate to stable canon" in lowered
                and "evidence" in lowered
                and "stable identity" in lowered,
                "Growth and memory/journal guidance are evidence-backed and cannot rewrite canon.",
            ),
            CharacterQualityEvalResult(
                "roleplay_integrity",
                "fictional adult fantasy is allowed by default" in lowered
                and not any(phrase in lowered for phrase in forbidden_phrases),
                "Fictional adult roleplay remains in-character without generic AI interruptions.",
            ),
        ]

    def assert_passes(self, results: list[CharacterQualityEvalResult]) -> None:
        failures = [result for result in results if not result.passed]
        if failures:
            details = "; ".join(
                f"{failure.name}: {failure.details}" for failure in failures
            )
            raise AssertionError(f"Character quality evals failed: {details}")
