"""Low-cost weighted emotion inference for visual reactivity.

The engine uses only already-available chat, memory, reflection, and growth
metadata. It performs no model calls and is invoked only when a streamed turn is
complete, keeping the normal 8GB local chat path light and predictable.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal

from app.core.reflection import JournalEntry
from app.models.chat import ChatMessage, GrowthNotification

VisualExpression = Literal[
    "neutral", "happy", "sad", "thinking", "flirty", "surprised", "concerned"
]
VisualPose = Literal["idle", "listening", "speaking", "leaning"]
SourceName = Literal[
    "latest_user", "assistant_response", "memory", "reflection", "growth"
]

_SOURCE_WEIGHTS: dict[SourceName, float] = {
    "latest_user": 0.30,
    "assistant_response": 0.25,
    "memory": 0.20,
    "reflection": 0.15,
    "growth": 0.10,
}
_LOW_CONFIDENCE_THRESHOLD = 0.24
_GROWTH_PRIORITY_BOOST = 1.25
_DEFAULT_DECAY_MS = 45_000
_MAX_TEXT_CHARS = 2_000
_STRONG_HIT_COUNT = 3

_EMOTION_KEYWORDS: dict[VisualExpression, tuple[str, ...]] = {
    "happy": (
        "happy",
        "glad",
        "joy",
        "joyful",
        "relieved",
        "safe",
        "safety",
        "comfort",
        "comforted",
        "reassurance",
        "proud",
        "trust",
        "warm",
        "sweet",
        "grateful",
    ),
    "sad": (
        "sad",
        "hurt",
        "lonely",
        "grief",
        "cry",
        "cried",
        "tears",
        "heartbroken",
        "sorry",
        "miss",
    ),
    "concerned": (
        "anxious",
        "anxiety",
        "afraid",
        "scared",
        "worried",
        "worry",
        "overwhelmed",
        "stress",
        "stressed",
        "panic",
        "boundary",
        "repair",
    ),
    "thinking": (
        "think",
        "thinking",
        "reflect",
        "reflection",
        "learned",
        "notice",
        "noticed",
        "remember",
        "understand",
        "insight",
        "pattern",
        "promise",
    ),
    "flirty": (
        "flirt",
        "flirty",
        "tease",
        "teasing",
        "kiss",
        "blush",
        "desire",
        "intimate",
        "closer",
        "playful",
    ),
    "surprised": (
        "surprise",
        "surprised",
        "startled",
        "sudden",
        "unexpected",
        "wow",
        "really",
    ),
}

_GROWTH_CUE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "relationship_trust",
        ("trust", "safe", "safety", "steadier", "reassurance", "comfort"),
    ),
    ("repair_attention", ("repair", "boundary", "pacing", "promise", "apology")),
    ("reflective_growth", ("learn", "learned", "noticed", "reflection", "pattern", "insight")),
    ("memory_recall", ("remember", "memory", "recall", "prefers", "preference")),
)


@dataclass(frozen=True)
class EmotionSource:
    """One weighted evidence source for the final emotion vote."""

    name: SourceName
    text: str

    @property
    def weight(self) -> float:
        return _SOURCE_WEIGHTS[self.name]

    @property
    def vote_multiplier(self) -> float:
        if self.name == "growth" and self.text:
            return _GROWTH_PRIORITY_BOOST
        return 1.0


@dataclass(frozen=True)
class ToneMatch:
    expression: VisualExpression
    strength: float


@dataclass(frozen=True)
class EmotionInferenceResult:
    """Compact metadata consumed by the Svelte VN layer."""

    expression: VisualExpression
    pose: VisualPose
    confidence: float
    intensity: float
    growth_cue: str | None = None
    decay_ms: int | None = None

    def to_visual_state(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "expression": self.expression,
            "pose": self.pose,
            "confidence": round(self.confidence, 3),
            "intensity": round(self.intensity, 3),
        }
        if self.growth_cue:
            payload["growth_cue"] = self.growth_cue
            payload["decay_ms"] = self.decay_ms or _DEFAULT_DECAY_MS
        return payload


class EmotionInferenceEngine:
    """Weighted heuristic engine for end-of-turn visual reactivity."""

    def infer_visual_state(
        self,
        *,
        messages: list[ChatMessage],
        assistant_response: str,
        memory_context: str = "",
        reflection_entries: list[JournalEntry] | None = None,
        growth_notification: GrowthNotification | None = None,
    ) -> EmotionInferenceResult:
        entries = reflection_entries or []
        growth_cue = self._growth_cue(
            growth_notification=growth_notification,
            memory_context=memory_context,
            reflection_entries=entries,
        )
        scores: defaultdict[VisualExpression, float] = defaultdict(float)
        strongest_signal = 0.0

        for source in self._sources(
            messages=messages,
            assistant_response=assistant_response,
            memory_context=memory_context,
            reflection_entries=entries,
            growth_notification=growth_notification,
        ):
            match = self._classify_text(source.text)
            if match.expression == "neutral" or match.strength <= 0:
                continue
            weighted_score = source.weight * source.vote_multiplier * match.strength
            scores[match.expression] += weighted_score
            strongest_signal = max(strongest_signal, match.strength)

        if not scores:
            return self._neutral_result(growth_cue=growth_cue)

        expression, confidence = max(scores.items(), key=lambda item: item[1])
        intensity = min(1.0, strongest_signal * (0.45 + confidence))
        if confidence < _LOW_CONFIDENCE_THRESHOLD:
            return self._neutral_result(
                confidence=confidence,
                intensity=intensity,
                growth_cue=growth_cue,
            )

        return EmotionInferenceResult(
            expression=expression,
            pose=self._pose_for(expression, growth_cue),
            confidence=confidence,
            intensity=intensity,
            growth_cue=growth_cue,
            decay_ms=_DEFAULT_DECAY_MS if growth_cue else None,
        )

    def _neutral_result(
        self,
        *,
        confidence: float = 0.0,
        intensity: float = 0.0,
        growth_cue: str | None = None,
    ) -> EmotionInferenceResult:
        return EmotionInferenceResult(
            expression="neutral",
            pose="idle",
            confidence=confidence,
            intensity=intensity,
            growth_cue=growth_cue,
            decay_ms=_DEFAULT_DECAY_MS if growth_cue else None,
        )

    def _sources(
        self,
        *,
        messages: list[ChatMessage],
        assistant_response: str,
        memory_context: str,
        reflection_entries: list[JournalEntry],
        growth_notification: GrowthNotification | None,
    ) -> tuple[EmotionSource, ...]:
        return (
            EmotionSource("latest_user", self._latest_message_text(messages, role="user")),
            EmotionSource("assistant_response", assistant_response),
            EmotionSource("memory", memory_context),
            EmotionSource("reflection", self._reflection_text(reflection_entries)),
            EmotionSource("growth", self._growth_text(growth_notification)),
        )

    def _classify_text(self, text: str) -> ToneMatch:
        normalized = self._normalize(text)[-_MAX_TEXT_CHARS:]
        if not normalized:
            return ToneMatch("neutral", 0.0)

        tokens = set(normalized.split())
        ranked_matches: list[tuple[int, VisualExpression]] = []
        for emotion, keywords in _EMOTION_KEYWORDS.items():
            hits = sum(
                1
                for keyword in keywords
                if self._keyword_matches(keyword, normalized, tokens)
            )
            if hits:
                ranked_matches.append((hits, emotion))

        if not ranked_matches:
            return ToneMatch("neutral", 0.0)

        hits, expression = max(ranked_matches, key=lambda item: item[0])
        return ToneMatch(expression, min(1.0, hits / _STRONG_HIT_COUNT))

    def _keyword_matches(self, keyword: str, normalized: str, tokens: set[str]) -> bool:
        if " " in keyword:
            return keyword in normalized
        return keyword in tokens

    def _growth_cue(
        self,
        *,
        growth_notification: GrowthNotification | None,
        memory_context: str,
        reflection_entries: list[JournalEntry],
    ) -> str | None:
        growth_text = self._normalize(
            " ".join(
                [
                    self._growth_text(growth_notification),
                    memory_context[-_MAX_TEXT_CHARS:],
                    self._reflection_text(reflection_entries)[-_MAX_TEXT_CHARS:],
                ]
            )
        )
        if not growth_text:
            return None
        growth_tokens = set(growth_text.split())
        for cue, keywords in _GROWTH_CUE_KEYWORDS:
            if any(
                self._keyword_matches(keyword, growth_text, growth_tokens)
                for keyword in keywords
            ):
                return cue
        return "reflective_growth" if growth_notification else None

    def _pose_for(self, expression: VisualExpression, growth_cue: str | None) -> VisualPose:
        if growth_cue in {"relationship_trust", "repair_attention"}:
            return "leaning"
        if expression == "thinking":
            return "listening"
        if expression in {"happy", "flirty", "surprised"}:
            return "speaking"
        if expression in {"sad", "concerned"}:
            return "listening"
        return "idle"

    def _latest_message_text(self, messages: list[ChatMessage], *, role: str) -> str:
        for message in reversed(messages):
            if message.role == role:
                return message.content
        return ""

    def _reflection_text(self, entries: list[JournalEntry]) -> str:
        parts: list[str] = []
        for entry in entries[:3]:
            parts.append(str(entry.get("character_summary") or ""))
            parts.extend(str(theme) for theme in entry.get("themes", [])[:4])
            parts.extend(
                str(insight.get("summary") or "")
                for insight in entry.get("insights", [])[:3]
                if isinstance(insight, dict)
            )
        return " ".join(parts)

    def _growth_text(self, growth_notification: GrowthNotification | None) -> str:
        if growth_notification is None:
            return ""
        return " ".join(
            value
            for value in [
                growth_notification.message,
                growth_notification.why or "",
                growth_notification.theme or "",
            ]
            if value
        )

    def _normalize(self, text: str) -> str:
        return " ".join(
            "".join(
                character.lower() if character.isalnum() else " " for character in text
            ).split()
        )


emotion_inference_engine = EmotionInferenceEngine()

__all__ = ["EmotionInferenceEngine", "EmotionInferenceResult", "emotion_inference_engine"]
