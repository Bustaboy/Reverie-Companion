"""Local-first TTS service with Orpheus primary and Piper fallback.

The service is intentionally adapter-shaped: routes call this business layer,
while backend-specific details stay private to the service. Orpheus is loaded
lazily because a 3B TTS model can consume most of an 8GB mobile GPU. Piper is
kept as the small CPU-friendly fallback for low-VRAM or missing-model cases.
"""

from __future__ import annotations

import asyncio
import base64
import importlib
import importlib.util
import logging
import shutil
import subprocess
import tempfile
import time
import wave
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from app.core.config import Settings

logger = logging.getLogger(__name__)

TTSEngineName = Literal["orpheus", "piper"]


class TTSServiceError(Exception):
    """Typed service error for TTS generation failures."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 500,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}


@dataclass(frozen=True)
class TTSGenerationResult:
    """Generated audio bytes plus compact metadata for API responses."""

    audio: bytes
    format: Literal["wav"]
    voice_id: str
    engine: TTSEngineName
    sample_rate: int | None = None
    duration_ms: int | None = None
    fallback_used: bool = False

    def as_base64(self) -> str:
        """Return the audio payload encoded for JSON transport."""

        return base64.b64encode(self.audio).decode("ascii")


@dataclass(frozen=True)
class TTSVoiceSettings:
    """Resolved voice settings for a single request."""

    voice_id: str
    orpheus_voice: str
    piper_model_path: Path | None
    sample_rate: int


class _OrpheusBackend:
    """Lazy Orpheus TTS 3B adapter.

    This adapter supports local Orpheus installations without adding a hard
    dependency to the base backend. It expects an optional `orpheus_tts` Python
    package exposing an `OrpheusModel`-like class. The service falls back to
    Piper when the package/model is absent, initialization is too slow, or VRAM
    policy rejects loading.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model: Any | None = None
        self._loaded = False

    def is_available(self) -> bool:
        """Return whether the optional Orpheus Python package is installed."""

        return importlib.util.find_spec("orpheus_tts") is not None

    def ensure_loaded(self, *, request_id: str | None) -> None:
        """Load Orpheus lazily after 8GB VRAM checks pass."""

        if self._loaded:
            return
        if not self.is_available():
            raise TTSServiceError(
                "orpheus_dependency_missing",
                "Orpheus TTS is not installed locally.",
                status_code=503,
                retryable=False,
            )

        resolved_device = self._resolve_device()
        self._enforce_vram_budget(device=resolved_device, request_id=request_id)
        started_at = time.monotonic()
        module = importlib.import_module("orpheus_tts")
        model_class = getattr(module, "OrpheusModel", None)
        if model_class is None:
            raise TTSServiceError(
                "orpheus_adapter_unsupported",
                "Installed Orpheus package does not expose OrpheusModel.",
                status_code=503,
                retryable=False,
            )

        model_kwargs = {
            "model_name": self._settings.tts_orpheus_model_path,
            "device": resolved_device,
        }
        if self._settings.tts_quantization != "none":
            model_kwargs["quantization"] = self._settings.tts_quantization

        logger.info(
            "Loading Orpheus TTS model",
            extra={
                "request_id": request_id,
                "model_path": self._settings.tts_orpheus_model_path,
                "device": resolved_device,
                "quantization": self._settings.tts_quantization,
            },
        )
        self._model = model_class(**model_kwargs)
        self._loaded = True
        logger.info(
            "Orpheus TTS model loaded",
            extra={
                "request_id": request_id,
                "load_seconds": round(time.monotonic() - started_at, 3),
            },
        )

    def generate(
        self,
        text: str,
        voice: TTSVoiceSettings,
        *,
        request_id: str | None,
    ) -> TTSGenerationResult:
        """Generate WAV audio through Orpheus."""

        self.ensure_loaded(request_id=request_id)
        if self._model is None:
            raise TTSServiceError(
                "orpheus_not_loaded",
                "Orpheus did not load successfully.",
                status_code=503,
                retryable=True,
            )

        generate_speech = getattr(self._model, "generate_speech", None)
        if generate_speech is None:
            generate_speech = getattr(self._model, "generate", None)
        if generate_speech is None:
            raise TTSServiceError(
                "orpheus_adapter_unsupported",
                "Loaded Orpheus model has no supported speech generation method.",
                status_code=503,
                retryable=False,
            )

        audio = generate_speech(text=text, voice=voice.orpheus_voice)
        if isinstance(audio, str):
            audio_bytes = Path(audio).read_bytes()
        elif isinstance(audio, Path):
            audio_bytes = audio.read_bytes()
        elif isinstance(audio, bytes):
            audio_bytes = audio
        else:
            raise TTSServiceError(
                "orpheus_invalid_audio",
                "Orpheus returned an unsupported audio payload.",
                status_code=502,
                retryable=True,
            )

        return TTSGenerationResult(
            audio=audio_bytes,
            format="wav",
            voice_id=voice.voice_id,
            engine="orpheus",
            sample_rate=_read_wav_sample_rate(audio_bytes) or voice.sample_rate,
            duration_ms=_read_wav_duration_ms(audio_bytes),
            fallback_used=False,
        )

    def _resolve_device(self) -> str:
        """Resolve auto device selection without importing torch at module import time."""

        if self._settings.tts_device != "auto":
            return self._settings.tts_device
        if importlib.util.find_spec("torch") is None:
            return "cpu"
        torch = importlib.import_module("torch")
        cuda = getattr(torch, "cuda", None)
        return "cuda" if cuda and cuda.is_available() else "cpu"

    def _enforce_vram_budget(self, *, device: str, request_id: str | None) -> None:
        """Reject unsafe Orpheus loads when CUDA VRAM is below configured budget."""

        if device == "cpu":
            return
        torch_spec = importlib.util.find_spec("torch")
        if torch_spec is None:
            if device == "cuda":
                raise TTSServiceError(
                    "cuda_probe_unavailable",
                    "CUDA was requested for Orpheus, but PyTorch is not installed.",
                    status_code=503,
                    retryable=False,
                )
            return

        torch = importlib.import_module("torch")
        cuda = getattr(torch, "cuda", None)
        cuda_available = bool(cuda and cuda.is_available())
        if device == "cuda" and not cuda_available:
            raise TTSServiceError(
                "cuda_unavailable",
                "CUDA was requested for Orpheus, but no CUDA device is available.",
                status_code=503,
                retryable=True,
            )
        if not cuda_available:
            return

        device_index = cuda.current_device()
        total_vram_gb = cuda.get_device_properties(device_index).total_memory / (1024**3)
        reserved_gb = cuda.memory_reserved(device_index) / (1024**3)
        allocated_gb = cuda.memory_allocated(device_index) / (1024**3)
        free_estimate_gb = max(total_vram_gb - max(reserved_gb, allocated_gb), 0.0)
        minimum_gb = self._settings.tts_min_free_vram_gb
        logger.info(
            "Checked Orpheus VRAM budget",
            extra={
                "request_id": request_id,
                "total_vram_gb": round(total_vram_gb, 2),
                "free_estimate_gb": round(free_estimate_gb, 2),
                "minimum_gb": minimum_gb,
            },
        )
        if free_estimate_gb < minimum_gb:
            raise TTSServiceError(
                "insufficient_vram_for_orpheus",
                "Not enough free VRAM for Orpheus TTS; using Piper fallback if available.",
                status_code=503,
                retryable=True,
                details={
                    "free_estimate_gb": round(free_estimate_gb, 2),
                    "minimum_gb": minimum_gb,
                    "recommendation": "Use 4-bit quantization, CPU/Piper fallback, or free GPU memory.",
                },
            )


