"""Persistent voice profile management for Reverie's local TTS system."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.core.config import Settings
from app.models.voice import VoiceProfile

logger = logging.getLogger(__name__)


class VoiceManagerError(Exception):
    """Base class for recoverable voice profile management failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "voice_manager_error",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class VoiceProfileNotFound(VoiceManagerError):
    """Raised when a requested voice profile does not exist."""


class VoiceProfileAlreadyExists(VoiceManagerError):
    """Raised when creating a voice profile with a duplicate ID."""


class VoiceProfileStore(BaseModel):
    """Versioned JSON payload persisted by :class:`VoiceManager`."""

    schema_version: int = 1
    voices: dict[str, VoiceProfile] = Field(default_factory=dict)
    character_assignments: dict[str, str] = Field(default_factory=dict)


class VoiceManager:
    """Load, persist, and resolve voice profiles for narrator and characters.

    The manager is intentionally lightweight: a local JSON file is enough for
    MVP/Alpha profile routing, keeps startup cheap on 8GB systems, and leaves a
    clean boundary for moving to SQLite or a richer repository later.
    """

    def __init__(
        self, settings: Settings, *, store_path: str | Path | None = None
    ) -> None:
        self._settings = settings
        configured_path = store_path or settings.voice_profiles_path
        self._store_path = Path(configured_path).expanduser()
        self._store = self._load_store()

    @property
    def store_path(self) -> Path:
        """Return the JSON store path used by this manager."""

        return self._store_path

    def list_voices(self) -> list[VoiceProfile]:
        """Return all known voice profiles sorted by voice ID for stable UIs."""

        return [self._store.voices[key] for key in sorted(self._store.voices)]

    def get_voice_profile(self, voice_id: str) -> VoiceProfile | None:
        """Return a voice profile by ID, or ``None`` when it is unknown."""

        return self._store.voices.get(
            self._normalize_id(voice_id, field_name="voice_id")
        )

    def require_voice_profile(self, voice_id: str) -> VoiceProfile:
        """Return a voice profile by ID or raise a typed not-found error."""

        normalized_voice_id = self._normalize_id(voice_id, field_name="voice_id")
        profile = self._store.voices.get(normalized_voice_id)
        if profile is None:
            raise VoiceProfileNotFound(
                "Voice profile was not found.",
                code="voice_profile_not_found",
                details={"voice_id": normalized_voice_id},
            )
        return profile

    def get_default_narrator_voice(self) -> VoiceProfile:
        """Return the configured default narrator voice, creating it if needed."""

        return self.ensure_default_narrator_voice()

    def ensure_default_narrator_voice(self) -> VoiceProfile:
        """Ensure a default narrator voice exists and persist it when missing."""

        default_voice_id = self._settings.voice_default_narrator_voice_id
        existing = self._store.voices.get(default_voice_id)
        if existing is not None:
            return existing

        default_profile = VoiceProfile(
            voice_id=default_voice_id,
            name=self._settings.voice_default_narrator_name,
            type="narrator",
            reference_audio_path=None,
            metadata={
                "system_default": True,
                "backend_hint": self._settings.tts_primary_backend,
                "cloning_ready": False,
            },
        )
        self._store.voices[default_profile.voice_id] = default_profile
        self._save_store()
        logger.info(
            "Created default narrator voice profile",
            extra={"voice_id": default_profile.voice_id, "path": str(self._store_path)},
        )
        return default_profile

    def create_voice_profile(self, profile: VoiceProfile) -> VoiceProfile:
        """Create and persist a new voice profile."""

        if profile.voice_id in self._store.voices:
            raise VoiceProfileAlreadyExists(
                "Voice profile already exists.",
                code="voice_profile_already_exists",
                details={"voice_id": profile.voice_id},
            )
        self._store.voices[profile.voice_id] = profile
        self._save_store()
        return profile

    def update_voice_profile(self, voice_id: str, **updates: Any) -> VoiceProfile:
        """Patch and persist an existing voice profile.

        ``voice_id`` is stable and cannot be renamed through this method; callers
        should create a new profile and migrate assignments if they need a new ID.
        """

        existing = self.require_voice_profile(voice_id)
        updates.pop("voice_id", None)
        updated = existing.model_copy(update=updates)
        updated = VoiceProfile.model_validate(updated.model_dump())
        self._store.voices[existing.voice_id] = updated
        self._save_store()
        return updated

    def delete_voice_profile(self, voice_id: str) -> None:
        """Delete a voice profile and remove character assignments that used it."""

        profile = self.require_voice_profile(voice_id)
        default_voice_id = self._settings.voice_default_narrator_voice_id
        if profile.voice_id == default_voice_id:
            raise VoiceManagerError(
                "The default narrator voice cannot be deleted.",
                code="voice_default_narrator_delete_forbidden",
                details={"voice_id": profile.voice_id},
            )

        del self._store.voices[profile.voice_id]
        self._store.character_assignments = {
            character_id: assigned_voice_id
            for character_id, assigned_voice_id in self._store.character_assignments.items()
            if assigned_voice_id != profile.voice_id
        }
        self._save_store()

    def assign_voice_to_character(
        self, character_id: str, voice_id: str
    ) -> VoiceProfile:
        """Assign an existing voice profile to a character and persist it."""

        normalized_character_id = self._normalize_id(
            character_id, field_name="character_id"
        )
        profile = self.require_voice_profile(voice_id)
        self._store.character_assignments[normalized_character_id] = profile.voice_id
        self._save_store()
        return profile

    def clear_character_voice(self, character_id: str) -> None:
        """Remove a character-specific voice assignment, if one exists."""

        normalized_character_id = self._normalize_id(
            character_id, field_name="character_id"
        )
        if (
            self._store.character_assignments.pop(normalized_character_id, None)
            is not None
        ):
            self._save_store()

    def get_voice_for_character(self, character_id: str) -> VoiceProfile | None:
        """Return a character assignment or configured fallback voice.

        ``voice_default_character_behavior='narrator'`` reuses the narrator when
        no character voice exists. ``'none'`` returns ``None`` so a caller can
        choose to keep text silent or ask the user to pick a voice.
        """

        normalized_character_id = self._normalize_id(
            character_id, field_name="character_id"
        )
        assigned_voice_id = self._store.character_assignments.get(
            normalized_character_id
        )
        if assigned_voice_id is not None:
            profile = self._store.voices.get(assigned_voice_id)
            if profile is not None:
                return profile
            logger.warning(
                "Character voice assignment points to a missing profile",
                extra={
                    "character_id": normalized_character_id,
                    "voice_id": assigned_voice_id,
                },
            )
        if self._settings.voice_default_character_behavior == "narrator":
            return self.get_default_narrator_voice()
        return None

    def resolve_voice_profile(
        self, *, voice_id: str | None = None, character_id: str | None = None
    ) -> VoiceProfile:
        """Resolve the profile TTS should use for a request."""

        if voice_id is not None:
            return self.require_voice_profile(voice_id)
        if character_id is not None:
            profile = self.get_voice_for_character(character_id)
            if profile is not None:
                return profile
        return self.get_default_narrator_voice()

    def _load_store(self) -> VoiceProfileStore:
        if not self._store_path.exists():
            return VoiceProfileStore()
        try:
            payload = json.loads(self._store_path.read_text(encoding="utf-8"))
            return VoiceProfileStore.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise VoiceManagerError(
                "Voice profile store could not be loaded.",
                code="voice_profile_store_invalid",
                details={"path": str(self._store_path)},
            ) from exc

    def _save_store(self) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._store.model_dump(mode="json")
        self._store_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    @staticmethod
    def _normalize_id(value: str, *, field_name: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise VoiceManagerError(
                f"{field_name} cannot be empty.",
                code=f"{field_name}_empty",
                details={field_name: value},
            )
        return normalized
