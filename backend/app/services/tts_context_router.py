"""Context-aware TTS voice routing for chat, VN, and RPG playback."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.tts import TTSContext
from app.models.voice import VoiceProfile
from app.services.voice_manager import VoiceManager

_QUOTED_SPEECH_RE = re.compile(r"[\"“”']([^\"“”']{2,})[\"“”']")
_SPEAKER_PREFIX_RE = re.compile(r"^\s*([\w .'-]{1,80})\s*:")


@dataclass(frozen=True)
class RoutedTTSContext:
    """Resolved context and concrete voice routing metadata."""

    context: TTSContext
    voice_profile: VoiceProfile
    backend_voice_id: str
    route_reason: str


class TTSContextRouter:
    """Resolve TTS context into a durable voice profile.

    The router deliberately uses a simple, transparent heuristic for Task 2C:
    explicit flags win, quoted lines usually mean character speech, RPG lines
    without speech cues are narration, and known character voice profile names or
    IDs can identify a speaker until richer scene metadata arrives.
    """

    def __init__(self, voice_manager: VoiceManager) -> None:
        self._voice_manager = voice_manager

    def resolve(
        self,
        *,
        text: str,
        context: TTSContext | None = None,
        voice_id: str | None = None,
        character_id: str | None = None,
    ) -> RoutedTTSContext:
        """Resolve request metadata into the profile a backend should synthesize."""

        normalized_context = self._normalize_context(
            context=context, character_id=character_id
        )
        matched_profile = self._match_character_profile(text)
        is_narration, reason = self._decide_narration(
            text=text,
            context=normalized_context,
            matched_profile=matched_profile,
        )
        effective_context = normalized_context.model_copy(
            update={"is_narration": is_narration}
        )

        if voice_id is not None:
            profile = self._voice_manager.require_voice_profile(voice_id)
            reason = f"explicit_voice:{reason}"
        elif is_narration:
            profile = self._voice_manager.ensure_default_narrator_voice()
            reason = f"narration:{reason}"
        elif effective_context.character_id is not None:
            profile = self._voice_manager.get_voice_for_character(
                effective_context.character_id
            )
            if profile is None:
                profile = self._voice_manager.ensure_default_narrator_voice()
                reason = f"character_fallback_narrator:{reason}"
            else:
                reason = f"character_assignment:{reason}"
        elif matched_profile is not None:
            profile = matched_profile
            reason = f"matched_character_profile:{reason}"
        else:
            profile = self._voice_manager.ensure_default_narrator_voice()
            reason = f"default_narrator:{reason}"

        return RoutedTTSContext(
            context=effective_context,
            voice_profile=profile,
            backend_voice_id=self._voice_manager.backend_voice_id_for_profile(profile),
            route_reason=reason,
        )

    @staticmethod
    def _normalize_context(
        *, context: TTSContext | None, character_id: str | None
    ) -> TTSContext:
        if context is None:
            return TTSContext(character_id=character_id)
        if context.character_id is None and character_id is not None:
            return context.model_copy(update={"character_id": character_id})
        return context

    def _decide_narration(
        self,
        *,
        text: str,
        context: TTSContext,
        matched_profile: VoiceProfile | None,
    ) -> tuple[bool, str]:
        """Classify text as narration or speech with explicit context first."""

        if context.is_narration:
            return True, "explicit_narration"
        if _QUOTED_SPEECH_RE.search(text):
            return False, "quoted_speech"
        if context.character_id is not None:
            return False, "explicit_character"
        if matched_profile is not None:
            return False, "matched_character_name"
        if context.mode == "rpg":
            return True, "rpg_unquoted_text"
        return False, "one_to_one_default_speech"

    def _match_character_profile(self, text: str) -> VoiceProfile | None:
        """Find a character voice profile referenced by a simple speaker cue."""

        cue = self._speaker_cue(text)
        text_lower = text.lower()
        for profile in self._voice_manager.list_voice_profiles():
            if profile.type != "character":
                continue
            names = {profile.voice_id.lower(), profile.name.lower()}
            if cue is not None and cue in names:
                return profile
            if any(f"{name}:" in text_lower for name in names):
                return profile
        return None

    @staticmethod
    def _speaker_cue(text: str) -> str | None:
        match = _SPEAKER_PREFIX_RE.match(text)
        if match is None:
            return None
        cue = match.group(1).strip().lower()
        return cue or None
