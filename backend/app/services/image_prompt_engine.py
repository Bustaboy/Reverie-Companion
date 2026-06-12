"""Deterministic context-aware image prompt builder for local generation.

The engine is deliberately lightweight: it reads already-available chat/VN,
character, voice-profile, memory, reflection, and growth metadata and turns it
into bounded positive/negative prompt text without calling another LLM on the
hot path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.models.image import MAX_IMAGE_NEGATIVE_PROMPT_CHARS

ENGINEERED_PROMPT_MAX_CHARS = 1_800
NEGATIVE_PROMPT_MAX_CHARS = MAX_IMAGE_NEGATIVE_PROMPT_CHARS
_MAX_RECENT_MESSAGES = 6
_MAX_CONTEXT_ITEMS = 8
_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z'-]{1,}")

_INTIMATE_TERMS = {
    "intimate",
    "sensual",
    "nsfw",
    "erotic",
    "sex",
    "sexual",
    "nude",
    "naked",
    "bedroom",
    "kiss",
    "kissing",
    "embrace",
    "straddle",
    "lap",
    "afterglow",
    "futa",
    "slime",
}

_USER_PRESENCE_TERMS = {
    "me",
    "my",
    "i",
    "i'm",
    "im",
    "we",
    "us",
    "our",
    "together",
    "user",
    "viewer",
    "partner",
}

_BASE_QUALITY = (
    "high quality character illustration, emotionally coherent visual novel scene, "
    "consistent character design, polished lighting, tasteful composition"
)
_BASE_NEGATIVE = (
    "low quality, blurry, distorted anatomy, extra fingers, missing fingers, "
    "duplicate limbs, warped face, inconsistent character design, text, watermark, logo"
)
_USER_FACE_NEGATIVE = (
    "user face visible, viewer face visible, detailed face of the user, front-facing user portrait"
)


@dataclass(frozen=True)
class EngineeredImagePrompt:
    """Prompt bundle passed from the prompt engine into image generation."""

    prompt: str
    negative_prompt: str
    style_notes: list[str] = field(default_factory=list)
    framing_notes: list[str] = field(default_factory=list)
    detected_scene_tags: list[str] = field(default_factory=list)


class ImagePromptEngine:
    """Build rich, bounded prompts from compact Reverie context metadata."""

    def build(
        self,
        *,
        prompt: str,
        context: dict[str, Any] | None = None,
        negative_prompt: str | None = None,
    ) -> EngineeredImagePrompt:
        """Return deterministic prompt text with negatives and framing metadata."""

        cleaned_prompt = _clean_phrase(prompt)
        context = context or {}
        messages = self._recent_messages(context)
        last_user_message = self._last_user_message(messages)
        scene_tags = self._scene_tags(context, last_user_message, cleaned_prompt)
        intimate_scene = self._has_any(scene_tags, _INTIMATE_TERMS)
        user_in_scene = self._user_in_scene(context, last_user_message, cleaned_prompt)

        sections = [
            self._compose_subject_section(context),
            self._compose_scene_section(context),
            self._compose_action_section(cleaned_prompt, last_user_message),
            self._compose_continuity_section(context),
            self._compose_style_section(context),
        ]
        framing_notes = self._framing_notes(
            intimate_scene=intimate_scene, user_in_scene=user_in_scene
        )
        if framing_notes:
            sections.append("Framing: " + "; ".join(framing_notes))
        sections.append(_BASE_QUALITY)

        positive = self._join_sections(sections, max_chars=ENGINEERED_PROMPT_MAX_CHARS)
        negative = self._build_negative_prompt(
            provided=negative_prompt,
            intimate_scene=intimate_scene,
            user_in_scene=user_in_scene,
        )
        return EngineeredImagePrompt(
            prompt=positive,
            negative_prompt=negative,
            style_notes=self._style_notes(context),
            framing_notes=framing_notes,
            detected_scene_tags=scene_tags,
        )

    def _compose_subject_section(self, context: dict[str, Any]) -> str:
        character = _first_mapping(context, "character", "character_card", "card")
        voice_profile = _first_mapping(context, "voice_profile", "voice", "tts_voice")
        parts: list[str] = []
        name = _first_text(character, "name", "display_name", "character_name")
        if name:
            parts.append(f"{name} as the main character")
        appearance = _first_text(
            character,
            "appearance",
            "physical_description",
            "body",
            "visual_description",
        )
        clothing = _first_text(character, "clothing", "outfit", "wardrobe")
        mood = _first_text(context, "mood", "emotion", "emotion_hint") or _first_text(
            character, "mood", "current_mood"
        )
        personality = _first_text(character, "personality", "personality_summary")
        voice_traits = _text_from_mapping_values(
            voice_profile.get("metadata") if isinstance(voice_profile, dict) else {},
            keys=("personality", "tone", "style", "description"),
        )
        for value in (appearance, clothing, mood, personality, voice_traits):
            if value:
                parts.append(value)
        return "Character continuity: " + "; ".join(_dedupe(parts, limit=8)) if parts else ""

    def _compose_scene_section(self, context: dict[str, Any]) -> str:
        visual_state = _first_mapping(context, "visual_state", "vn_state", "scene")
        scene = _first_text(context, "scene", "current_scene", "location") or _first_text(
            visual_state, "scene", "location"
        )
        background = _first_text(context, "background", "current_background") or _first_text(
            visual_state, "background", "background_id"
        )
        pose = _first_text(visual_state, "pose")
        expression = _first_text(visual_state, "expression", "emotion")
        pieces = [scene, background, pose, expression]
        return "Visual novel scene: " + "; ".join(_dedupe(pieces)) if any(pieces) else ""

    def _compose_action_section(self, prompt: str, last_user_message: str) -> str:
        action = self._action_from_last_user_message(last_user_message)
        if action and action.casefold() not in prompt.casefold():
            return f"Requested image: {prompt}; recent user intent/action: {action}"
        return f"Requested image: {prompt}"

    def _compose_continuity_section(self, context: dict[str, Any]) -> str:
        pieces: list[str] = []
        pieces.extend(_list_text(context, "memory_tags", "memories", "relevant_memories"))
        pieces.extend(_list_text(context, "reflection_themes", "themes"))
        pieces.extend(_list_text(context, "growth_cues", "growth", "growth_cue"))
        mood_settings = _first_mapping(context, "mood_settings")
        if mood_settings:
            pieces.extend(self._mood_setting_phrases(mood_settings))
        if not pieces:
            return ""
        return "Continuity cues: " + "; ".join(_dedupe(pieces, limit=_MAX_CONTEXT_ITEMS))

    def _compose_style_section(self, context: dict[str, Any]) -> str:
        pieces = self._style_notes(context)
        return "Style consistency: " + "; ".join(pieces) if pieces else ""

    def _style_notes(self, context: dict[str, Any]) -> list[str]:
        character = _first_mapping(context, "character", "character_card", "card")
        pieces = _list_text(context, "style_tags", "image_style", "style")
        pieces.extend(_list_text(character, "style_tags", "visual_style"))
        if _first_text(character, "appearance", "physical_description", "visual_description"):
            pieces.append("preserve canonical hair, eyes, body type, outfit, and identifying details")
        pieces.append("same character identity across generations")
        return _dedupe(pieces, limit=6)

    def _framing_notes(self, *, intimate_scene: bool, user_in_scene: bool) -> list[str]:
        if not (intimate_scene and user_in_scene):
            return []
        return [
            "include the user's body only as needed for the scene",
            "avoid showing the user's face",
            "use over-shoulder, back view, cropped below the face, or implied POV framing",
            "keep the character's face and emotion readable",
        ]

    def _build_negative_prompt(
        self,
        *,
        provided: str | None,
        intimate_scene: bool,
        user_in_scene: bool,
    ) -> str:
        pieces = [_BASE_NEGATIVE]
        if provided:
            pieces.append(provided)
        if intimate_scene and user_in_scene:
            pieces.append(_USER_FACE_NEGATIVE)
        return self._join_sections(pieces, max_chars=NEGATIVE_PROMPT_MAX_CHARS)

    def _recent_messages(self, context: dict[str, Any]) -> list[dict[str, str]]:
        raw_messages = context.get("recent_messages") or context.get("messages") or []
        normalized: list[dict[str, str]] = []
        if isinstance(raw_messages, list):
            for item in raw_messages[-_MAX_RECENT_MESSAGES:]:
                if isinstance(item, dict):
                    role = str(item.get("role") or item.get("speaker") or "").lower()
                    text = _clean_phrase(str(item.get("content") or item.get("text") or ""))
                else:
                    role = ""
                    text = _clean_phrase(str(item))
                if text:
                    normalized.append({"role": role, "content": text})
        return normalized

    def _last_user_message(self, messages: list[dict[str, str]]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user":
                return message.get("content", "")
        return ""

    def _action_from_last_user_message(self, message: str) -> str:
        if not message:
            return ""
        # Keep this deterministic and conservative: use the latest user message as
        # action evidence, trimmed to one prompt-friendly clause.
        return _truncate_at_word(message.replace("\n", " "), 220)

    def _scene_tags(
        self, context: dict[str, Any], last_user_message: str, prompt: str
    ) -> list[str]:
        tags: list[str] = []
        tags.extend(_list_text(context, "scene_tags", "tags"))
        tags.extend(_words(prompt))
        tags.extend(_words(last_user_message))
        return _dedupe(tags, limit=32)

    def _user_in_scene(
        self, context: dict[str, Any], last_user_message: str, prompt: str
    ) -> bool:
        participants = {item.casefold() for item in _list_text(context, "participants", "subjects")}
        if participants.intersection({"user", "viewer", "partner", "self"}):
            return True
        haystack = f"{prompt} {last_user_message}".casefold()
        words = set(_words(haystack))
        return bool(words.intersection(_USER_PRESENCE_TERMS))

    def _has_any(self, values: list[str], terms: set[str]) -> bool:
        normalized = {value.casefold() for value in values}
        return bool(normalized.intersection(terms))

    def _mood_setting_phrases(self, mood_settings: dict[str, Any]) -> list[str]:
        phrases: list[str] = []
        expressive = _as_float(mood_settings.get("baseline_expressiveness"))
        sensitivity = _as_float(mood_settings.get("emotional_sensitivity"))
        nsfw = _as_float(mood_settings.get("nsfw_intensity"))
        if expressive is not None and expressive > 1.15:
            phrases.append("more expressive body language")
        if sensitivity is not None and sensitivity > 1.15:
            phrases.append("heightened emotional responsiveness")
        if nsfw is not None and nsfw > 1.15:
            phrases.append("stronger intimate mood while preserving composition clarity")
        return phrases

    def _join_sections(self, sections: list[str], *, max_chars: int) -> str:
        cleaned = [_clean_phrase(section) for section in sections if _clean_phrase(section)]
        joined = ", ".join(_dedupe(cleaned, limit=24))
        return _truncate_at_word(joined, max_chars)


def _first_mapping(context: dict[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        value = context.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _first_text(mapping: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = mapping.get(key)
        text = _value_to_text(value)
        if text:
            return text
    return ""


def _text_from_mapping_values(mapping: Any, *, keys: tuple[str, ...]) -> str:
    if not isinstance(mapping, dict):
        return ""
    return "; ".join(_dedupe([_first_text(mapping, key) for key in keys], limit=4))


def _list_text(mapping: dict[str, Any], *keys: str) -> list[str]:
    values: list[str] = []
    for key in keys:
        raw = mapping.get(key)
        if raw is None:
            continue
        if isinstance(raw, list):
            values.extend(_value_to_text(item) for item in raw)
        elif isinstance(raw, dict):
            values.extend(_value_to_text(item) for item in raw.values())
        else:
            values.append(_value_to_text(raw))
    return [value for value in values if value]


def _value_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return _clean_phrase(value)
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        for key in ("text", "summary", "theme", "tag", "name", "description"):
            if key in value:
                text = _value_to_text(value[key])
                if text:
                    return text
    return ""


def _clean_phrase(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" ,;\t\n\r")


def _truncate_at_word(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    truncated = value[: max_chars - 1].rsplit(" ", 1)[0].rstrip(" ,;")
    return truncated or value[:max_chars].rstrip()


def _dedupe(values: list[str | None], *, limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value:
            continue
        cleaned = _clean_phrase(value)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
        if limit is not None and len(result) >= limit:
            break
    return result


def _words(value: str) -> list[str]:
    return [match.group(0).casefold() for match in _WORD_RE.finditer(value)]


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
