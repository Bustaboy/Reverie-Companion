"""Deterministic image prompt engineering for local Reverie image generation.

The engine is intentionally lightweight: it extracts bounded details from caller-
provided chat/VN/memory context and never calls an LLM on the hot path. The goal
is to preserve character continuity and scene awareness before a queued ComfyUI
job starts, while keeping RTX 4070 8GB image generation resource behavior owned
by ImageGenerationService.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

MAX_ENGINEERED_PROMPT_CHARS = 2_400
MAX_NEGATIVE_PROMPT_CHARS = 1_000
MAX_RECENT_MESSAGES = 6
MAX_FIELD_CHARS = 420
MAX_LIST_ITEMS = 8

STYLE_ANCHOR = (
    "high quality intimate visual novel scene, consistent character design, "
    "coherent anatomy, expressive body language, cinematic warm lighting"
)
CONSISTENCY_ANCHOR = (
    "preserve the character's established face, body type, hair, outfit details, "
    "mood, and personality; do not redesign the character"
)
DEFAULT_NEGATIVE_PROMPT = (
    "low quality, blurry, distorted anatomy, extra limbs, missing limbs, "
    "bad hands, inconsistent face, character redesign, wrong outfit, duplicate character, "
    "text, watermark, logo, UI overlay"
)
USER_FACE_NEGATIVE_PROMPT = "user face visible, recognizable user face, frontal user portrait, user looking at camera"

INTIMATE_TERMS = {
    "intimate",
    "nsfw",
    "sex",
    "sexual",
    "nude",
    "naked",
    "bedroom",
    "kiss",
    "kissing",
    "lap",
    "embrace",
    "aftercare",
    "arousal",
    "desire",
    "sensual",
    "futa",
    "slime",
    "moan",
    "orgasm",
    "cum",
    "cock",
    "pussy",
    "breasts",
    "thighs",
}
USER_PRESENCE_TERMS = {
    "user",
    "me",
    "my",
    "mine",
    "i ",
    "i'm",
    "i’ll",
    "i'd",
    "we",
    "us",
    "our",
    "together",
}
ACTION_HINTS = {
    "sit": "seated pose",
    "stand": "standing pose",
    "hug": "embracing pose",
    "hold": "close physical contact",
    "kiss": "kissing or near-kiss composition",
    "sleep": "resting pose",
    "dance": "dancing pose",
    "look": "focused gaze and eye contact from character",
    "touch": "tactile close-up composition",
    "smile": "soft smile",
    "cry": "tearful vulnerable expression",
    "laugh": "laughing expression",
}


@dataclass(frozen=True)
class EngineeredImagePrompt:
    """Prompt bundle produced by ImagePromptEngine."""

    prompt: str
    negative_prompt: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ImagePromptEngine:
    """Build rich, deterministic ComfyUI prompts from compact Reverie context."""

    def build(
        self,
        *,
        prompt: str | None,
        context: dict[str, Any] | None = None,
        negative_prompt: str | None = None,
    ) -> EngineeredImagePrompt:
        """Return a bounded prompt bundle for ImageGenerationService.

        ``prompt`` may be a simple user request, while ``context`` can provide
        character card/voice profile details, VN scene metadata, recent chat,
        memory tags, reflection themes, growth cues, and mood settings.
        """

        safe_context = context or {}
        simple_prompt = _clean_text(prompt or self._context_prompt(safe_context))
        character = self._character_block(safe_context)
        scene = self._scene_block(safe_context)
        recent_chat = self._recent_chat_block(safe_context)
        memory = self._memory_block(safe_context)
        mood = self._mood_block(safe_context)
        last_user_message = self._last_user_message(safe_context)
        action = self._action_block(simple_prompt, last_user_message)
        intimate = self._is_intimate(simple_prompt, safe_context, last_user_message)
        includes_user = self._includes_user(
            simple_prompt, safe_context, last_user_message
        )
        framing = self._framing_block(intimate=intimate, includes_user=includes_user)

        sections = [
            (
                f"Image request: {simple_prompt}"
                if simple_prompt
                else "Image request: current Reverie scene"
            ),
            f"Style: {STYLE_ANCHOR}",
            f"Continuity: {CONSISTENCY_ANCHOR}",
            character,
            scene,
            recent_chat,
            action,
            memory,
            mood,
            framing,
        ]
        engineered_prompt = _join_sections(sections, MAX_ENGINEERED_PROMPT_CHARS)
        engineered_negative = self._negative_prompt(
            request_negative=negative_prompt,
            context=safe_context,
            intimate=intimate,
            includes_user=includes_user,
        )
        return EngineeredImagePrompt(
            prompt=engineered_prompt,
            negative_prompt=engineered_negative,
            metadata={
                "engine": "deterministic_context_v1",
                "intimate_scene": intimate,
                "includes_user": includes_user,
                "user_face_avoidance": intimate and includes_user,
                "source_prompt": simple_prompt,
            },
        )

    def _context_prompt(self, context: dict[str, Any]) -> str:
        for key in ("prompt", "image_prompt", "request", "user_request", "description"):
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
        last_user = self._last_user_message(context)
        return last_user or ""

    def _character_block(self, context: dict[str, Any]) -> str:
        character = _first_dict(
            context, "character", "character_card", "character_details", "card"
        )
        voice_profile = _first_dict(context, "voice_profile", "voiceProfile")
        if not voice_profile:
            nested_voice = (
                _first_dict(character, "voice_profile", "voiceProfile")
                if character
                else {}
            )
            voice_profile = nested_voice
        parts: list[str] = []
        name = _first_text(
            character, "name", "display_name", "character_name"
        ) or _first_text(context, "character_name", "characterId", "character_id")
        if name:
            parts.append(f"Character: {name}")
        appearance = _collect_named_text(
            character,
            (
                "appearance",
                "physical_description",
                "body",
                "hair",
                "eyes",
                "face",
                "skin",
                "species",
                "age_appearance",
            ),
        )
        clothing = _collect_named_text(
            character, ("clothing", "outfit", "wardrobe", "accessories")
        )
        mood = _first_text(context, "mood", "emotion_hint") or _first_text(
            character, "mood", "current_mood"
        )
        personality = _collect_named_text(
            character,
            ("personality", "traits", "speaking_style", "scenario", "description"),
        )
        voice_mood = _collect_named_text(voice_profile, ("name", "type"))
        voice_metadata = _collect_named_text(
            _first_dict(voice_profile, "metadata"), ("personality", "style", "tone")
        )
        for label, value in (
            ("Appearance", appearance),
            ("Clothing", clothing),
            ("Current mood", mood),
            ("Personality", personality),
            ("Voice profile cues", voice_mood),
            ("Voice metadata", voice_metadata),
        ):
            if value:
                parts.append(f"{label}: {value}")
        return _section("Character continuity", parts)

    def _scene_block(self, context: dict[str, Any]) -> str:
        visual_state = _first_dict(
            context, "visual_state", "visualState", "vn_state", "vnScene"
        )
        scene = _first_dict(context, "scene", "current_scene", "visual_novel_scene")
        parts = []
        background = (
            _first_text(context, "background")
            or _first_text(visual_state, "background")
            or _first_text(scene, "background")
        )
        location = _first_text(context, "location") or _first_text(
            scene, "location", "setting"
        )
        pose = _first_text(visual_state, "pose") or _first_text(scene, "pose")
        expression = _first_text(visual_state, "expression") or _first_text(
            scene, "expression"
        )
        lighting = _first_text(context, "lighting") or _first_text(scene, "lighting")
        for label, value in (
            ("Background", background),
            ("Location", location),
            ("Pose", pose),
            ("Expression", expression),
            ("Lighting", lighting),
        ):
            if value:
                parts.append(f"{label}: {value}")
        scene_tags = _string_list(context.get("scene_tags") or context.get("tags"))
        if scene_tags:
            parts.append(f"Scene tags: {', '.join(scene_tags[:MAX_LIST_ITEMS])}")
        return _section("Visual novel scene", parts)

    def _recent_chat_block(self, context: dict[str, Any]) -> str:
        messages = _message_list(context)
        if not messages:
            return ""
        selected = messages[-MAX_RECENT_MESSAGES:]
        lines = []
        for message in selected:
            role = _clean_text(str(message.get("role") or "message"))[:24]
            content = _clean_text(str(message.get("content") or ""))
            if content:
                lines.append(f"{role}: {content}")
        return _section("Recent chat context", lines)

    def _memory_block(self, context: dict[str, Any]) -> str:
        parts = []
        for label, key in (
            ("Memory tags", "memory_tags"),
            ("Reflection themes", "reflection_themes"),
            ("Growth cues", "growth_cues"),
        ):
            values = _string_list(context.get(key))
            if values:
                parts.append(f"{label}: {', '.join(values[:MAX_LIST_ITEMS])}")
        memory_context = _first_text(context, "memory_context", "reflection_context")
        if memory_context:
            parts.append(f"Continuity notes: {memory_context}")
        return _section("Memory and growth continuity", parts)

    def _mood_block(self, context: dict[str, Any]) -> str:
        mood_settings = _first_dict(context, "mood_settings", "moodSettings")
        if not mood_settings:
            tts_context = _first_dict(context, "tts_context", "ttsContext")
            mood_settings = (
                _first_dict(tts_context, "mood_settings", "moodSettings")
                if tts_context
                else {}
            )
        parts = []
        for key in (
            "baseline_expressiveness",
            "emotional_sensitivity",
            "nsfw_intensity",
        ):
            value = mood_settings.get(key) if mood_settings else None
            if isinstance(value, int | float):
                parts.append(f"{key}: {value:.2f}")
        return _section("Character mood settings", parts)

    def _action_block(self, simple_prompt: str, last_user_message: str) -> str:
        text = f"{simple_prompt} {last_user_message}".lower()
        hints = [hint for term, hint in ACTION_HINTS.items() if term in text]
        if hints:
            return "Action emphasis: " + ", ".join(dict.fromkeys(hints))
        return ""

    def _framing_block(self, *, intimate: bool, includes_user: bool) -> str:
        if intimate and includes_user:
            return (
                "NSFW/privacy framing: include the user's body only as needed for the scene, "
                "but strongly avoid showing the user's face; use back view, over-shoulder view, "
                "cropped composition, obscured face, or focus on the character's face and body language."
            )
        if includes_user:
            return (
                "Privacy framing: if the user appears, keep them non-identifying; prefer over-shoulder, "
                "hands, silhouette, or cropped body framing rather than a recognizable face."
            )
        return "Framing: focus on the character and current scene composition."

    def _negative_prompt(
        self,
        *,
        request_negative: str | None,
        context: dict[str, Any],
        intimate: bool,
        includes_user: bool,
    ) -> str:
        negatives = [DEFAULT_NEGATIVE_PROMPT]
        context_negative = _first_text(context, "negative_prompt", "negativePrompt")
        if context_negative:
            negatives.append(context_negative)
        if request_negative:
            negatives.append(request_negative)
        if intimate and includes_user:
            negatives.append(USER_FACE_NEGATIVE_PROMPT)
        return _join_unique_phrases(negatives, MAX_NEGATIVE_PROMPT_CHARS)

    def _last_user_message(self, context: dict[str, Any]) -> str:
        messages = _message_list(context)
        for message in reversed(messages):
            if str(message.get("role") or "").lower() == "user":
                return _clean_text(str(message.get("content") or ""))
        return ""

    def _is_intimate(
        self, prompt: str, context: dict[str, Any], last_user_message: str
    ) -> bool:
        text = " ".join(
            [
                prompt,
                last_user_message,
                _first_text(context, "emotion_hint", "mood") or "",
                " ".join(_string_list(context.get("scene_tags"))),
                " ".join(_string_list(context.get("memory_tags"))),
            ]
        ).lower()
        return any(term in text for term in INTIMATE_TERMS)

    def _includes_user(
        self, prompt: str, context: dict[str, Any], last_user_message: str
    ) -> bool:
        if context.get("includes_user") is True or context.get("user_in_scene") is True:
            return True
        text = f" {prompt} {last_user_message} ".lower()
        return any(term in text for term in USER_PRESENCE_TERMS)


def _section(title: str, parts: list[str]) -> str:
    cleaned = [_clean_text(part) for part in parts if _clean_text(part)]
    if not cleaned:
        return ""
    return f"{title}: " + "; ".join(cleaned)


def _join_sections(sections: list[str], max_chars: int) -> str:
    cleaned = [_clean_text(section) for section in sections if _clean_text(section)]
    return _truncate(". ".join(cleaned), max_chars)


def _join_unique_phrases(values: list[str], max_chars: int) -> str:
    seen = set()
    phrases = []
    for value in values:
        for phrase in re.split(r",|;", value):
            cleaned = _clean_text(phrase).lower()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                phrases.append(_clean_text(phrase))
    return _truncate(", ".join(phrases), max_chars)


def _collect_named_text(source: dict[str, Any] | None, keys: tuple[str, ...]) -> str:
    if not source:
        return ""
    values = []
    for key in keys:
        value = source.get(key)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(_string_list(value))
        elif isinstance(value, dict):
            values.extend(_string_list(value))
    return _truncate(
        "; ".join(_clean_text(value) for value in values if _clean_text(value)),
        MAX_FIELD_CHARS,
    )


def _first_text(source: dict[str, Any] | None, *keys: str) -> str:
    if not source:
        return ""
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return _truncate(_clean_text(value), MAX_FIELD_CHARS)
        if isinstance(value, int | float | bool):
            return str(value)
    return ""


def _first_dict(source: dict[str, Any] | None, *keys: str) -> dict[str, Any]:
    if not source:
        return {}
    for key in keys:
        value = source.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _message_list(context: dict[str, Any]) -> list[dict[str, Any]]:
    raw = (
        context.get("recent_messages")
        or context.get("chat_messages")
        or context.get("messages")
        or []
    )
    if not isinstance(raw, list):
        return []
    messages = []
    for item in raw:
        if hasattr(item, "model_dump"):
            item = item.model_dump(mode="json")
        if isinstance(item, dict):
            messages.append(item)
    return messages


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_truncate(_clean_text(value), MAX_FIELD_CHARS)] if value.strip() else []
    if isinstance(value, dict):
        items = []
        for key, item in value.items():
            if isinstance(item, str | int | float | bool):
                items.append(f"{key}: {item}")
        return [
            _truncate(_clean_text(item), MAX_FIELD_CHARS)
            for item in items
            if _clean_text(item)
        ]
    if isinstance(value, list | tuple | set):
        items = []
        for item in value:
            if isinstance(item, str | int | float | bool):
                items.append(str(item))
            elif isinstance(item, dict):
                label = _first_text(item, "theme", "tag", "name", "text", "summary")
                if label:
                    items.append(label)
        return [
            _truncate(_clean_text(item), MAX_FIELD_CHARS)
            for item in items
            if _clean_text(item)
        ]
    return []


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _truncate(value: str, max_chars: int) -> str:
    cleaned = _clean_text(value)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip(" ,;.") + "…"