class _PiperBackend:
    """Piper CLI adapter for lightweight CPU fallback speech."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_available(self, voice: TTSVoiceSettings) -> bool:
        """Return whether the Piper executable and voice model are available."""

        return bool(
            shutil.which(self._settings.tts_piper_executable)
            and voice.piper_model_path
            and voice.piper_model_path.exists()
        )

    def generate(
        self,
        text: str,
        voice: TTSVoiceSettings,
        *,
        request_id: str | None,
    ) -> TTSGenerationResult:
        """Generate WAV audio by invoking the local Piper binary."""

        if voice.piper_model_path is None:
            raise TTSServiceError(
                "piper_voice_missing",
                "No Piper model is configured for this voice.",
                status_code=503,
                retryable=False,
            )
        executable = shutil.which(self._settings.tts_piper_executable)
        if executable is None:
            raise TTSServiceError(
                "piper_executable_missing",
                "Piper executable was not found on PATH.",
                status_code=503,
                retryable=False,
            )
        if not voice.piper_model_path.exists():
            raise TTSServiceError(
                "piper_model_missing",
                "Configured Piper voice model does not exist.",
                status_code=503,
                retryable=False,
                details={"model_path": str(voice.piper_model_path)},
            )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output_file:
            output_path = Path(output_file.name)
        command = [
            executable,
            "--model",
            str(voice.piper_model_path),
            "--output_file",
            str(output_path),
        ]
        started_at = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                input=text,
                text=True,
                capture_output=True,
                timeout=self._settings.tts_piper_timeout_seconds,
                check=False,
            )
            if completed.returncode != 0:
                raise TTSServiceError(
                    "piper_generation_failed",
                    "Piper failed to synthesize speech.",
                    status_code=502,
                    retryable=True,
                    details={"stderr": completed.stderr[-500:]},
                )
            audio_bytes = output_path.read_bytes()
            logger.info(
                "Piper TTS generation completed",
                extra={
                    "request_id": request_id,
                    "voice_id": voice.voice_id,
                    "duration_seconds": round(time.monotonic() - started_at, 3),
                },
            )
            return TTSGenerationResult(
                audio=audio_bytes,
                format="wav",
                voice_id=voice.voice_id,
                engine="piper",
                sample_rate=_read_wav_sample_rate(audio_bytes) or voice.sample_rate,
                duration_ms=_read_wav_duration_ms(audio_bytes),
                fallback_used=True,
            )
        finally:
            output_path.unlink(missing_ok=True)


class TTSService:
    """Generate speech from text with Orpheus primary and Piper fallback."""

    def __init__(
        self,
        settings: Settings,
        *,
        orpheus_backend: _OrpheusBackend | None = None,
        piper_backend: _PiperBackend | None = None,
    ) -> None:
        self._settings = settings
        self._orpheus = orpheus_backend or _OrpheusBackend(settings)
        self._piper = piper_backend or _PiperBackend(settings)

    async def generate_speech(
        self,
        *,
        text: str,
        voice_id: str | None = None,
        stream: bool = False,
        request_id: str | None = None,
    ) -> TTSGenerationResult | AsyncIterator[bytes]:
        """Generate speech from text, optionally returning a byte stream.

        The primary path attempts Orpheus when enabled. If Orpheus is missing,
        too slow, or rejected by VRAM policy, Piper is used. If both are
        unavailable, a typed error is raised for the route to map cleanly.
        """

        normalized_text = text.strip()
        if not normalized_text:
            raise TTSServiceError(
                "tts_empty_text",
                "Text is required for speech generation.",
                status_code=422,
                retryable=False,
            )
        voice = self._resolve_voice(voice_id)
        result = await asyncio.to_thread(
            self._generate_non_streaming,
            normalized_text,
            voice,
            request_id,
        )
        if stream:
            return _single_chunk_stream(result.audio)
        return result

    def _generate_non_streaming(
        self,
        text: str,
        voice: TTSVoiceSettings,
        request_id: str | None,
    ) -> TTSGenerationResult:
        """Synchronous generation implementation for thread offloading."""

        if self._settings.tts_orpheus_enabled:
            try:
                executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tts-orpheus")
                future = executor.submit(
                    self._orpheus.generate, text, voice, request_id=request_id
                )
                try:
                    return future.result(
                        timeout=self._settings.tts_orpheus_timeout_seconds
                    )
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
            except FutureTimeoutError as exc:
                logger.warning(
                    "Orpheus TTS timed out; attempting Piper fallback",
                    extra={
                        "request_id": request_id,
                        "timeout_seconds": self._settings.tts_orpheus_timeout_seconds,
                    },
                )
                if not self._settings.tts_piper_enabled:
                    raise TTSServiceError(
                        "orpheus_generation_timeout",
                        "Orpheus was too slow to synthesize speech.",
                        status_code=504,
                        retryable=True,
                    ) from exc
            except TTSServiceError as exc:
                logger.warning(
                    "Orpheus TTS unavailable; attempting Piper fallback",
                    extra={
                        "request_id": request_id,
                        "code": exc.code,
                        "retryable": exc.retryable,
                    },
                )
                if not self._settings.tts_piper_enabled:
                    raise
            except Exception as exc:
                logger.exception(
                    "Unexpected Orpheus TTS failure; attempting Piper fallback",
                    extra={"request_id": request_id, "error_type": type(exc).__name__},
                )
                if not self._settings.tts_piper_enabled:
                    raise TTSServiceError(
                        "orpheus_generation_failed",
                        "Orpheus failed to synthesize speech.",
                        status_code=502,
                        retryable=True,
                    ) from exc

        if self._settings.tts_piper_enabled:
            return self._piper.generate(text, voice, request_id=request_id)

        raise TTSServiceError(
            "tts_backend_unavailable",
            "No local TTS backend is available.",
            status_code=503,
            retryable=True,
        )

    def _resolve_voice(self, voice_id: str | None) -> TTSVoiceSettings:
        """Resolve user-facing voice ID to Orpheus/Piper defaults."""

        resolved_voice_id = (voice_id or self._settings.tts_default_voice_id).strip()
        if not resolved_voice_id:
            resolved_voice_id = self._settings.tts_default_voice_id

        piper_model = self._settings.tts_piper_model_path
        return TTSVoiceSettings(
            voice_id=resolved_voice_id,
            orpheus_voice=(
                resolved_voice_id
                if resolved_voice_id != "default"
                else self._settings.tts_orpheus_default_voice
            ),
            piper_model_path=Path(piper_model).expanduser() if piper_model else None,
            sample_rate=self._settings.tts_default_sample_rate,
        )


async def _single_chunk_stream(audio: bytes) -> AsyncIterator[bytes]:
    """Yield a generated audio payload as a simple streaming response."""

    yield audio


def _read_wav_sample_rate(audio: bytes) -> int | None:
    """Read sample rate from WAV bytes when possible."""

    with tempfile.NamedTemporaryFile(suffix=".wav") as wav_file:
        wav_file.write(audio)
        wav_file.flush()
        try:
            with wave.open(wav_file.name, "rb") as reader:
                return int(reader.getframerate())
        except wave.Error:
            return None


def _read_wav_duration_ms(audio: bytes) -> int | None:
    """Read approximate duration from WAV bytes when possible."""

    with tempfile.NamedTemporaryFile(suffix=".wav") as wav_file:
        wav_file.write(audio)
        wav_file.flush()
        try:
            with wave.open(wav_file.name, "rb") as reader:
                frames = reader.getnframes()
                framerate = reader.getframerate()
                if framerate <= 0:
                    return None
                return round((frames / framerate) * 1000)
        except wave.Error:
            return None
