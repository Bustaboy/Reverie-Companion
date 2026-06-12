"""Cheap weighted emotion inference for completed chat turns.

The engine is deliberately heuristic: it adds no resident model to the normal
chat path, uses only text/metadata already assembled for the turn, and runs once
when a response is complete so streaming latency stays untouched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Literal

from app.core.reflection import JournalEntry
from app.models.chat import (
    ChatMessage,
    ChatRequest,
    GrowthNotification,
    VisualStateMetadata,
)

Emotion = Literal[
    "neutral", "happy", "sad", "thinking", "flirty", "surprised", "concerned"
]

_WEIGHTS = {
    "latest_user": 0.30,
    "assistant": 0.25,
    "memory": 0.20,
    "reflection": 0.15,
    "growth": 0.10,
}
_LOW_CONFIDENCE_FALLBACK = 0.34
_MIN_WINNING_MARGIN = 0.06
_GROWTH_PRIORITY_BOOST = 0.08
_MAX_SIGNAL_CHARS = 4_000

_EMOTION_KEYWORDS: dict[Emotion, tuple[str, ...]] = {
    "happy": (
        "love",
        "like",
        "happy",
        "glad",
        "great",
        "good",
        "safe",
        "trust",
        "proud",
        "sweet",
        "gentle",
        "comfort",
        "relieved",
        "thank",
        "thanks",
        "smile",
        "laugh",
        "excited",
    ),
    "sad": (
        "sad",
        "lonely",
        "miss",
        "grief",
        "cry",
        "hurt",
        "heartbroken",
        "depressed",
        "empty",
    ),
    "concerned": (
        "anxious",
        "afraid",
        "worried",
        "worry",
        "scared",
        "nervous",
        "uncomfortable",
        "boundary",
        "boundaries",
        "consent",
        "unsafe",
        "overwhelmed",
        "sorry",
        "repair",
        "frustrated",
        "angry",
    ),
    "thinking": (
        "think",
        "thinking",
        "wonder",
        "curious",
        "learn",
        "remember",
        "reflect",
        "journal",
        "question",
        "understand",
        "maybe",
        "plan",
        "practice",
        "growth",
        "change",
        "improve",
    ),
    "flirty": (
        "flirt",
        "flirty",
        "tease",
        "playful",
        "kiss",
        "cuddle",
        "sensual",
        "desire",
        "intimate",
        "close",
        "blush",
        "shy",
    ),
    "surprised": (
        "surprised",
        "startled",
        "sudden",
        "wow",
        "unexpected",
        "shock",
        "really?",
        "oh!",
    ),
    "neutral": ("calm", "steady", "quiet", "okay", "fine"),
}

_THEME_TO_EMOTION: dict[str, Emotion] = {
    "affection": "happy",
    "trust": "happy",
    "boundaries": "concerned",
    "reassurance": "concerned",
    "playfulness": "flirty",
    "curiosity": "thinking",
    "conflict": "concerned",
    "intimacy": "flirty",
    "routine": "thinking",
    "growth": "thinking",
}

_POSE_BY_EMOTION: dict[Emotion, str] = {
    "neutral": "idle",
    "happy": "speaking",
    "sad": "listening",
    "thinking": "listening",
    "flirty": "leaning",
    "surprised": "speaking",
    "concerned": "listening",
}

_TOKEN_RE = re.compile(r"[a-z0-9']+")


@dataclass
class EmotionInferenceContext:
    """Inputs available after the assistant response has completed."""

    request: ChatRequest
    assistant_response: str
    memory_context: str = ""
    reflection_entries: list[JournalEntry] = field(default_factory=list)
    growth_notification: GrowthNotification | None = None


@dataclass(frozen=True)
class _ToneSignal:
    emotion: Emotion
    confidence: float


class EmotionInferenceEngine:
    """Weighted deterministic emotion inference for Reverie's visual layer."""

    def infer(self, context: EmotionInferenceContext) -> VisualStateMetadata:
        scores: dict[Emotion, float] = {emotion: 0.0 for emotion in _EMOTION_KEYWORDS}
        evidence_weights = 0.0

        evidence_weights += self._add_signal(
            scores,
            self._tone_from_text(self._latest_user_message(context.request)),
            _WEIGHTS["latest_user"],
        )
        evidence_weights += self._add_signal(
            scores,
            self._tone_from_text(context.assistant_response),
            _WEIGHTS["assistant"],
        )
        evidence_weights += self._add_signal(
            scores, self._tone_from_memory(context.memory_context), _WEIGHTS["memory"]
        )
        evidence_weights += self._add_signal(
            scores,
            self._tone_from_reflections(context.reflection_entries),
            _WEIGHTS["reflection"],
        )

        growth_signal, growth_cue = self._tone_from_growth(
            context.growth_notification, context.reflection_entries
        )
        growth_weight = self._add_signal(scores, growth_signal, _WEIGHTS["growth"])
        evidence_weights += growth_weight
        if growth_signal is not None and growth_cue:
            scores[growth_signal.emotion] += _GROWTH_PRIORITY_BOOST

        emotion, confidence = self._choose_emotion(
            scores, evidence_weights, growth_priority=bool(growth_cue)
        )
        themes = self._reflection_themes(context.reflection_entries)
        if emotion == "neutral":
            growth_cue = None

        return VisualStateMetadata(
            expression=emotion,
            pose=_POSE_BY_EMOTION[emotion],
            confidence=round(confidence, 3),
            emotion=emotion,
            growth_cue=growth_cue,
            memory_recall_used=bool(context.memory_context.strip()),
            reflection_themes=themes[:4],
        )

    def _add_signal(
        self, scores: dict[Emotion, float], signal: _ToneSignal | None, weight: float
    ) -> float:
        if signal is None or signal.confidence <= 0:
            return 0.0
        scores[signal.emotion] += weight * signal.confidence
        return weight * signal.confidence

    def _choose_emotion(
        self,
        scores: dict[Emotion, float],
        evidence_weights: float,
        *,
        growth_priority: bool = False,
    ) -> tuple[Emotion, float]:
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        winner, winning_score = ranked[0]
        runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
        confidence = min(
            1.0, winning_score + max(0.0, evidence_weights - winning_score) * 0.15
        )
        min_confidence = 0.24 if growth_priority else _LOW_CONFIDENCE_FALLBACK
        min_margin = 0.025 if growth_priority else _MIN_WINNING_MARGIN
        if (
            winner == "neutral"
            or confidence < min_confidence
            or (winning_score - runner_up) < min_margin
        ):
            return "neutral", min(confidence, 0.33)
        return winner, confidence

    def _tone_from_text(self, text: str) -> _ToneSignal | None:
        tokens = self._tokens(text[:_MAX_SIGNAL_CHARS])
        if not tokens:
            return None
        token_set = set(tokens)
        counts: dict[Emotion, int] = {}
        for emotion, keywords in _EMOTION_KEYWORDS.items():
            count = sum(
                1
                for keyword in keywords
                if self._keyword_matches(keyword, token_set, text)
            )
            if count:
                counts[emotion] = count
        if not counts:
            return None
        emotion, count = max(counts.items(), key=lambda item: item[1])
        total = sum(counts.values())
        confidence = min(
            1.0, 0.42 + (count / max(total, 1)) * 0.46 + min(count, 4) * 0.03
        )
        return _ToneSignal(emotion=emotion, confidence=confidence)

    def _tone_from_memory(self, memory_context: str) -> _ToneSignal | None:
        if not memory_context.strip():
            return None
        signal = self._tone_from_text(memory_context)
        if signal is None:
            return _ToneSignal(emotion="thinking", confidence=0.38)
        # Retrieved memory is meaningful, but it should not overpower current tone unless strong.
        return _ToneSignal(
            emotion=signal.emotion, confidence=min(1.0, signal.confidence + 0.08)
        )

    def _tone_from_reflections(
        self, entries: Iterable[JournalEntry]
    ) -> _ToneSignal | None:
        themes = self._reflection_themes(entries)
        if not themes:
            return None
        emotions: dict[Emotion, int] = {}
        for theme in themes:
            emotion = _THEME_TO_EMOTION.get(theme)
            if emotion:
                emotions[emotion] = emotions.get(emotion, 0) + 1
        if not emotions:
            return None
        emotion, count = max(emotions.items(), key=lambda item: item[1])
        confidence = min(1.0, 0.44 + count * 0.12)
        return _ToneSignal(emotion=emotion, confidence=confidence)

    def _tone_from_growth(
        self, notification: GrowthNotification | None, entries: Iterable[JournalEntry]
    ) -> tuple[_ToneSignal | None, str | None]:
        if notification is not None:
            text = " ".join(
                part
                for part in [notification.theme, notification.message, notification.why]
                if part
            )
            signal = self._tone_from_text(text) or _ToneSignal(
                emotion=_THEME_TO_EMOTION.get(
                    (notification.theme or "").lower(), "thinking"
                ),
                confidence=0.68,
            )
            return signal, (notification.theme or "growth").lower()

        for theme in self._reflection_themes(entries):
            if theme == "growth":
                return _ToneSignal(emotion="thinking", confidence=0.58), "growth"
        return None, None

    def _reflection_themes(self, entries: Iterable[JournalEntry]) -> list[str]:
        themes: list[str] = []
        for entry in entries:
            for raw_theme in entry.get("themes", []):
                theme = str(raw_theme).strip().lower()
                if theme and theme not in themes:
                    themes.append(theme)
            for insight in entry.get("insights", []):
                if not isinstance(insight, dict):
                    continue
                for raw_theme in insight.get("themes", []):
                    theme = str(raw_theme).strip().lower()
                    if theme and theme not in themes:
                        themes.append(theme)
        return themes

    def _latest_user_message(self, request: ChatRequest) -> str:
        for message in reversed(request.messages):
            if isinstance(message, ChatMessage) and message.role == "user":
                return message.content
        return ""

    def _tokens(self, text: str) -> list[str]:
        return [
            match.group(0).lower().strip("'")
            for match in _TOKEN_RE.finditer(text.lower())
        ]

    def _keyword_matches(self, keyword: str, token_set: set[str], text: str) -> bool:
        if " " in keyword or "?" in keyword or "!" in keyword:
            return keyword in text.lower()
        return keyword in token_set


__all__ = ["EmotionInferenceContext", "EmotionInferenceEngine"]
