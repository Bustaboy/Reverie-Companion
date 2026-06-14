"""Tests for the local-first TTS service foundation."""

import asyncio
import io
import wave

import numpy as np
import pytest

from app.core.config import Settings
from app.models.voice import VoiceProfile
from app.services.voice_manager import VoiceManager
from app.services.tts_service import (
    OrpheusBackend,
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
        tts_primary_backend="orpheus",
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


def test_orpheus_cpp_tts_result_is_encoded_as_wav() -> None:
    class FakeCppModel:
        def tts(self, text, options):
            assert text == "Hello"
            assert options["voice_id"] == "tara"
            return 24_000, np.zeros((1, 24), dtype=np.int16)

    backend = OrpheusBackend(
        Settings(
            _env_file=None,
            tts_orpheus_runtime="cpp",
            tts_orpheus_default_voice_id="tara",
        )
    )

    audio = backend._generate_with_model(  # type: ignore[attr-defined]
        FakeCppModel(), "Hello", "reverie_default", None
    )

    with wave.open(io.BytesIO(audio), "rb") as wav_file:
        assert wav_file.getframerate() == 24_000
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getnframes() == 24


def test_orpheus_cpp_reports_audio_duration_not_generation_latency() -> None:
    class FakeCppModel:
        def tts(self, text, options):
            return 24_000, np.zeros((1, 24), dtype=np.int16)

    async def run_test() -> None:
        backend = OrpheusBackend(
            Settings(
                _env_file=None,
                tts_orpheus_runtime="cpp",
                tts_orpheus_default_voice_id="tara",
            )
        )
        backend._model = FakeCppModel()  # type: ignore[attr-defined]

        result = await backend.generate(
            text="Hello",
            voice_id="reverie_default",
            audio_format="wav",
            request_id="req_duration",
        )

        assert result.duration_seconds == pytest.approx(24 / 24_000)

    asyncio.run(run_test())


def test_orpheus_cpp_context_is_bounded(monkeypatch) -> None:
    llama_cpp = pytest.importorskip("llama_cpp")
    captured: dict[str, object] = {}

    def fake_llama(*args, **kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return object()

    class FakeOrpheusCpp:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            from llama_cpp import Llama

            self.llama = Llama(model_path="fake.gguf", n_ctx=0)

    monkeypatch.setattr(llama_cpp, "Llama", fake_llama)
    backend = OrpheusBackend(
        Settings(
            _env_file=None,
            tts_orpheus_runtime="cpp",
            tts_orpheus_cpp_n_ctx=4096,
            tts_orpheus_cpp_n_threads=2,
        )
    )

    model = backend._instantiate_orpheus_cpp(FakeOrpheusCpp)  # type: ignore[attr-defined]

    assert isinstance(model, FakeOrpheusCpp)
    assert model.kwargs["n_threads"] == 2
    assert captured["n_ctx"] == 4096
    assert llama_cpp.Llama is fake_llama


def test_orpheus_unknown_voice_maps_to_default_voice() -> None:
    backend = OrpheusBackend(
        Settings(
            _env_file=None,
            tts_orpheus_runtime="cpp",
            tts_orpheus_default_voice_id="tara",
        )
    )

    assert backend._orpheus_voice_id("reverie_default") == "tara"  # type: ignore[attr-defined]
    assert backend._orpheus_voice_id("leah_soft") == "leah"  # type: ignore[attr-defined]


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


def test_stream_speech_chunks_uses_true_orpheus_stream(tmp_path) -> None:
    async def run_test() -> None:
        class StreamingBackend(FakeBackend):
            async def stream_generate(self, **kwargs):
                self.calls += 1
                self.last_kwargs = kwargs
                from app.services.tts_service import TTSStreamChunk

                yield TTSStreamChunk(
                    audio_bytes=b"pcm-1",
                    backend="orpheus",
                    voice_id=kwargs["response_voice_id"],
                    audio_format="pcm",
                    sample_rate=24_000,
                    sequence=1,
                )
                yield TTSStreamChunk(
                    audio_bytes=b"",
                    backend="orpheus",
                    voice_id=kwargs["response_voice_id"],
                    audio_format="pcm",
                    sample_rate=24_000,
                    sequence=2,
                    is_final=True,
                )

        service = make_service(tmp_path)
        service._orpheus = StreamingBackend("orpheus")  # type: ignore[assignment]
        service._piper = FakeBackend(  # type: ignore[assignment]
            "piper", error=AssertionError("fallback not expected")
        )

        chunks = [
            chunk
            async for chunk in service.stream_speech_chunks(
                text="Hello", voice_id="tara", request_id="req_stream"
            )
        ]

        assert chunks[0].audio_bytes == b"pcm-1"
        assert chunks[0].audio_format == "pcm"
        assert chunks[-1].is_final is True
        assert service._orpheus.last_kwargs["reference_audio_path"] == "voices/tara.wav"

    asyncio.run(run_test())


def test_stream_speech_chunks_falls_back_to_full_generation(tmp_path) -> None:
    async def run_test() -> None:
        service = make_service(tmp_path)
        piper_result = TTSGenerationResult(
            audio_bytes=b"fallback wav",
            backend="piper",
            voice_id="tara_backend",
            audio_format="wav",
            sample_rate=22_050,
        )
        service._orpheus = FakeBackend(  # type: ignore[assignment]
            "orpheus", error=TTSBackendUnavailable("missing", code="missing")
        )
        service._piper = FakeBackend("piper", result=piper_result)  # type: ignore[assignment]

        chunks = [
            chunk
            async for chunk in service.stream_speech_chunks(
                text="Hello", voice_id="tara", request_id="req_stream_fallback"
            )
        ]

        assert b"".join(chunk.audio_bytes for chunk in chunks) == b"fallback wav"
        assert chunks[0].fallback_used is True
        assert chunks[-1].is_final is True
        assert chunks[-1].audio_format == "wav"

    asyncio.run(run_test())
