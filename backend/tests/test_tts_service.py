"""Tests for the local-first TTS service foundation."""

import asyncio

import pytest

from app.core.config import Settings
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

    async def generate(self, **kwargs) -> TTSGenerationResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def make_service() -> TTSService:
    return TTSService(
        Settings(tts_orpheus_timeout_seconds=1.0, tts_piper_timeout_seconds=1.0)
    )


def test_generate_speech_prefers_orpheus() -> None:
    async def run_test() -> None:
        service = make_service()
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
        assert result.fallback_used is False
        assert result.audio_bytes == b"orpheus wav"

    asyncio.run(run_test())


def test_generate_speech_falls_back_to_piper_when_orpheus_unavailable() -> None:
    async def run_test() -> None:
        service = make_service()
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


def test_generate_speech_reports_all_backends_unavailable() -> None:
    async def run_test() -> None:
        service = make_service()
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
