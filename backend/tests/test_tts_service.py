"""Coverage for the local-first TTS service foundation."""

from __future__ import annotations

import asyncio
import base64
import io
import unittest
import wave
from collections.abc import AsyncIterator
from typing import Any

from fastapi.testclient import TestClient

from app.api.routes.tts import get_tts_service
from app.core.config import Settings
from app.main import create_app
from app.services.tts_service import TTSGenerationResult, TTSService, TTSServiceError


def tiny_wav(sample_rate: int = 16000) -> bytes:
    """Create a tiny valid WAV payload for deterministic tests."""

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        writer.writeframes(b"\x00\x00" * 16)
    return buffer.getvalue()


class FailingOrpheus:
    def generate(self, *_args: Any, **_kwargs: Any) -> TTSGenerationResult:
        raise TTSServiceError(
            "insufficient_vram_for_orpheus",
            "Not enough free VRAM for Orpheus.",
            status_code=503,
            retryable=True,
        )


class FakePiper:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate(self, text: str, voice: Any, **_kwargs: Any) -> TTSGenerationResult:
        self.calls.append(text)
        return TTSGenerationResult(
            audio=tiny_wav(),
            format="wav",
            voice_id=voice.voice_id,
            engine="piper",
            sample_rate=16000,
            duration_ms=1,
            fallback_used=True,
        )


class FakeService:
    async def generate_speech(
        self,
        *,
        text: str,
        voice_id: str | None = None,
        stream: bool = False,
        request_id: str | None = None,
    ) -> TTSGenerationResult | AsyncIterator[bytes]:
        result = TTSGenerationResult(
            audio=tiny_wav(),
            format="wav",
            voice_id=voice_id or "default",
            engine="piper",
            sample_rate=16000,
            duration_ms=1,
            fallback_used=True,
        )
        if stream:
            async def chunks() -> AsyncIterator[bytes]:
                yield result.audio

            return chunks()
        return result


class TTSServiceTests(unittest.TestCase):
    def test_orpheus_failure_falls_back_to_piper(self) -> None:
        piper = FakePiper()
        service = TTSService(
            Settings(tts_orpheus_enabled=True, tts_piper_enabled=True),
            orpheus_backend=FailingOrpheus(),  # type: ignore[arg-type]
            piper_backend=piper,  # type: ignore[arg-type]
        )

        result = asyncio.run(
            service.generate_speech(text="Hello, beloved.", voice_id="tara")
        )

        self.assertIsInstance(result, TTSGenerationResult)
        assert isinstance(result, TTSGenerationResult)
        self.assertEqual(result.engine, "piper")
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.voice_id, "tara")
        self.assertEqual(piper.calls, ["Hello, beloved."])

    def test_streaming_returns_audio_chunks(self) -> None:
        service = TTSService(
            Settings(tts_orpheus_enabled=False, tts_piper_enabled=True),
            piper_backend=FakePiper(),  # type: ignore[arg-type]
        )

        async def collect() -> bytes:
            stream = await service.generate_speech(text="Stream me.", stream=True)
            chunks: list[bytes] = []
            async for chunk in stream:  # type: ignore[union-attr]
                chunks.append(chunk)
            return b"".join(chunks)

        audio = asyncio.run(collect())
        self.assertTrue(audio.startswith(b"RIFF"))

    def test_generate_endpoint_returns_base64_audio(self) -> None:
        app = create_app()
        app.dependency_overrides[get_tts_service] = lambda: FakeService()
        client = TestClient(app)

        response = client.post(
            "/api/tts/generate",
            json={"text": "Say hello.", "voice_id": "tara", "stream": False},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["engine"], "piper")
        self.assertEqual(payload["voice_id"], "tara")
        self.assertTrue(base64.b64decode(payload["audio_base64"]).startswith(b"RIFF"))

    def test_generate_endpoint_streams_wav_audio(self) -> None:
        app = create_app()
        app.dependency_overrides[get_tts_service] = lambda: FakeService()
        client = TestClient(app)

        response = client.post(
            "/api/tts/generate",
            json={"text": "Stream hello.", "voice_id": "tara", "stream": True},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/wav")
        self.assertTrue(response.content.startswith(b"RIFF"))
