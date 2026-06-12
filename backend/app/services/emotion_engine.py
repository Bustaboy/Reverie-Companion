"""Deterministic emotional prosody tagging for Orpheus-ready TTS text.

The engine is deliberately lightweight: it uses bounded keyword/rule scoring over
already-available chat, TTS context, memory, reflection, and growth metadata. It
never calls an LLM, never loads a model, and keeps visible chat text separate
from speech-only tags.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from app.models.chat import ChatMessage, GrowthNotification
from app.models.tts import TTSContext

EmotionScene = Literal[
    "neutral", "warm", "tender", "playful", "intimate", "high_emotion"
]

_ORPHEUS_TAGS = ("moan", "gasp", "whisper", "sigh", "groan", "laugh")
_TAG_RE = re.compile(
    r"</?(?:" + "|".join(_ORPHEUS_TAGS) + r")(?:\s+[^>]*)?>",
    re.IGNORECASE,
)
_ANY_SIMPLE_TAG_RE = re.compile(r"<\s*/?\s*[a-zA-Z][a-zA-Z0-9_-]{0,32}(?:\s+[^>]*)?>")
_SENTENCE_RE = re.compile(r"([^.!?…]+[.!?…]*)(\s*)", re.DOTALL)
_MAX_CONTEXT_CHARS = 4_000

_INTIMATE_TERMS = {
    "intimate",
    "desire",
    "kiss",
    "touch",
    "closer",
    "tease",
    "teasing",
    "moan",
    "pleasure",
    "need you",
    "want you",
    "bed",
    "body",
    "nsfw",
    "aroused",
    "climax",
    "orgasm",
    "cock",
    "pussy",
    "cum",
    "slime",
    "futa",
}
_HIGH_EMOTION_TERMS = {
    "cry",
    "tears",
    "sob",
    "scared",
    "afraid",
    "panic",
    "anxious",
    "overwhelmed",
    "desperate",
    "please",
    "need",
    "miss you",
    "love you",
    "trust",
    "safe",
    "hurt",
    "lonely",
    "finally",
}
_PLAYFUL_TERMS = {"laugh", "giggle", "tease", "playful", "grin", "smile", "joke"}
_TENDER_TERMS = {
    "soft",
    "gentle",
    "safe",
    "trust",
    "comfort",
    "reassurance",
    "warm",
    "hold",
}


@dataclass(frozen=True)
class EmotionTaggingResult:
    """Speech-only emotional prosody result and audit metadata."""

    visible_text: str
    tts_text: str
    tags: list[str]
    scene: EmotionScene
    intensity: float
    is_high_emotion: bool
    is_intimate: bool
    cues: list[str]

    def to_metadata(self) -> dict[str, Any]:
        return {
            "scene": self.scene,
            "intensity": round(self.intensity, 3),
            "tags": self.tags,
            "is_high_emotion": self.is_high_emotion,
            "is_intimate": self.is_intimate,
            "cues": self.cues,
            "visible_text_stripped": self.visible_text != self.tts_text,
        }


class EmotionEngine:
    """Rule-based Orpheus emotion tag injector for chat and TTS pipelines."""

    def strip_emotion_tags(self, text: str) -> str:
        """Remove supported speech-only tags from user-visible text."""

        without_orpheus = _TAG_RE.sub("", text)
        # Defensive cleanup for model-authored simple XML-ish tags so they never
        # leak into chat bubbles. This is intentionally conservative and applies
        # only to compact tag shapes, not arbitrary angle-bracket prose.
        without_simple_tags = _ANY_SIMPLE_TAG_RE.sub("", without_orpheus)
        return re.sub(r"[ \t]{2,}", " ", without_simple_tags).strip()

    def analyze_and_tag(
        self,
        *,
        text: str,
        tts_context: TTSContext | None = None,
        recent_messages: list[ChatMessage] | None = None,
        memory_context: str = "",
        reflection_entries: list[dict[str, Any]] | None = None,
        growth_notification: GrowthNotification | None = None,
        pretagged_tts_text: str | None = None,
    ) -> EmotionTaggingResult:
        """Return clean visible text plus an Orpheus-tagged TTS version."""

        visible_text = self.strip_emotion_tags(text)
        if pretagged_tts_text and pretagged_tts_text.strip():
            tts_text = pretagged_tts_text.strip()
            tags = self.extract_tags(tts_text)
            scene, intensity, high, intimate, cues = self._classify(
                visible_text=visible_text,
                tts_context=tts_context,
                recent_messages=recent_messages or [],
                memory_context=memory_context,
                reflection_entries=reflection_entries or [],
                growth_notification=growth_notification,
                existing_tags=tags,
            )
            return EmotionTaggingResult(
                visible_text=visible_text,
                tts_text=tts_text,
                tags=tags,
                scene=scene,
                intensity=intensity,
                is_high_emotion=high,
                is_intimate=intimate,
                cues=cues,
            )

        scene, intensity, high, intimate, cues = self._classify(
            visible_text=visible_text,
            tts_context=tts_context,
            recent_messages=recent_messages or [],
            memory_context=memory_context,
            reflection_entries=reflection_entries or [],
            growth_notification=growth_notification,
            existing_tags=[],
        )
        tags = self._tags_for_scene(
            scene=scene, intensity=intensity, is_intimate=intimate
        )
        tts_text = self._inject_tags(visible_text, tags)
        return EmotionTaggingResult(
            visible_text=visible_text,
            tts_text=tts_text,
            tags=tags,
            scene=scene,
            intensity=intensity,
            is_high_emotion=high,
            is_intimate=intimate,
            cues=cues,
        )

    def extract_tags(self, text: str) -> list[str]:
        """Return normalized Orpheus tag names in first-seen order."""

        seen: set[str] = set()
        tags: list[str] = []
        for match in _TAG_RE.finditer(text):
            tag = match.group(0).strip("< />\t\n").split()[0].lower()
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
        return tags

    def _classify(
        self,
        *,
        visible_text: str,
        tts_context: TTSContext | None,
        recent_messages: list[ChatMessage],
        memory_context: str,
        reflection_entries: list[dict[str, Any]],
        growth_notification: GrowthNotification | None,
        existing_tags: list[str],
    ) -> tuple[EmotionScene, float, bool, bool, list[str]]:
        evidence = self._evidence_text(
            visible_text=visible_text,
            tts_context=tts_context,
            recent_messages=recent_messages,
            memory_context=memory_context,
            reflection_entries=reflection_entries,
            growth_notification=growth_notification,
            existing_tags=existing_tags,
        )
        lower = evidence.casefold()
        intimate_hits = self._count_terms(lower, _INTIMATE_TERMS)
        high_hits = self._count_terms(lower, _HIGH_EMOTION_TERMS)
        playful_hits = self._count_terms(lower, _PLAYFUL_TERMS)
        tender_hits = self._count_terms(lower, _TENDER_TERMS)

        mood = tts_context.mood_settings if tts_context is not None else None
        baseline = mood.baseline_expressiveness if mood is not None else 1.0
        sensitivity = mood.emotional_sensitivity if mood is not None else 1.0
        nsfw_intensity = mood.nsfw_intensity if mood is not None else 1.0
        context_intensity = tts_context.intensity if tts_context is not None else 1.0
        scene_boost = (
            0.14 * intimate_hits * nsfw_intensity + 0.10 * high_hits * sensitivity
        )
        if growth_notification is not None:
            scene_boost += 0.10 * sensitivity
        intensity = min(
            2.0,
            max(0.15, context_intensity * baseline + scene_boost),
        )
        cues: list[str] = []
        if tts_context and tts_context.emotion_hint:
            cues.append(f"hint:{tts_context.emotion_hint.casefold()}")
        if tts_context and tts_context.scene_tags:
            cues.extend(f"scene:{tag.casefold()}" for tag in tts_context.scene_tags[:4])
        if mood is not None:
            cues.append(
                "mood:"
                f"expressive={baseline:.2f},sensitive={sensitivity:.2f},nsfw={nsfw_intensity:.2f}"
            )
        if intimate_hits:
            cues.append("intimate_scene")
        if high_hits:
            cues.append("high_emotion")
        if growth_notification is not None:
            cues.append("growth_reflection")

        hint = (
            tts_context.emotion_hint.casefold()
            if tts_context and tts_context.emotion_hint
            else ""
        )
        scene_tags = (
            {tag.casefold() for tag in tts_context.scene_tags} if tts_context else set()
        )
        is_intimate = (
            intimate_hits >= (1 if nsfw_intensity >= 1.35 else 2)
            or hint in {"intimate", "desire", "nsfw"}
            or bool(scene_tags & {"intimate", "nsfw", "desire", "aftercare"})
        )
        is_high = high_hits >= (2 if sensitivity >= 1.35 else 3) or intensity >= 1.45
        if is_intimate and intensity >= 1.25:
            return "intimate", intensity, is_high, True, cues
        if is_high:
            return "high_emotion", intensity, True, is_intimate, cues
        if playful_hits >= 2:
            return "playful", intensity, False, is_intimate, cues
        if tender_hits >= 2 or growth_notification is not None:
            return "tender", intensity, False, is_intimate, cues
        if tts_context and tts_context.emotion_hint:
            return "warm", intensity, False, is_intimate, cues
        return "neutral", intensity, False, is_intimate, cues

    def _evidence_text(
        self,
        *,
        visible_text: str,
        tts_context: TTSContext | None,
        recent_messages: list[ChatMessage],
        memory_context: str,
        reflection_entries: list[dict[str, Any]],
        growth_notification: GrowthNotification | None,
        existing_tags: list[str],
    ) -> str:
        pieces = [visible_text, memory_context]
        pieces.extend(
            message.content
            for message in recent_messages[-6:]
            if message.role != "system"
        )
        if tts_context is not None:
            pieces.extend(
                str(item)
                for item in (
                    tts_context.emotion_hint,
                    tts_context.mode,
                    tts_context.character_id,
                )
                if item
            )
            pieces.extend(tts_context.scene_tags[:6])
        for entry in reflection_entries[:3]:
            pieces.append(str(entry.get("character_summary", "")))
            pieces.extend(str(theme) for theme in entry.get("themes", [])[:5])
            pieces.extend(
                str(insight.get("summary", ""))
                for insight in entry.get("insights", [])[:3]
                if isinstance(insight, dict)
            )
        if growth_notification is not None:
            pieces.extend(
                part
                for part in (
                    growth_notification.message,
                    growth_notification.why,
                    growth_notification.theme,
                    growth_notification.style,
                )
                if part
            )
        pieces.extend(existing_tags)
        return "\n".join(pieces)[-_MAX_CONTEXT_CHARS:]

    def _tags_for_scene(
        self, *, scene: EmotionScene, intensity: float, is_intimate: bool
    ) -> list[str]:
        if scene == "neutral":
            return []
        if scene == "playful":
            return ["laugh"] if intensity < 1.35 else ["laugh", "sigh"]
        if scene == "tender":
            return ["sigh", "whisper"] if intensity >= 1.15 else ["sigh"]
        if scene == "warm":
            return ["whisper"]
        if scene == "high_emotion":
            return ["gasp", "sigh"] if intensity < 1.55 else ["gasp", "sigh", "groan"]
        if scene == "intimate":
            if intensity >= 1.6:
                return ["whisper", "gasp", "moan", "groan"]
            if is_intimate:
                return ["whisper", "gasp", "moan"]
            return ["whisper", "gasp"]
        return []

    def _inject_tags(self, visible_text: str, tags: list[str]) -> str:
        if not tags or not visible_text:
            return visible_text
        prefix = " ".join(f"<{tag}>" for tag in tags[:3])
        if len(visible_text) < 180 or len(tags) <= 2:
            return f"{prefix} {visible_text}"

        sentences = _SENTENCE_RE.findall(visible_text)
        if len(sentences) < 2:
            return f"{prefix} {visible_text}"
        rebuilt: list[str] = []
        inserted_second = False
        for index, (sentence, spacing) in enumerate(sentences):
            if index == 0:
                rebuilt.append(f"{prefix} {sentence}{spacing}")
            elif not inserted_second:
                rebuilt.append(f"<{tags[-1]}> {sentence}{spacing}")
                inserted_second = True
            else:
                rebuilt.append(f"{sentence}{spacing}")
        return "".join(rebuilt).strip()

    @staticmethod
    def _count_terms(text: str, terms: set[str]) -> int:
        return sum(1 for term in terms if term in text)


emotion_engine = EmotionEngine()
