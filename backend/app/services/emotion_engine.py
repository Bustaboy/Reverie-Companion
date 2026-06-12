"""Deterministic emotion and prosody tagging for local TTS.

The engine is deliberately lightweight: it uses bounded keyword scoring over the
already available TTS context, recent chat text, memory/reflection snippets, and
growth notices. It never performs an LLM call and never persists new state.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal

from app.core.reflection import JournalEntry
from app.models.chat import ChatMessage, GrowthNotification
from app.models.tts import TTSContext, TTSEmotionMetadata

OrpheusEmotionTag = Literal["<moan>", "<gasp>", "<whisper>", "<sigh>", "<groan>", "<laugh>"]
IntensityModifier = Literal["subtle", "warm", "heightened", "intense", "overwhelming"]

_ALLOWED_TAGS: tuple[OrpheusEmotionTag, ...] = (
    "<moan>",
    "<gasp>",
    "<whisper>",
    "<sigh>",
    "<groan>",
    "<laugh>",
)
_TAG_RE = re.compile(r"\s*<(?:moan|gasp|whisper|sigh|groan|laugh)>\s*", re.IGNORECASE)
_ANY_ANGLE_TAG_RE = re.compile(r"\s*</?[^>\s]{1,32}>\s*")
_SENTENCE_RE = re.compile(r"([^.!?。！？]+[.!?。！？]*)(\s*)")
_MAX_ANALYSIS_CHARS = 2_500
_MAX_TTS_TAGS = 4

_EMOTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "tender": (
        "love",
        "loved",
        "darling",
        "sweetheart",
        "gentle",
        "soft",
        "safe",
        "trust",
        "close",
        "hold me",
        "miss you",
        "need you",
    ),
    "intimate": (
        "kiss",
        "kissed",
        "kissing",
        "touch",
        "touched",
        "intimate",
        "closer",
        "desire",
        "arousal",
        "tease",
        "teasing",
        "body",
        "skin",
        "breath",
        "pant",
        "shiver",
        "moan",
        "pleasure",
        "thigh",
        "hips",
        "breasts",
        "cock",
        "pussy",
        "futa",
        "slime",
        "wet",
        "heat",
        "needy",
    ),
    "concerned": (
        "anxious",
        "afraid",
        "scared",
        "worried",
        "overwhelmed",
        "panic",
        "hurt",
        "cry",
        "tears",
        "sorry",
        "boundary",
        "careful",
    ),
    "joy": (
        "laugh",
        "laughs",
        "giggle",
        "happy",
        "joy",
        "playful",
        "tease",
        "smile",
        "delighted",
        "proud",
    ),
    "surprise": ("gasp", "surprise", "surprised", "sudden", "startled", "oh!", "wow"),
    "strain": (
        "groan",
        "ache",
        "aching",
        "tremble",
        "trembling",
        "too much",
        "harder",
        "please",
        "desperate",
    ),
}

_GROWTH_INTIMACY_KEYWORDS = (
    "trust",
    "safe",
    "safety",
    "comfort",
    "reassurance",
    "attachment",
    "closer",
    "intimacy",
    "vulnerable",
)

_NSFW_KEYWORDS = (
    "arousal",
    "moan",
    "pleasure",
    "orgasm",
    "cock",
    "pussy",
    "futa",
    "slime",
    "breasts",
    "thigh",
    "hips",
    "wet",
    "sex",
    "fuck",
)


@dataclass(frozen=True)
class EmotionResult:
    """Clean visible text plus Orpheus-ready TTS text and metadata."""

    clean_text: str
    tts_text: str
    metadata: TTSEmotionMetadata


class OrpheusTagStreamFilter:
    """Strip Orpheus tags from streamed chunks, including split tags."""

    def __init__(self) -> None:
        self._pending = ""

    def filter(self, chunk: str) -> str:
        text = self._pending + chunk
        self._pending = ""
        last_open = text.rfind("<")
        last_close = text.rfind(">")
        if last_open > last_close and len(text) - last_open <= 32:
            self._pending = text[last_open:]
            text = text[:last_open]
        return strip_orpheus_tags(text)

    def flush(self) -> str:
        if not self._pending:
            return ""
        flushed = strip_orpheus_tags(self._pending)
        self._pending = ""
        return flushed


def strip_orpheus_tags(text: str) -> str:
    """Remove supported Orpheus tags and compact whitespace for visible chat text."""

    without_known_tags = _TAG_RE.sub(" ", text)
    without_unknown_short_tags = _ANY_ANGLE_TAG_RE.sub(" ", without_known_tags)
    return re.sub(r"[ \t]{2,}", " ", without_unknown_short_tags).strip()


class EmotionEngine:
    """Heuristic Orpheus emotion tag injector for Task 2D.

    Resource budget: no model residency, no network, no background job, and only
    bounded string scans over recent text. It is safe to run after a chat turn
    finishes or inside TTSService as a fallback when the chat pipeline did not
    provide pre-tagged text.
    """

    def analyze(
        self,
        *,
        text: str,
        context: TTSContext | None = None,
        recent_messages: list[ChatMessage] | None = None,
        memory_context: str = "",
        reflection_entries: list[JournalEntry] | None = None,
        growth_notification: GrowthNotification | None = None,
    ) -> EmotionResult:
        resolved_context = context or TTSContext()
        clean_text = strip_orpheus_tags(text)
        cue_text = self._cue_text(
            clean_text=clean_text,
            context=resolved_context,
            recent_messages=recent_messages or [],
            memory_context=memory_context,
            reflection_entries=reflection_entries or [],
            growth_notification=growth_notification,
        )
        scores = self._score(cue_text)
        nsfw_scene = self._contains_any(cue_text, _NSFW_KEYWORDS)
        intimate_scene = nsfw_scene or scores["intimate"] > 0 or self._growth_intimacy(cue_text)
        high_emotion = self._is_high_emotion(clean_text, cue_text, scores)
        intensity = self._intensity(
            base=resolved_context.intensity,
            scores=scores,
            high_emotion=high_emotion,
            intimate_scene=intimate_scene,
            nsfw_scene=nsfw_scene,
        )
        primary_emotion = self._primary_emotion(scores, intimate_scene=intimate_scene)
        tags = self._tags_for(
            primary_emotion=primary_emotion,
            context=resolved_context,
            high_emotion=high_emotion,
            intimate_scene=intimate_scene,
            nsfw_scene=nsfw_scene,
            intensity=intensity,
        )
        tts_text = self._inject_tags(clean_text, tags)
        metadata = TTSEmotionMetadata(
            primary_emotion=primary_emotion,
            intensity=round(intensity, 3),
            intensity_modifier=self._intensity_modifier(intensity),
            tags=list(tags),
            high_emotion=high_emotion,
            intimate_scene=intimate_scene,
            nsfw_scene=nsfw_scene,
            cue_count=sum(scores.values()),
        )
        return EmotionResult(clean_text=clean_text, tts_text=tts_text, metadata=metadata)

    def fallback_tts_text(self, text: str, context: TTSContext | None = None) -> EmotionResult:
        """Tag text using only the TTS request context when chat metadata is absent."""

        return self.analyze(text=text, context=context)

    def _cue_text(
        self,
        *,
        clean_text: str,
        context: TTSContext,
        recent_messages: list[ChatMessage],
        memory_context: str,
        reflection_entries: list[JournalEntry],
        growth_notification: GrowthNotification | None,
    ) -> str:
        pieces = [clean_text, context.emotion_hint or ""]
        pieces.extend(message.content for message in recent_messages[-6:] if message.role != "system")
        pieces.append(memory_context[-_MAX_ANALYSIS_CHARS:])
        for entry in reflection_entries[:3]:
            pieces.append(str(entry.get("character_summary") or ""))
            pieces.extend(str(theme) for theme in entry.get("themes", [])[:5])
            for insight in entry.get("insights", [])[:2]:
                if isinstance(insight, dict):
                    pieces.append(str(insight.get("summary") or ""))
        if growth_notification is not None:
            pieces.extend(
                [
                    growth_notification.message,
                    growth_notification.why or "",
                    growth_notification.theme or "",
                    growth_notification.style,
                ]
            )
        return self._normalize("\n".join(piece for piece in pieces if piece))[-_MAX_ANALYSIS_CHARS:]

    def _score(self, cue_text: str) -> defaultdict[str, int]:
        scores: defaultdict[str, int] = defaultdict(int)
        tokens = set(cue_text.split())
        for emotion, keywords in _EMOTION_KEYWORDS.items():
            for keyword in keywords:
                if self._keyword_matches(keyword, cue_text, tokens):
                    scores[emotion] += 1
        return scores

    def _keyword_matches(self, keyword: str, normalized: str, tokens: set[str]) -> bool:
        if " " in keyword or "!" in keyword:
            return keyword in normalized
        return keyword in tokens

    def _is_high_emotion(
        self, clean_text: str, cue_text: str, scores: dict[str, int]
    ) -> bool:
        punctuation_intensity = clean_text.count("!") >= 2 or clean_text.count("?") >= 3
        emphatic_caps = any(word.isupper() and len(word) >= 4 for word in clean_text.split())
        return punctuation_intensity or emphatic_caps or sum(scores.values()) >= 4 or self._contains_any(
            cue_text, ("desperate", "overwhelmed", "need you", "too much", "please")
        )

    def _intensity(
        self,
        *,
        base: float,
        scores: dict[str, int],
        high_emotion: bool,
        intimate_scene: bool,
        nsfw_scene: bool,
    ) -> float:
        score_boost = min(0.45, sum(scores.values()) * 0.06)
        scene_boost = (0.25 if intimate_scene else 0.0) + (0.25 if nsfw_scene else 0.0)
        emotion_boost = 0.3 if high_emotion else 0.0
        return max(0.0, min(2.0, base + score_boost + scene_boost + emotion_boost))

    def _primary_emotion(self, scores: dict[str, int], *, intimate_scene: bool) -> str:
        if not scores:
            return "neutral"
        if intimate_scene and scores.get("intimate", 0) >= max(scores.values()) - 1:
            return "intimate"
        return max(scores.items(), key=lambda item: item[1])[0]

    def _tags_for(
        self,
        *,
        primary_emotion: str,
        context: TTSContext,
        high_emotion: bool,
        intimate_scene: bool,
        nsfw_scene: bool,
        intensity: float,
    ) -> tuple[OrpheusEmotionTag, ...]:
        tags: list[OrpheusEmotionTag] = []
        if context.is_narration:
            if primary_emotion in {"concerned", "tender", "intimate"} or context.emotion_hint:
                tags.append("<whisper>")
            if primary_emotion == "concerned" or high_emotion:
                tags.append("<sigh>")
            return tuple(tags[:2])

        if primary_emotion in {"tender", "intimate"} or intimate_scene:
            tags.append("<whisper>")
        if primary_emotion == "concerned":
            tags.extend(["<sigh>", "<whisper>"])
        elif primary_emotion == "joy":
            tags.append("<laugh>")
        elif primary_emotion == "surprise":
            tags.append("<gasp>")
        elif primary_emotion == "strain":
            tags.append("<groan>")

        if intimate_scene and intensity >= 1.25:
            tags.append("<gasp>")
        if nsfw_scene and intensity >= 1.45:
            tags.append("<moan>")
        if high_emotion and intensity >= 1.55 and "<gasp>" not in tags:
            tags.append("<gasp>")
        if not tags and intensity >= 1.2:
            tags.append("<sigh>")

        deduped: list[OrpheusEmotionTag] = []
        for tag in tags:
            if tag not in deduped:
                deduped.append(tag)
        return tuple(deduped[:_MAX_TTS_TAGS])

    def _inject_tags(self, clean_text: str, tags: tuple[OrpheusEmotionTag, ...]) -> str:
        if not clean_text or not tags:
            return clean_text
        sentences = [match.group(1).strip() for match in _SENTENCE_RE.finditer(clean_text) if match.group(1).strip()]
        if not sentences:
            return f"{' '.join(tags)} {clean_text}".strip()
        output: list[str] = []
        for index, sentence in enumerate(sentences):
            if index < len(tags):
                output.append(f"{tags[index]} {sentence}")
            else:
                output.append(sentence)
        return " ".join(output)

    def _growth_intimacy(self, cue_text: str) -> bool:
        return self._contains_any(cue_text, _GROWTH_INTIMACY_KEYWORDS)

    def _contains_any(self, cue_text: str, keywords: tuple[str, ...]) -> bool:
        tokens = set(cue_text.split())
        return any(self._keyword_matches(keyword, cue_text, tokens) for keyword in keywords)

    def _intensity_modifier(self, intensity: float) -> IntensityModifier:
        if intensity >= 1.65:
            return "overwhelming"
        if intensity >= 1.35:
            return "intense"
        if intensity >= 1.1:
            return "heightened"
        if intensity >= 0.75:
            return "warm"
        return "subtle"

    def _normalize(self, text: str) -> str:
        return " ".join(
            "".join(character.lower() if character.isalnum() or character in {"!", "?"} else " " for character in text).split()
        )


emotion_engine = EmotionEngine()
