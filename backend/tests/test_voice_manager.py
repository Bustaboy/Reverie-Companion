"""Tests for durable voice profile management."""

from app.core.config import Settings
from app.models.voice import VoiceMoodSettings, VoiceProfile, VoiceProfileUpdate
from app.services.voice_manager import VoiceManager, VoiceManagerError


def make_manager(tmp_path):
    return VoiceManager(
        Settings(voice_profile_store_path=str(tmp_path / "voices.json")),
    )


def test_ensure_default_narrator_voice_persists_profile(tmp_path) -> None:
    manager = make_manager(tmp_path)

    profile = manager.ensure_default_narrator_voice()
    reloaded = make_manager(tmp_path)

    assert profile.voice_id == "reverie_default"
    assert profile.type == "narrator"
    assert reloaded.get_default_narrator_voice() == profile


def test_voice_profile_crud_and_character_assignment(tmp_path) -> None:
    manager = make_manager(tmp_path)
    manager.ensure_default_narrator_voice()
    profile = VoiceProfile(
        voice_id="tara_soft",
        name="Tara Soft",
        type="character",
        reference_audio_path="voices/tara.wav",
        metadata={"backend_voice_id": "tara-piper", "style": "soft"},
    )

    manager.create_voice_profile(profile)
    updated = manager.update_voice_profile(
        "tara_soft", VoiceProfileUpdate(name="Tara Warm", metadata={"style": "warm"})
    )
    assigned = manager.assign_voice_to_character("tara", "tara_soft")

    assert updated.name == "Tara Warm"
    assert assigned.voice_id == "tara_soft"
    assert manager.get_voice_for_character("tara") == updated
    assert manager.backend_voice_id_for_profile(updated) == "tara_soft"

    reloaded = make_manager(tmp_path)
    assert reloaded.get_voice_for_character("tara") == updated

    reloaded.delete_voice_profile("tara_soft")
    assert reloaded.get_assigned_voice_id("tara") is None


def test_character_voice_falls_back_to_narrator_by_default(tmp_path) -> None:
    manager = make_manager(tmp_path)

    profile = manager.get_voice_for_character("unknown_character")

    assert profile is not None
    assert profile.type == "narrator"


def test_cannot_delete_only_default_narrator(tmp_path) -> None:
    manager = make_manager(tmp_path)
    manager.ensure_default_narrator_voice()

    try:
        manager.delete_voice_profile("reverie_default")
    except VoiceManagerError as exc:
        assert exc.code == "voice_default_narrator_required"
    else:  # pragma: no cover - assertion clarity.
        raise AssertionError("Expected deleting the only narrator to fail")


def test_create_zero_shot_voice_profile_stores_reference_and_assignment(
    tmp_path,
) -> None:
    settings = Settings(
        voice_profile_store_path=str(tmp_path / "voices.json"),
        voice_reference_audio_dir=str(tmp_path / "reference_audio"),
    )
    manager = VoiceManager(settings)

    profile = manager.create_zero_shot_voice_profile(
        name="Tara Clone",
        audio_file=__import__("io").BytesIO(b"fake audio"),
        filename="tara.wav",
        content_type="audio/wav",
        character_id="tara",
        duration_seconds=8.0,
    )

    assert profile.voice_id.startswith("clone_tara_clone")
    assert profile.metadata["clone_backend"] == "orpheus_zero_shot"
    assert profile.reference_audio_path is not None
    assert manager.get_voice_for_character("tara") == profile


def test_voice_profile_persists_mood_settings(tmp_path) -> None:
    manager = make_manager(tmp_path)
    profile = VoiceProfile(
        voice_id="tara_mood",
        name="Tara Mood",
        type="character",
        mood_settings=VoiceMoodSettings(
            baseline_expressiveness=1.3,
            emotional_sensitivity=1.6,
            nsfw_intensity=0.8,
        ),
    )

    manager.create_voice_profile(profile)
    updated = manager.update_voice_profile(
        "tara_mood",
        VoiceProfileUpdate(
            mood_settings=VoiceMoodSettings(
                baseline_expressiveness=0.8,
                emotional_sensitivity=1.2,
                nsfw_intensity=1.7,
            )
        ),
    )

    assert updated.mood_settings.nsfw_intensity == 1.7
    assert (
        make_manager(tmp_path).require_voice_profile("tara_mood").mood_settings
        == updated.mood_settings
    )
