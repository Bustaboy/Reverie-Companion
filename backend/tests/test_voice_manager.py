"""Tests for JSON-backed voice profile management."""

import pytest

from app.core.config import Settings
from app.models.voice import VoiceProfile
from app.services.voice_manager import (
    VoiceManager,
    VoiceManagerError,
    VoiceProfileAlreadyExists,
)


def make_manager(tmp_path) -> VoiceManager:
    return VoiceManager(
        Settings(
            voice_profiles_path=str(tmp_path / "voices.json"),
            voice_default_narrator_voice_id="narrator_default",
            voice_default_narrator_name="Default Narrator",
        )
    )


def test_default_narrator_voice_is_persisted(tmp_path) -> None:
    manager = make_manager(tmp_path)

    default_voice = manager.get_default_narrator_voice()
    reloaded = make_manager(tmp_path)

    assert default_voice.voice_id == "narrator_default"
    assert default_voice.type == "narrator"
    assert reloaded.get_default_narrator_voice().voice_id == "narrator_default"


def test_voice_profile_crud_and_character_assignment(tmp_path) -> None:
    manager = make_manager(tmp_path)
    profile = VoiceProfile(
        voice_id="aurora_voice",
        name="Aurora",
        type="character",
        reference_audio_path="voices/aurora.wav",
        metadata={"style": "warm"},
    )

    manager.create_voice_profile(profile)
    updated = manager.update_voice_profile("aurora_voice", metadata={"style": "soft"})
    assigned = manager.assign_voice_to_character("aurora", "aurora_voice")

    assert updated.metadata == {"style": "soft"}
    assert assigned.voice_id == "aurora_voice"
    assert manager.get_voice_for_character("aurora") == updated

    manager.delete_voice_profile("aurora_voice")

    assert manager.get_voice_profile("aurora_voice") is None
    assert manager.get_voice_for_character("aurora").voice_id == "narrator_default"


def test_duplicate_and_default_delete_are_rejected(tmp_path) -> None:
    manager = make_manager(tmp_path)
    default_voice = manager.get_default_narrator_voice()

    with pytest.raises(VoiceProfileAlreadyExists):
        manager.create_voice_profile(default_voice)

    with pytest.raises(VoiceManagerError) as exc_info:
        manager.delete_voice_profile(default_voice.voice_id)

    assert exc_info.value.code == "voice_default_narrator_delete_forbidden"
