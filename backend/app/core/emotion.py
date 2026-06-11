"""Deterministic visual-state inference for Reverie's VN mode.

V1 deliberately uses bounded heuristic scoring instead of an LLM call on the
interactive chat path. Richer model-assisted interpretation can run later in
background reflection jobs, where it will not compete with streaming chat.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import IntEnum
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
    priority: "SignalPriority"
    priority_boost: float = 0.0


class SignalPriority(IntEnum):
    """Deterministic priority tiers for bounded visual inference signals."""

    NONE = 0
    ASSISTANT_RESPONSE_TONE = 10
    LATEST_MESSAGE_TONE = 20
    REFLECTION_THEMES = 30
    MEMORY_TAGS = 40
    STRONG_MEMORY_TAGS = 50
    GROWTH_CUE = 60


@dataclass
class ExpressionScore:
    """Accumulated bounded score and deterministic boost for one expression."""

    score: float = 0.0
    priority: SignalPriority = SignalPriority.NONE
    priority_boost: float = 0.0
    sources: list[str] | None = None

    @property
    def ranking_score(self) -> float:
        return self.score + self.priority_boost

    def add(
        self,
        amount: float,
        priority: SignalPriority,
        source: str,
        *,
        priority_boost: float = 0.0,
        source_aliases: Iterable[str] = (),
    ) -> None:
        self.score += amount
        self.priority = max(self.priority, priority)
        self.priority_boost = max(self.priority_boost, priority_boost)
        if self.sources is None:
            self.sources = []
        for source_name in (source, *source_aliases):
            if source_name not in self.sources:
                self.sources.append(source_name)


class EmotionInferenceEngine:
    """Infer VN expression, pose, and background from bounded local signals."""

    # Approved V1 blend: latest message 30%, assistant tone 25%, memory tags
    # 20%, reflection themes 15%, and growth cues 10%. Priority boosts affect
    # ranking only; they do not mutate the documented raw weighted score.
    _LATEST_USER_WEIGHT = 0.30
    _ASSISTANT_WEIGHT = 0.25
    _MEMORY_TAG_WEIGHT = 0.20
    _REFLECTION_THEME_WEIGHT = 0.15
    _GROWTH_CUE_WEIGHT = 0.10
    _GROWTH_PRIORITY_BOOST = 0.35
    _STRONG_MEMORY_PRIORITY_BOOST = 0.16

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
        "tender": (
            "attachment",
            "boundary",
            "comfort",
            "promise",
            "trust",
            "reassurance",
            "slow-burn",
            "safe",
        ),
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
        scores: dict[VisualExpression, ExpressionScore] = {}

        for signal in signals:
            self._score_signal(signal, scores)

        expression, expression_score = self._select_expression(scores)
        sources = self._ordered_sources(expression_score.sources or [])
        growth_cue = self._growth_cue_label(growth_notification)
        if growth_cue and "growth_cue" not in sources:
            sources.insert(0, "growth_cue")
        if not sources:
            sources = ["fallback_neutral"]

        return VisualState(
            character_id=character_id,
            emotion=expression,
            expression=expression,
            pose=self._POSE_BY_EXPRESSION[expression],
            background=self._select_background(signals),
            intensity=self._intensity(
                expression_score.score,
                expression_score.priority,
                expression_score.priority_boost,
            ),
            confidence=self._confidence(
                expression_score.score,
                expression_score.priority,
                expression_score.priority_boost,
                sources,
            ),
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
                    SignalPriority.LATEST_MESSAGE_TONE,
                )
            )
        if assistant_text:
            signals.append(
                WeightedTextSignal(
                    "assistant_response_tone",
                    assistant_text,
                    self._ASSISTANT_WEIGHT,
                    SignalPriority.ASSISTANT_RESPONSE_TONE,
                )
            )
        if memory_context:
            signals.append(
                WeightedTextSignal(
                    "memory_tags",
                    memory_context,
                    self._MEMORY_TAG_WEIGHT,
                    SignalPriority.MEMORY_TAGS,
                )
            )

        reflection_text = self._reflection_theme_text(reflection_entries)
        if reflection_text:
            signals.append(
                WeightedTextSignal(
                    "reflection_themes",
                    reflection_text,
                    self._REFLECTION_THEME_WEIGHT,
                    SignalPriority.REFLECTION_THEMES,
                )
            )

        growth_text = self._growth_notification_text(growth_notification)
        if growth_text:
            signals.append(
                WeightedTextSignal(
                    "growth_cue",
                    growth_text,
                    self._GROWTH_CUE_WEIGHT,
                    SignalPriority.GROWTH_CUE,
                    priority_boost=self._GROWTH_PRIORITY_BOOST,
                )
            )
        return signals

    def _score_signal(
        self, signal: WeightedTextSignal, scores: dict[VisualExpression, ExpressionScore]
    ) -> None:
        text = self._normalize(signal.text)
        matched_expressions = set(self._matching_expressions(text, self._KEYWORDS))
        for expression in matched_expressions:
            self._add_score(
                scores,
                expression,
                signal.weight,
                signal.priority,
                signal.source,
                priority_boost=signal.priority_boost,
            )

        if signal.source == "memory_tags":
            for expression in self._matching_expressions(text, self._STRONG_MEMORY_TAGS):
                amount = 0.0 if expression in matched_expressions else signal.weight
                self._add_score(
                    scores,
                    expression,
                    amount,
                    SignalPriority.STRONG_MEMORY_TAGS,
                    "strong_memory_tags",
                    priority_boost=self._STRONG_MEMORY_PRIORITY_BOOST,
                    source_aliases=("memory_tags",),
                )

    def _add_score(
        self,
        scores: dict[VisualExpression, ExpressionScore],
        expression: VisualExpression,
        amount: float,
        priority: SignalPriority,
        source: str,
        *,
        priority_boost: float = 0.0,
        source_aliases: Iterable[str] = (),
    ) -> None:
        if expression not in scores:
            scores[expression] = ExpressionScore()
        scores[expression].add(
            amount,
            priority,
            source,
            priority_boost=priority_boost,
            source_aliases=source_aliases,
        )

    def _select_expression(
        self, scores: dict[VisualExpression, ExpressionScore]
    ) -> tuple[VisualExpression, ExpressionScore]:
        if not scores:
            return "neutral", ExpressionScore()
        expression, score = max(
            scores.items(),
            key=lambda item: (
                item[1].ranking_score,
                item[1].priority,
                item[1].score,
                self._tie_break_rank(item[0]),
            ),
        )
        if score.score <= 0:
            return "neutral", ExpressionScore()
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
            insights = entry.get("insights")
            if isinstance(insights, list):
                for insight in insights:
                    if isinstance(insight, Mapping):
                        insight_summary = insight.get("summary")
                        if isinstance(insight_summary, str):
                            parts.append(insight_summary)
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

    def _matching_expressions(
        self,
        text: str,
        keyword_map: Mapping[VisualExpression, tuple[str, ...]],
    ) -> Iterable[VisualExpression]:
        for expression, keywords in keyword_map.items():
            if any(keyword in text for keyword in keywords):
                yield expression

    def _intensity(
        self, score: float, priority: SignalPriority, priority_boost: float
    ) -> float:
        if score <= 0:
            return 0.15
        priority_floor = {
            SignalPriority.GROWTH_CUE: 0.55,
            SignalPriority.STRONG_MEMORY_TAGS: 0.48,
            SignalPriority.MEMORY_TAGS: 0.42,
            SignalPriority.REFLECTION_THEMES: 0.36,
        }.get(priority, 0.2)
        return round(min(1.0, max(priority_floor, score + priority_boost)), 3)

    def _confidence(
        self,
        score: float,
        priority: SignalPriority,
        priority_boost: float,
        sources: list[str],
    ) -> float:
        if score <= 0:
            return 0.25
        source_bonus = min(0.16, len(sources) * 0.035)
        priority_bonus = {
            SignalPriority.GROWTH_CUE: 0.12,
            SignalPriority.STRONG_MEMORY_TAGS: 0.09,
            SignalPriority.MEMORY_TAGS: 0.06,
            SignalPriority.REFLECTION_THEMES: 0.04,
        }.get(priority, 0.0)
        return round(
            min(
                0.95,
                0.34
                + ((score + priority_boost) * 0.45)
                + source_bonus
                + priority_bonus,
            ),
            3,
        )

    def _ordered_sources(self, sources: Iterable[str]) -> list[str]:
        priority = [
            "growth_cue",
            "strong_memory_tags",
            "memory_tags",
            "reflection_themes",
            "latest_message_tone",
            "assistant_response_tone",
        ]
        deduped = []
        for source in sources:
            if source not in deduped:
                deduped.append(source)
        return sorted(
            deduped,
            key=lambda source: (
                priority.index(source) if source in priority else len(priority),
                source,
            ),
        )

    def _normalize(self, text: str) -> str:
        return text.lower().replace("_", "-")


__all__ = [
    "EmotionInferenceEngine",
    "ExpressionScore",
    "SignalPriority",
    "WeightedTextSignal",
]
