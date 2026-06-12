"""Tests for the local-first TTS service foundation."""

import asyncio

import pytest

from app.core.config import Settings
from app.models.voice import VoiceProfile
from app.services.voice_manager import VoiceManager
from app.services.tts_service import (
    TTSBackendUnavailable,
    TTSGenerationResult,
    TTSService,
    TTSServiceError,
)


class FakeBackend:
    def __init__(
        self,
        name: str,
        result: TTSGenerationResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.name = name
        self.result = result
        self.error = error
        self.calls = 0
        self.last_kwargs = {}

    async def generate(self, **kwargs) -> TTSGenerationResult:
        self.calls += 1
        self.last_kwargs = kwargs
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def make_service(tmp_path) -> TTSService:
    settings = Settings(
        tts_orpheus_timeout_seconds=1.0,
        tts_piper_timeout_seconds=1.0,
        voice_profile_store_path=str(tmp_path / "voices.json"),
    )
    voice_manager = VoiceManager(settings)
    voice_manager.create_voice_profile(
        VoiceProfile(
            voice_id="tara",
            name="Tara",
            type="character",
            reference_audio_path="voices/tara.wav",
            metadata={"backend_voice_id": "tara_backend"},
        )
    )
    return TTSService(settings, voice_manager=voice_manager)


def test_generate_speech_prefers_orpheus(tmp_path) -> None:
    async def run_test() -> None:
        service = make_service(tmp_path)
        orpheus_result = TTSGenerationResult(
            audio_bytes=b"orpheus wav",
            backend="orpheus",
            voice_id="tara",
            audio_format="wav",
            sample_rate=24_000,
        )
        service._orpheus = FakeBackend(  # type: ignore[assignment]
            "orpheus", result=orpheus_result
        )
        service._piper = FakeBackend(  # type: ignore[assignment]
            "piper", error=AssertionError("fallback not expected")
        )

        result = await service.generate_speech(
            text="Hello", voice_id="tara", request_id="req_1"
        )

        assert result.backend == "orpheus"
        assert result.voice_id == "tara"
        assert service._orpheus.last_kwargs["voice_id"] == "tara_backend"
        assert result.fallback_used is False
        assert result.audio_bytes == b"orpheus wav"

    asyncio.run(run_test())


def test_generate_speech_falls_back_to_piper_when_orpheus_unavailable(tmp_path) -> None:
    async def run_test() -> None:
        service = make_service(tmp_path)
        piper_result = TTSGenerationResult(
            audio_bytes=b"piper wav",
            backend="piper",
            voice_id="tara",
            audio_format="wav",
            sample_rate=22_050,
        )
        service._orpheus = FakeBackend(  # type: ignore[assignment]
            "orpheus",
            error=TTSBackendUnavailable(
                "missing", code="tts_orpheus_dependency_missing"
            ),
        )
        service._piper = FakeBackend(  # type: ignore[assignment]
            "piper", result=piper_result
        )

        result = await service.generate_speech(
            text="Hello", voice_id="tara", request_id="req_2"
        )

        assert result.backend == "piper"
        assert result.fallback_used is True
        assert result.audio_bytes == b"piper wav"

    asyncio.run(run_test())


def test_generate_speech_reports_all_backends_unavailable(tmp_path) -> None:
    async def run_test() -> None:
        service = make_service(tmp_path)
        service._orpheus = FakeBackend(  # type: ignore[assignment]
            "orpheus", error=TTSBackendUnavailable("missing", code="missing")
        )
        service._piper = FakeBackend(  # type: ignore[assignment]
            "piper", error=TTSServiceError("failed", code="failed", retryable=True)
        )

        with pytest.raises(TTSBackendUnavailable) as exc_info:
            await service.generate_speech(
                text="Hello", voice_id="tara", request_id="req_3"
            )

        assert exc_info.value.code == "tts_backend_unavailable"
        assert len(exc_info.value.details["attempts"]) == 2

    asyncio.run(run_test())


def test_generate_speech_rejects_unknown_voice_profile(tmp_path) -> None:
    async def run_test() -> None:
        service = make_service(tmp_path)

        with pytest.raises(TTSServiceError) as exc_info:
            await service.generate_speech(
                text="Hello", voice_id="missing_voice", request_id="req_4"
            )

        assert exc_info.value.code == "voice_profile_not_found"

    asyncio.run(run_test())


def test_generate_speech_resolves_character_assignment(tmp_path) -> None:
    async def run_test() -> None:
        service = make_service(tmp_path)
        service._voice_manager.assign_voice_to_character("tara_character", "tara")
        piper_result = TTSGenerationResult(
            audio_bytes=b"piper wav",
            backend="piper",
            voice_id="tara_backend",
            audio_format="wav",
            sample_rate=22_050,
        )
        service._orpheus = FakeBackend(  # type: ignore[assignment]
            "orpheus", error=TTSBackendUnavailable("missing", code="missing")
        )
        service._piper = FakeBackend(  # type: ignore[assignment]
            "piper", result=piper_result
        )

        result = await service.generate_speech(
            text="Hello", character_id="tara_character", request_id="req_5"
        )

        assert result.voice_id == "tara"
        assert service._piper.last_kwargs["voice_id"] == "tara_backend"

    asyncio.run(run_test())


def test_generate_speech_routes_explicit_narration_to_narrator(tmp_path) -> None:
    async def run_test() -> None:
        from app.models.tts import TTSContext

        service = make_service(tmp_path)
        service._voice_manager.assign_voice_to_character("tara_character", "tara")
        piper_result = TTSGenerationResult(
            audio_bytes=b"narrator wav",
            backend="piper",
            voice_id="reverie_default",
            audio_format="wav",
            sample_rate=22_050,
        )
        service._orpheus = FakeBackend(  # type: ignore[assignment]
            "orpheus", error=TTSBackendUnavailable("missing", code="missing")
        )
        service._piper = FakeBackend(  # type: ignore[assignment]
            "piper", result=piper_result
        )

        result = await service.generate_speech(
            text="The hallway falls silent.",
            context=TTSContext(
                character_id="tara_character", is_narration=True, mode="rpg"
            ),
            request_id="req_narration",
        )

        assert result.voice_id == "reverie_default"
        assert service._piper.last_kwargs["voice_id"] == "reverie_default"

    asyncio.run(run_test())


def test_generate_speech_routes_rpg_quoted_character_line(tmp_path) -> None:
    async def run_test() -> None:
        from app.models.tts import TTSContext

        service = make_service(tmp_path)
        service._voice_manager.assign_voice_to_character("tara_character", "tara")
        piper_result = TTSGenerationResult(
            audio_bytes=b"character wav",
            backend="piper",
            voice_id="tara_backend",
            audio_format="wav",
            sample_rate=22_050,
        )
        service._orpheus = FakeBackend(  # type: ignore[assignment]
            "orpheus", error=TTSBackendUnavailable("missing", code="missing")
        )
        service._piper = FakeBackend(  # type: ignore[assignment]
            "piper", result=piper_result
        )

        result = await service.generate_speech(
            text='"I am right here," Tara says.',
            context=TTSContext(character_id="tara_character", mode="rpg"),
            request_id="req_character",
        )

        assert result.voice_id == "tara"
        assert service._piper.last_kwargs["voice_id"] == "tara_backend"

    asyncio.run(run_test())



def test_generate_speech_prefers_pretagged_tts_text(tmp_path) -> None:
    async def run_test() -> None:
        service = make_service(tmp_path)
        piper_result = TTSGenerationResult(
            audio_bytes=b"piper wav",
            backend="piper",
            voice_id="tara_backend",
            audio_format="wav",
            sample_rate=22_050,
        )
        service._orpheus = FakeBackend(  # type: ignore[assignment]
            "orpheus", error=TTSBackendUnavailable("missing", code="missing")
        )
        service._piper = FakeBackend(  # type: ignore[assignment]
            "piper", result=piper_result
        )

        await service.generate_speech(
            text="Stay close.",
            voice_id="tara",
            tts_text="<whisper> <gasp> Stay close.",
            request_id="req_pretagged",
        )

        assert service._piper.last_kwargs["text"] == "<whisper> <gasp> Stay close."
        assert service._piper.last_kwargs["voice_id"] == "tara_backend"

    asyncio.run(run_test())


def test_generate_speech_adds_fallback_tags_from_context(tmp_path) -> None:
    async def run_test() -> None:
        from app.models.tts import TTSContext

        service = make_service(tmp_path)
        piper_result = TTSGenerationResult(
            audio_bytes=b"piper wav",
            backend="piper",
            voice_id="tara_backend",
            audio_format="wav",
            sample_rate=22_050,
        )
        service._orpheus = FakeBackend(  # type: ignore[assignment]
            "orpheus", error=TTSBackendUnavailable("missing", code="missing")
        )
        service._piper = FakeBackend(  # type: ignore[assignment]
            "piper", result=piper_result
        )

        await service.generate_speech(
            text="I want you close and I trust you.",
            voice_id="tara",
            context=TTSContext(emotion_hint="intimate", intensity=1.5),
            request_id="req_fallback_tags",
        )

        assert "<" in service._piper.last_kwargs["text"]
        assert "I want you close" in service._piper.last_kwargs["text"]

    asyncio.run(run_test())
