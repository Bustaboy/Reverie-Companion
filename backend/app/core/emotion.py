"""Deterministic visual-state inference for Reverie's VN mode.

V1 deliberately uses bounded heuristic scoring instead of an LLM call on the
interactive chat path. Richer model-assisted interpretation can run later in
background reflection jobs, where it will not compete with streaming chat.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from app.models.chat import (
    ChatRequest,
    GrowthNotification,
    VisualExpression,
    VisualPose,
    VisualState,
)


@dataclass(frozen=True)
class WeightedTextSignal:
    """A small text source and its influence on expression scoring."""

    source: str
    text: str
    weight: float


class EmotionInferenceEngine:
    """Infer VN expression, pose, and background from bounded local signals."""

    # Growth cues and memory tags intentionally outrank immediate tone; they
    # represent recent evidence-backed growth and durable continuity signals.
    _LATEST_USER_WEIGHT = 1.25
    _ASSISTANT_WEIGHT = 1.0
    _REFLECTION_THEME_WEIGHT = 1.2
    _MEMORY_TAG_WEIGHT = 1.9
    _GROWTH_CUE_WEIGHT = 2.6

    _KEYWORDS: dict[VisualExpression, tuple[str, ...]] = {
        "happy": (
            "happy",
            "smile",
            "smiling",
            "laugh",
            "laughing",
            "joy",
            "delight",
            "excited",
            "pleased",
        ),
        "tender": (
            "gentle",
            "soft",
            "safe",
            "reassurance",
            "reassuring",
            "trust",
            "care",
            "comfort",
            "protective",
            "intimate",
        ),
        "teasing": (
            "tease",
            "teasing",
            "playful",
            "mischief",
            "smirk",
            "flirt",
            "flirty",
            "banter",
        ),
        "shy": (
            "shy",
            "bashful",
            "nervous",
            "hesitant",
            "uncertain",
            "timid",
        ),
        "embarrassed": (
            "embarrassed",
            "blush",
            "blushing",
            "flustered",
            "awkward",
            "mortified",
        ),
        "confident": (
            "confident",
            "confidence",
            "steady",
            "steadier",
            "sure",
            "assured",
            "brave",
            "growth",
        ),
        "dominant": (
            "dominant",
            "possessive",
            "commanding",
            "control",
            "assertive",
            "firm",
            "claim",
            "claiming",
        ),
        "aroused": (
            "aroused",
            "desire",
            "want",
            "heated",
            "breathless",
            "needy",
            "sensual",
            "hungry",
        ),
        "angry": (
            "angry",
            "furious",
            "mad",
            "irritated",
            "frustrated",
            "hurt",
            "argument",
            "boundary crossed",
        ),
        "sad": (
            "sad",
            "lonely",
            "grief",
            "sorry",
            "apology",
            "apologize",
            "regret",
            "miss",
            "tears",
        ),
        "surprised": (
            "surprised",
            "surprise",
            "startled",
            "sudden",
            "unexpected",
            "gasp",
            "wow",
        ),
        "neutral": (),
    }

    _STRONG_MEMORY_TAGS: dict[VisualExpression, tuple[str, ...]] = {
        "tender": ("boundary", "promise", "trust", "reassurance", "slow-burn"),
        "confident": ("growth", "confidence", "steady", "learned", "milestone"),
        "dominant": ("possessive", "dominant", "assertive", "claiming"),
    }

    _POSE_BY_EXPRESSION: dict[VisualExpression, VisualPose] = {
        "neutral": "idle",
        "happy": "leaning",
        "tender": "close",
        "teasing": "leaning",
        "shy": "guarded",
        "embarrassed": "guarded",
        "confident": "assertive",
        "dominant": "assertive",
        "aroused": "close",
        "angry": "guarded",
        "sad": "guarded",
        "surprised": "close",
    }

    _BACKGROUND_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("slime-cave", ("slime", "cave", "glow", "gel")),
        ("bedroom", ("bedroom", "bed", "sheets", "pillow")),
        ("rain-window", ("rain", "storm", "window", "thunder")),
        ("garden-night", ("garden", "flowers", "moon", "night air")),
        ("studio", ("studio", "mirror", "wardrobe", "dressing")),
    )

    def infer_visual_state(
        self,
        request: ChatRequest,
        *,
        assistant_text: str = "",
        memory_context: str = "",
        reflection_entries: Iterable[Mapping[str, Any]] = (),
        growth_notification: GrowthNotification | None = None,
        character_id: str = "reverie",
    ) -> VisualState:
        """Return a bounded visual-state guess for the current assistant turn."""

        signals = self._build_signals(
            request,
            assistant_text=assistant_text,
            memory_context=memory_context,
            reflection_entries=reflection_entries,
            growth_notification=growth_notification,
        )
        scores: dict[VisualExpression, float] = defaultdict(float)
        source_hits: list[str] = []

        for signal in signals:
            hit = self._score_signal(signal, scores)
            if hit:
                source_hits.append(signal.source)

        expression, score = self._select_expression(scores)
        sources = self._dedupe_sources(source_hits) or ["fallback_neutral"]
        growth_cue = self._growth_cue_label(growth_notification)
        if growth_cue and "growth_cue" not in sources:
            sources.insert(0, "growth_cue")

        return VisualState(
            character_id=character_id,
            emotion=expression,
            expression=expression,
            pose=self._POSE_BY_EXPRESSION[expression],
            background=self._select_background(signals),
            intensity=self._intensity(score),
            confidence=self._confidence(score, sources),
            sources=sources[:8],
            growth_cue=growth_cue,
        )

    def _build_signals(
        self,
        request: ChatRequest,
        *,
        assistant_text: str,
        memory_context: str,
        reflection_entries: Iterable[Mapping[str, Any]],
        growth_notification: GrowthNotification | None,
    ) -> list[WeightedTextSignal]:
        latest_user_message = self._latest_user_message(request)
        signals: list[WeightedTextSignal] = []
        if latest_user_message:
            signals.append(
                WeightedTextSignal(
                    "latest_message_tone",
                    latest_user_message,
                    self._LATEST_USER_WEIGHT,
                )
            )
        if assistant_text:
            signals.append(
                WeightedTextSignal(
                    "assistant_response_tone",
                    assistant_text,
                    self._ASSISTANT_WEIGHT,
                )
            )
        if memory_context:
            signals.append(
                WeightedTextSignal(
                    "memory_tags",
                    memory_context,
                    self._MEMORY_TAG_WEIGHT,
                )
            )

        reflection_text = self._reflection_theme_text(reflection_entries)
        if reflection_text:
            signals.append(
                WeightedTextSignal(
                    "reflection_themes",
                    reflection_text,
                    self._REFLECTION_THEME_WEIGHT,
                )
            )

        growth_text = self._growth_notification_text(growth_notification)
        if growth_text:
            signals.append(
                WeightedTextSignal(
                    "growth_cue",
                    growth_text,
                    self._GROWTH_CUE_WEIGHT,
                )
            )
        return signals

    def _score_signal(
        self, signal: WeightedTextSignal, scores: dict[VisualExpression, float]
    ) -> bool:
        text = self._normalize(signal.text)
        hit = False
        for expression, keywords in self._KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[expression] += signal.weight
                    hit = True

        if signal.source == "memory_tags":
            for expression, tags in self._STRONG_MEMORY_TAGS.items():
                if expression not in self._KEYWORDS:
                    continue
                for tag in tags:
                    if tag in text:
                        scores[expression] += signal.weight * 0.8
                        hit = True
        return hit

    def _select_expression(
        self, scores: dict[VisualExpression, float]
    ) -> tuple[VisualExpression, float]:
        if not scores:
            return "neutral", 0.0
        expression, score = max(
            scores.items(),
            key=lambda item: (item[1], self._tie_break_rank(item[0])),
        )
        if score <= 0:
            return "neutral", 0.0
        return expression, score

    def _select_background(self, signals: Iterable[WeightedTextSignal]) -> str:
        combined = self._normalize(" ".join(signal.text for signal in signals))
        for background, keywords in self._BACKGROUND_KEYWORDS:
            if any(keyword in combined for keyword in keywords):
                return background
        return "default"

    def _reflection_theme_text(
        self, reflection_entries: Iterable[Mapping[str, Any]]
    ) -> str:
        parts: list[str] = []
        for entry in reflection_entries:
            themes = entry.get("themes")
            if isinstance(themes, list):
                parts.extend(str(theme) for theme in themes)
            summary = entry.get("character_summary")
            if isinstance(summary, str):
                parts.append(summary)
        return " ".join(parts)

    def _growth_notification_text(
        self, growth_notification: GrowthNotification | None
    ) -> str:
        if growth_notification is None:
            return ""
        return " ".join(
            value
            for value in [
                growth_notification.theme,
                growth_notification.message,
                growth_notification.why,
            ]
            if value
        )

    def _growth_cue_label(
        self, growth_notification: GrowthNotification | None
    ) -> str | None:
        if growth_notification is None:
            return None
        return growth_notification.theme or "growth"

    def _latest_user_message(self, request: ChatRequest) -> str:
        for message in reversed(request.messages):
            if message.role == "user" and message.content.strip():
                return message.content
        return ""

    def _tie_break_rank(self, expression: VisualExpression) -> int:
        priority: list[VisualExpression] = [
            "confident",
            "tender",
            "teasing",
            "dominant",
            "aroused",
            "happy",
            "sad",
            "angry",
            "shy",
            "embarrassed",
            "surprised",
            "neutral",
        ]
        return len(priority) - priority.index(expression)

    def _intensity(self, score: float) -> float:
        if score <= 0:
            return 0.15
        return round(min(1.0, max(0.2, score / 5.0)), 3)

    def _confidence(self, score: float, sources: list[str]) -> float:
        if score <= 0:
            return 0.25
        source_bonus = min(0.18, len(sources) * 0.035)
        growth_bonus = 0.08 if "growth_cue" in sources else 0.0
        return round(min(0.95, 0.36 + (score / 10.0) + source_bonus + growth_bonus), 3)

    def _dedupe_sources(self, sources: Iterable[str]) -> list[str]:
        ordered: list[str] = []
        for source in sources:
            if source not in ordered:
                ordered.append(source)
        return ordered

    def _normalize(self, text: str) -> str:
        return text.lower().replace("_", "-")


__all__ = ["EmotionInferenceEngine", "WeightedTextSignal"]
