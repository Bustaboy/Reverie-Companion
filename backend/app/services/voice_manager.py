"""Local voice profile management for Reverie TTS.

The manager keeps profile persistence lightweight and local-first: a single JSON
file stores voice profiles plus character-to-voice assignments. It deliberately
stores reference audio paths and metadata for future zero-shot cloning adapters
without implementing cloning logic in this milestone.
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any

from app.core.config import Settings
from app.models.voice import VoiceProfile, VoiceProfileUpdate

logger = logging.getLogger(__name__)


class VoiceManagerError(Exception):
    """Base class for recoverable voice profile management errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "voice_manager_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class VoiceProfileNotFound(VoiceManagerError):
    """Raised when a requested voice profile does not exist."""


class VoiceProfileConflict(VoiceManagerError):
    """Raised when creating a profile would overwrite an existing profile."""


class VoiceManager:
    """CRUD and assignment workflow for durable local voice profiles."""

    def __init__(
        self, settings: Settings, *, store_path: str | Path | None = None
    ) -> None:
        self._settings = settings
        self._store_path = Path(
            store_path or settings.voice_profile_store_path
        ).expanduser()
        self._lock = RLock()
        self._voices: dict[str, VoiceProfile] = {}
        self._character_voice_assignments: dict[str, str] = {}
        self._load()

    @property
    def store_path(self) -> Path:
        """Return the JSON path backing this manager."""

        return self._store_path

    def ensure_default_narrator_voice(self) -> VoiceProfile:
        """Create the configured narrator profile when no narrator exists."""

        with self._lock:
            existing = self.get_default_narrator_voice()
            if existing is not None:
                return existing

            default_voice_id = self._settings.voice_default_narrator_voice_id
            profile = VoiceProfile(
                voice_id=default_voice_id,
                name="Default Narrator",
                type="narrator",
                reference_audio_path=None,
                metadata={
                    "backend_voice_id": self._settings.tts_default_voice_id,
                    "created_by": "reverie_startup",
                    "cloning_ready": False,
                },
            )
            self._voices[profile.voice_id] = profile
            self._save_locked()
            logger.info(
                "Created default narrator voice profile",
                extra={"voice_id": profile.voice_id},
            )
            return profile

    def list_voice_profiles(self) -> list[VoiceProfile]:
        """Return all profiles sorted by display name for stable UI rendering."""

        with self._lock:
            return sorted(
                self._voices.values(),
                key=lambda profile: (profile.name, profile.voice_id),
            )

    def get_voice_profile(self, voice_id: str) -> VoiceProfile | None:
        """Return a voice profile by ID, or None when it does not exist."""

        with self._lock:
            return self._voices.get(voice_id.strip())

    def require_voice_profile(self, voice_id: str) -> VoiceProfile:
        """Return a voice profile or raise a typed not-found error."""

        profile = self.get_voice_profile(voice_id)
        if profile is None:
            raise VoiceProfileNotFound(
                "Voice profile was not found.",
                code="voice_profile_not_found",
                details={"voice_id": voice_id},
            )
        return profile

    def get_default_narrator_voice(self) -> VoiceProfile | None:
        """Return the configured narrator profile, falling back to any narrator."""

        with self._lock:
            configured = self._voices.get(
                self._settings.voice_default_narrator_voice_id
            )
            if configured is not None and configured.type == "narrator":
                return configured
            for profile in self._voices.values():
                if profile.type == "narrator":
                    return profile
            return None

    def create_voice_profile(
        self, profile: VoiceProfile, *, overwrite: bool = False
    ) -> VoiceProfile:
        """Create a voice profile, optionally replacing an existing profile."""

        with self._lock:
            if profile.voice_id in self._voices and not overwrite:
                raise VoiceProfileConflict(
                    "Voice profile already exists.",
                    code="voice_profile_exists",
                    details={"voice_id": profile.voice_id},
                )
            self._voices[profile.voice_id] = profile
            self._save_locked()
            return profile

    def update_voice_profile(
        self, voice_id: str, update: VoiceProfileUpdate
    ) -> VoiceProfile:
        """Apply a partial update to an existing profile."""

        with self._lock:
            current = self.require_voice_profile(voice_id)
            values = update.model_dump(exclude_unset=True)
            updated = current.model_copy(update=values)
            self._voices[current.voice_id] = updated
            self._save_locked()
            return updated

    def delete_voice_profile(self, voice_id: str) -> None:
        """Delete a voice profile and remove character assignments pointing to it."""

        with self._lock:
            profile = self.require_voice_profile(voice_id)
            default_narrator_id = self._settings.voice_default_narrator_voice_id
            narrator_count = sum(
                1 for candidate in self._voices.values() if candidate.type == "narrator"
            )
            if profile.voice_id == default_narrator_id and narrator_count <= 1:
                raise VoiceManagerError(
                    "Cannot delete the only default narrator voice.",
                    code="voice_default_narrator_required",
                    details={"voice_id": voice_id},
                )
            del self._voices[profile.voice_id]
            self._character_voice_assignments = {
                character_id: assigned_voice_id
                for character_id, assigned_voice_id in self._character_voice_assignments.items()
                if assigned_voice_id != profile.voice_id
            }
            self._save_locked()

    def assign_voice_to_character(
        self, character_id: str, voice_id: str
    ) -> VoiceProfile:
        """Assign an existing voice profile to a character ID."""

        normalized_character_id = self._normalize_character_id(character_id)
        profile = self.require_voice_profile(voice_id)
        with self._lock:
            self._character_voice_assignments[normalized_character_id] = (
                profile.voice_id
            )
            self._save_locked()
            return profile

    def clear_character_voice(self, character_id: str) -> None:
        """Remove a character-specific voice assignment if present."""

        normalized_character_id = self._normalize_character_id(character_id)
        with self._lock:
            self._character_voice_assignments.pop(normalized_character_id, None)
            self._save_locked()

    def get_assigned_voice_id(self, character_id: str) -> str | None:
        """Return the raw assigned voice ID for a character, if one exists."""

        normalized_character_id = self._normalize_character_id(character_id)
        with self._lock:
            return self._character_voice_assignments.get(normalized_character_id)

    def get_voice_for_character(self, character_id: str) -> VoiceProfile | None:
        """Return a character's assigned profile, with configured fallback behavior."""

        assigned_voice_id = self.get_assigned_voice_id(character_id)
        if assigned_voice_id is not None:
            profile = self.get_voice_profile(assigned_voice_id)
            if profile is not None:
                return profile

        if self._settings.voice_default_character_voice_behavior == "narrator":
            return self.ensure_default_narrator_voice()
        return None

    def resolve_tts_voice_profile(
        self,
        *,
        voice_id: str | None = None,
        character_id: str | None = None,
    ) -> VoiceProfile:
        """Resolve the profile that a TTS request should use."""

        if voice_id is not None:
            return self.require_voice_profile(voice_id)
        if character_id is not None:
            profile = self.get_voice_for_character(character_id)
            if profile is not None:
                return profile
        return self.ensure_default_narrator_voice()

    def backend_voice_id_for_profile(self, profile: VoiceProfile) -> str:
        """Return the concrete backend voice key for a profile.

        Future cloning adapters can inspect `reference_audio_path` and richer
        metadata. Current Orpheus/Piper adapters receive `metadata.backend_voice_id`
        when present, otherwise the durable `voice_id` itself.
        """

        backend_voice_id = profile.metadata.get("backend_voice_id")
        if isinstance(backend_voice_id, str) and backend_voice_id.strip():
            return backend_voice_id.strip()
        return profile.voice_id

    def _load(self) -> None:
        with self._lock:
            if not self._store_path.exists():
                self._voices = {}
                self._character_voice_assignments = {}
                return
            try:
                raw = json.loads(self._store_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise VoiceManagerError(
                    "Voice profile store is not valid JSON.",
                    code="voice_store_invalid_json",
                    details={"store_path": str(self._store_path)},
                ) from exc

            voices = raw.get("voices", [])
            assignments = raw.get("character_voice_assignments", {})
            self._voices = {
                profile.voice_id: profile
                for profile in (VoiceProfile.model_validate(item) for item in voices)
            }
            self._character_voice_assignments = {
                str(character_id): str(voice_id)
                for character_id, voice_id in assignments.items()
                if str(voice_id) in self._voices
            }

    def _save_locked(self) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "voices": [
                profile.model_dump(mode="json")
                for profile in sorted(
                    self._voices.values(), key=lambda item: item.voice_id
                )
            ],
            "character_voice_assignments": dict(
                sorted(self._character_voice_assignments.items())
            ),
        }
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self._store_path.parent,
            prefix=f".{self._store_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            json.dump(payload, temp_file, indent=2, sort_keys=True)
            temp_file.write("\n")
            temp_path = Path(temp_file.name)
        temp_path.replace(self._store_path)

    @staticmethod
    def _normalize_character_id(character_id: str) -> str:
        normalized = character_id.strip()
        if not normalized:
            raise VoiceManagerError(
                "character_id cannot be empty.",
                code="voice_character_id_empty",
            )
        return normalized
