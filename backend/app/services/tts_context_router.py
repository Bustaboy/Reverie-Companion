"""Context-aware voice routing for Reverie TTS.

This module keeps narration/speaker decisions out of FastAPI routes and out of
backend adapters. The heuristics are intentionally simple for Milestone 3 Task
2C; emotion/prosody shaping is reserved for Task 2D.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.models.tts import TTSContext
from app.models.voice import VoiceProfile
from app.services.voice_manager import VoiceManager

TTSRoutingReason = Literal[
    "explicit_voice_id",
    "explicit_narration",
    "one_to_one_character",
    "rpg_character_speech",
    "rpg_character_name",
    "rpg_narration",
    "default_narrator",
]

_QUOTED_SPEECH_RE = re.compile(r"[\"“”‘’']")
_SPEAKER_PREFIX_RE = re.compile(r"^\s*([A-Za-z][\w .'-]{0,80})\s*:")


@dataclass(frozen=True)
class TTSRoutingDecision:
    """Resolved TTS profile and lightweight routing metadata."""

    context: TTSContext
    voice_profile: VoiceProfile
    backend_voice_id: str
    is_narration: bool
    reason: TTSRoutingReason


class TTSContextRouter:
    """Resolve TTS context into a durable voice profile and backend voice key."""

    def __init__(self, voice_manager: VoiceManager) -> None:
        self._voice_manager = voice_manager

    def route(
        self,
        *,
        text: str,
        context: TTSContext | None = None,
        voice_id: str | None = None,
        character_id: str | None = None,
    ) -> TTSRoutingDecision:
        """Choose the correct voice profile for a TTS line.

        Explicit `voice_id` remains an override for existing Task 2A/2B clients.
        Otherwise, context controls narration and character speech routing. RPG
        mode gets a small quoted-speech / speaker-prefix heuristic so future
        frontend state can pass partial context without requiring advanced NLP.
        """

        resolved_context = self._merge_context(context, character_id=character_id)
        if voice_id is not None:
            profile = self._voice_manager.require_voice_profile(voice_id)
            return self._decision(
                context=resolved_context,
                voice_profile=profile,
                is_narration=resolved_context.is_narration,
                reason="explicit_voice_id",
            )

        is_narration, reason = self._classify_text(text, resolved_context)
        if is_narration:
            profile = self._voice_manager.ensure_default_narrator_voice()
        elif resolved_context.character_id is not None:
            profile = self._voice_manager.resolve_tts_voice_profile(
                character_id=resolved_context.character_id
            )
        else:
            profile = self._voice_manager.ensure_default_narrator_voice()
            reason = "default_narrator"
            is_narration = True

        return self._decision(
            context=resolved_context.model_copy(update={"is_narration": is_narration}),
            voice_profile=profile,
            is_narration=is_narration,
            reason=reason,
        )

    def _merge_context(
        self, context: TTSContext | None, *, character_id: str | None
    ) -> TTSContext:
        resolved = context or TTSContext(character_id=character_id)
        if character_id is not None and resolved.character_id is None:
            return resolved.model_copy(update={"character_id": character_id})
        return resolved

    def _classify_text(
        self, text: str, context: TTSContext
    ) -> tuple[bool, TTSRoutingReason]:
        if context.is_narration:
            return True, "explicit_narration"

        if context.mode == "one_to_one":
            if context.character_id is not None:
                return False, "one_to_one_character"
            return True, "default_narrator"

        if context.character_id is None:
            return True, "rpg_narration"

        if self._has_character_name_marker(text, context.character_id):
            return False, "rpg_character_name"
        if _QUOTED_SPEECH_RE.search(text):
            return False, "rpg_character_speech"
        return True, "rpg_narration"

    def _has_character_name_marker(self, text: str, character_id: str) -> bool:
        speaker_match = _SPEAKER_PREFIX_RE.match(text)
        if speaker_match is None:
            return False

        speaker = self._normalize_marker(speaker_match.group(1))
        markers = {self._normalize_marker(character_id)}
        assigned_profile = self._voice_manager.get_voice_for_character(character_id)
        if assigned_profile is not None:
            markers.add(self._normalize_marker(assigned_profile.name))
            metadata_name = assigned_profile.metadata.get("character_name")
            if isinstance(metadata_name, str):
                markers.add(self._normalize_marker(metadata_name))
        return speaker in markers

    def _decision(
        self,
        *,
        context: TTSContext,
        voice_profile: VoiceProfile,
        is_narration: bool,
        reason: TTSRoutingReason,
    ) -> TTSRoutingDecision:
        resolved_context = context.model_copy(
            update={"mood_settings": voice_profile.mood_settings}
        )
        return TTSRoutingDecision(
            context=resolved_context,
            voice_profile=voice_profile,
            backend_voice_id=self._voice_manager.backend_voice_id_for_profile(
                voice_profile
            ),
            is_narration=is_narration,
            reason=reason,
        )

    @staticmethod
    def _normalize_marker(value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().casefold())
