"""Low-cost weighted emotion inference for visual reactivity.

This module deliberately avoids model calls. It turns already-available chat,
memory, reflection, and growth-notice signals into compact visual_state metadata
only after a streamed turn finishes, keeping the normal token path light for 8GB
local systems.
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

_SOURCE_WEIGHTS = {
    "latest_user": 0.30,
    "assistant_response": 0.25,
    "memory": 0.20,
    "reflection": 0.15,
    "growth": 0.10,
}
_LOW_CONFIDENCE_THRESHOLD = 0.32
_GROWTH_PRIORITY_BOOST = 1.25
_DEFAULT_DECAY_MS = 45_000
_MAX_TEXT_CHARS = 2_000

_EMOTION_KEYWORDS: dict[VisualExpression, tuple[str, ...]] = {
    "happy": (
        "happy",
        "glad",
        "joy",
        "relieved",
        "safe",
        "comfort",
        "comforted",
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
        "really?",
    ),
}

_GROWTH_CUE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("relationship_trust", ("trust", "safe", "steadier", "reassurance", "comfort")),
    ("repair_attention", ("repair", "boundary", "pacing", "promise", "apology")),
    ("reflective_growth", ("learn", "learned", "noticed", "reflection", "pattern", "insight")),
    ("memory_recall", ("remember", "memory", "recall", "prefers", "preference")),
)


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
        votes: defaultdict[VisualExpression, float] = defaultdict(float)
        total_weight = 0.0
        intensity_signals: list[float] = []

        latest_user = self._latest_message_text(messages, role="user")
        sources = [
            ("latest_user", latest_user),
            ("assistant_response", assistant_response),
            ("memory", memory_context),
            ("reflection", self._reflection_text(reflection_entries or [])),
            ("growth", self._growth_text(growth_notification)),
        ]

        for source, text in sources:
            tone, strength = self._classify_text(text)
            if tone == "neutral" or strength <= 0:
                continue
            weight = _SOURCE_WEIGHTS[source]
            if source == "growth" and growth_notification is not None:
                weight *= _GROWTH_PRIORITY_BOOST
            votes[tone] += weight * strength
            total_weight += weight
            intensity_signals.append(strength)

        if not votes:
            return EmotionInferenceResult(
                expression="neutral", pose="idle", confidence=0.0, intensity=0.0
            )

        expression, score = max(votes.items(), key=lambda item: item[1])
        confidence = score / max(total_weight, 0.001)
        intensity = min(1.0, max(intensity_signals, default=0.0) * confidence)
        growth_cue = self._growth_cue(
            growth_notification=growth_notification,
            memory_context=memory_context,
            reflection_entries=reflection_entries or [],
        )

        if confidence < _LOW_CONFIDENCE_THRESHOLD:
            return EmotionInferenceResult(
                expression="neutral",
                pose="idle",
                confidence=confidence,
                intensity=intensity,
                growth_cue=growth_cue,
                decay_ms=_DEFAULT_DECAY_MS if growth_cue else None,
            )

        return EmotionInferenceResult(
            expression=expression,
            pose=self._pose_for(expression, growth_cue),
            confidence=confidence,
            intensity=intensity,
            growth_cue=growth_cue,
            decay_ms=_DEFAULT_DECAY_MS if growth_cue else None,
        )

    def _classify_text(self, text: str) -> tuple[VisualExpression, float]:
        normalized = self._normalize(text)[-_MAX_TEXT_CHARS:]
        if not normalized:
            return "neutral", 0.0

        scores: dict[VisualExpression, int] = {}
        for emotion, keywords in _EMOTION_KEYWORDS.items():
            hits = sum(1 for keyword in keywords if keyword in normalized)
            if hits:
                scores[emotion] = hits

        if not scores:
            return "neutral", 0.0

        emotion, hits = max(scores.items(), key=lambda item: item[1])
        # Three matching cues is already strong for this compact heuristic; cap
        # so repeated words cannot dominate every other weighted source.
        return emotion, min(1.0, hits / 3)

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
        for cue, keywords in _GROWTH_CUE_KEYWORDS:
            if any(keyword in growth_text for keyword in keywords):
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
        return " ".join(text.lower().split())


emotion_inference_engine = EmotionInferenceEngine()

__all__ = ["EmotionInferenceEngine", "EmotionInferenceResult", "emotion_inference_engine"]
