"""Local-first text-to-speech service with Orpheus primary and Piper fallback.

The service is intentionally lazy: no TTS model is imported or loaded during
FastAPI startup. Orpheus is attempted first for richer emotional voice quality,
while Piper is kept as a lightweight CPU fallback for 8GB VRAM systems or
machines without the optional Orpheus dependencies installed.
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import shutil
import subprocess
import tempfile
import wave
from collections.abc import AsyncIterator
from dataclasses import dataclass
from inspect import signature
from pathlib import Path
from time import perf_counter
from typing import Protocol

from app.core.config import Settings
from app.models.tts import TTSContext
from app.services.emotion_engine import emotion_engine
from app.services.tts_context_router import TTSContextRouter
from app.services.resource_coordinator import resource_coordinator
from app.services.voice_manager import VoiceManager, VoiceManagerError

logger = logging.getLogger(__name__)


class TTSServiceError(Exception):
    """Base class for recoverable TTS service failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "tts_generation_failed",
        retryable: bool = False,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable
        self.details = details or {}


class TTSBackendUnavailable(TTSServiceError):
    """Raised when a configured TTS backend cannot be used."""


class TTSInsufficientVRAM(TTSServiceError):
    """Raised when Orpheus cannot fit inside the configured VRAM budget."""


@dataclass(frozen=True)
class TTSGenerationResult:
    """Audio and metadata returned by a TTS backend."""

    audio_bytes: bytes
    backend: str
    voice_id: str
    audio_format: str
    sample_rate: int
    duration_seconds: float | None = None
    fallback_used: bool = False

    def to_base64(self) -> str:
        """Return audio bytes encoded for a JSON API response."""

        return base64.b64encode(self.audio_bytes).decode("ascii")


@dataclass(frozen=True)
class TTSStreamChunk:
    """A progressively generated audio chunk plus playback metadata."""

    audio_bytes: bytes
    backend: str
    voice_id: str
    audio_format: str
    sample_rate: int
    sequence: int
    is_final: bool = False
    fallback_used: bool = False
    duration_seconds: float | None = None


class TTSBackend(Protocol):
    """Protocol implemented by local TTS adapters."""

    name: str

    async def generate(
        self,
        *,
        text: str,
        voice_id: str,
        audio_format: str,
        request_id: str | None,
        reference_audio_path: str | None = None,
    ) -> TTSGenerationResult:
        """Generate speech audio for text."""


class OrpheusBackend:
    """Lazy Orpheus TTS 3B adapter with 8GB-aware quantized loading.

    This adapter supports the community Orpheus package when present. It keeps
    imports local so Reverie can start without heavyweight GPU dependencies, and
    it validates CUDA VRAM before trying a 3B model. Piper remains the fallback
    when the optional package, model path, or VRAM budget is unavailable.
    """

    name = "orpheus"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model: object | None = None
        self._lock = asyncio.Lock()

    async def generate(
        self,
        *,
        text: str,
        voice_id: str,
        audio_format: str,
        request_id: str | None,
        reference_audio_path: str | None = None,
    ) -> TTSGenerationResult:
        if audio_format != "wav":
            raise TTSBackendUnavailable(
                "Orpheus currently returns WAV audio in Reverie.",
                code="tts_format_not_supported",
                retryable=False,
                details={"requested_format": audio_format},
            )

        model = await self._get_model(request_id=request_id)
        start = perf_counter()
        try:
            audio_bytes = await asyncio.to_thread(
                self._generate_with_model, model, text, voice_id, reference_audio_path
            )
        except TTSServiceError:
            raise
        except RuntimeError as exc:
            message = str(exc).lower()
            if "cuda" in message and ("out of memory" in message or "oom" in message):
                self.unload()
                raise TTSInsufficientVRAM(
                    "Orpheus ran out of GPU memory; retrying with Piper fallback.",
                    code="tts_insufficient_vram",
                    retryable=True,
                    details={"backend": self.name},
                ) from exc
            raise TTSServiceError(
                "Orpheus TTS generation failed.",
                code="tts_orpheus_generation_failed",
                retryable=True,
                details={"backend": self.name},
            ) from exc

        return TTSGenerationResult(
            audio_bytes=audio_bytes,
            backend=self.name,
            voice_id=voice_id,
            audio_format="wav",
            sample_rate=self._settings.tts_sample_rate,
            duration_seconds=perf_counter() - start,
        )

    async def _get_model(self, *, request_id: str | None) -> object:
        """Load Orpheus once, guarded by a lock so concurrent requests share it."""

        if self._model is not None:
            return self._model

        async with self._lock:
            if self._model is None:
                await asyncio.to_thread(self._load_model, request_id)
        if self._model is None:  # pragma: no cover - defensive guard.
            raise TTSBackendUnavailable(
                "Orpheus failed to initialize.", code="tts_orpheus_unavailable"
            )
        return self._model

    def _load_model(self, request_id: str | None) -> None:
        """Import and initialize Orpheus with quantization only when needed."""

        self._validate_vram_budget(request_id=request_id)
        try:
            from orpheus_tts import OrpheusModel  # type: ignore[import-not-found]
        except ImportError as exc:
            raise TTSBackendUnavailable(
                "Orpheus TTS dependencies are not installed.",
                code="tts_orpheus_dependency_missing",
                retryable=False,
                details={"package": "orpheus_tts"},
            ) from exc

        model_path = self._settings.tts_orpheus_model_path
        if model_path and not Path(model_path).expanduser().exists():
            raise TTSBackendUnavailable(
                "Configured Orpheus model path does not exist.",
                code="tts_orpheus_model_missing",
                retryable=False,
                details={"model_path": model_path},
            )

        logger.info(
            "Loading Orpheus TTS backend",
            extra={
                "request_id": request_id,
                "device": self._settings.tts_device,
                "quantization": self._settings.tts_quantization,
                "model_path": model_path or self._settings.tts_orpheus_model_id,
            },
        )
        self._model = OrpheusModel(
            model_name=model_path or self._settings.tts_orpheus_model_id,
            device=self._resolved_device(),
            dtype=self._orpheus_dtype(),
            load_in_4bit=self._settings.tts_quantization == "4bit",
            load_in_8bit=self._settings.tts_quantization == "8bit",
        )

    def _validate_vram_budget(self, *, request_id: str | None) -> None:
        """Fail early when CUDA memory is clearly too constrained for Orpheus."""

        if self._resolved_device() != "cuda":
            return
        try:
            import torch  # type: ignore[import-not-found]
        except ImportError:
            return
        if not torch.cuda.is_available():
            raise TTSBackendUnavailable(
                "CUDA was requested for Orpheus but is not available.",
                code="tts_cuda_unavailable",
                retryable=False,
            )
        free_bytes, total_bytes = torch.cuda.mem_get_info()
        free_mb = free_bytes // (1024 * 1024)
        min_free_mb = self._settings.tts_min_free_vram_mb
        if free_mb < min_free_mb:
            logger.warning(
                "Skipping Orpheus because free VRAM is below budget",
                extra={
                    "request_id": request_id,
                    "free_vram_mb": free_mb,
                    "total_vram_mb": total_bytes // (1024 * 1024),
                    "min_free_vram_mb": min_free_mb,
                },
            )
            raise TTSInsufficientVRAM(
                "Not enough free VRAM for Orpheus TTS.",
                code="tts_insufficient_vram",
                retryable=True,
                details={"free_vram_mb": free_mb, "min_free_vram_mb": min_free_mb},
            )

    async def stream_generate(
        self,
        *,
        text: str,
        voice_id: str,
        audio_format: str,
        request_id: str | None,
        response_voice_id: str | None = None,
        reference_audio_path: str | None = None,
    ) -> AsyncIterator[TTSStreamChunk]:
        """Yield true Orpheus audio chunks when the installed adapter exposes them."""

        model = await self._get_model(request_id=request_id)
        method = self._streaming_method(model)
        if method is None:
            raise TTSBackendUnavailable(
                "Installed Orpheus backend does not expose a streaming generation API.",
                code="tts_orpheus_streaming_unavailable",
                retryable=True,
                details={"backend": self.name},
            )

        start = perf_counter()
        sequence = 0
        try:
            stream = method(
                **self._orpheus_kwargs(method, text, voice_id, reference_audio_path)
            )
            async for audio_bytes in self._iter_model_stream(stream):
                if not audio_bytes:
                    continue
                sequence += 1
                yield TTSStreamChunk(
                    audio_bytes=audio_bytes,
                    backend=self.name,
                    voice_id=response_voice_id or voice_id,
                    audio_format="pcm" if audio_format == "wav" else audio_format,
                    sample_rate=self._settings.tts_sample_rate,
                    sequence=sequence,
                )
        except TTSServiceError:
            raise
        except RuntimeError as exc:
            message = str(exc).lower()
            if "cuda" in message and ("out of memory" in message or "oom" in message):
                self.unload()
                raise TTSInsufficientVRAM(
                    "Orpheus ran out of GPU memory; retrying with full-generation fallback.",
                    code="tts_insufficient_vram",
                    retryable=True,
                    details={"backend": self.name},
                ) from exc
            raise TTSServiceError(
                "Orpheus streaming TTS generation failed.",
                code="tts_orpheus_streaming_failed",
                retryable=True,
                details={"backend": self.name},
            ) from exc

        yield TTSStreamChunk(
            audio_bytes=b"",
            backend=self.name,
            voice_id=response_voice_id or voice_id,
            audio_format="pcm" if audio_format == "wav" else audio_format,
            sample_rate=self._settings.tts_sample_rate,
            sequence=sequence + 1,
            is_final=True,
            duration_seconds=perf_counter() - start,
        )

    def _generate_with_model(
        self, model: object, text: str, voice_id: str, reference_audio_path: str | None
    ) -> bytes:
        """Call common Orpheus package generation APIs and normalize to bytes."""

        for method_name in ("synthesize", "generate_speech", "generate"):
            method = getattr(model, method_name, None)
            if method is None:
                continue
            audio = method(
                **self._orpheus_kwargs(method, text, voice_id, reference_audio_path)
            )
            if isinstance(audio, bytes):
                return audio
            if hasattr(audio, "read"):
                return audio.read()
            if isinstance(audio, str):
                return Path(audio).read_bytes()
        raise TTSBackendUnavailable(
            "Installed Orpheus backend does not expose a supported generation API.",
            code="tts_orpheus_api_unsupported",
            retryable=False,
        )

    def _streaming_method(self, model: object):
        """Return the first recognized streaming method from community Orpheus builds."""

        for method_name in (
            "stream",
            "stream_speech",
            "synthesize_stream",
            "generate_stream",
            "generate_speech_stream",
        ):
            method = getattr(model, method_name, None)
            if method is not None:
                return method
        return None

    def _orpheus_kwargs(
        self, method: object, text: str, voice_id: str, reference_audio_path: str | None
    ) -> dict[str, object]:
        """Build tolerant kwargs for several Orpheus package variants."""

        try:
            parameters = signature(method).parameters
        except (TypeError, ValueError):
            parameters = {}

        kwargs: dict[str, object] = {}
        text_key = "prompt" if "prompt" in parameters or not parameters else "text"
        voice_key = "voice" if "voice" in parameters or not parameters else "voice_id"
        kwargs[text_key] = text
        kwargs[voice_key] = voice_id

        if reference_audio_path:
            for key in (
                "reference_audio",
                "reference_audio_path",
                "voice_reference",
                "speaker_reference",
            ):
                if key in parameters:
                    kwargs[key] = reference_audio_path
                    break
        return kwargs

    async def _iter_model_stream(self, stream: object) -> AsyncIterator[bytes]:
        if hasattr(stream, "__aiter__"):
            async for chunk in stream:  # type: ignore[attr-defined]
                yield self._coerce_audio_chunk(chunk)
            return

        for chunk in await asyncio.to_thread(lambda: list(stream)):  # type: ignore[arg-type]
            yield self._coerce_audio_chunk(chunk)

    def _coerce_audio_chunk(self, chunk: object) -> bytes:
        if isinstance(chunk, bytes):
            return chunk
        if isinstance(chunk, bytearray):
            return bytes(chunk)
        if isinstance(chunk, memoryview):
            return chunk.tobytes()
        if isinstance(chunk, tuple) and chunk:
            return self._coerce_audio_chunk(chunk[0])
        if isinstance(chunk, dict):
            for key in ("audio", "audio_bytes", "chunk", "pcm"):
                value = chunk.get(key)
                if value is not None:
                    return self._coerce_audio_chunk(value)
        if hasattr(chunk, "tobytes"):
            return chunk.tobytes()  # type: ignore[no-any-return]
        raise TTSServiceError(
            "Orpheus returned an unreadable streaming audio chunk.",
            code="tts_orpheus_stream_chunk_invalid",
            retryable=True,
        )

    def _resolved_device(self) -> str:
        """Resolve auto/cuda/cpu selection without importing torch unless needed."""

        if self._settings.tts_device != "auto":
            return self._settings.tts_device
        try:
            import torch  # type: ignore[import-not-found]
        except ImportError:
            return "cpu"
        return "cuda" if torch.cuda.is_available() else "cpu"

    def _orpheus_dtype(self) -> str:
        """Keep full precision off 8GB systems unless explicitly configured."""

        if self._settings.tts_quantization in {"4bit", "8bit"}:
            return "auto"
        return "float16" if self._resolved_device() == "cuda" else "float32"

    def unload(self) -> None:
        """Drop the lazy model reference and clear CUDA cache when possible."""

        self._model = None
        try:
            import torch  # type: ignore[import-not-found]
        except ImportError:
            return
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


class PiperBackend:
    """Subprocess adapter for Piper, Reverie's fast lightweight fallback."""

    name = "piper"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def generate(
        self,
        *,
        text: str,
        voice_id: str,
        audio_format: str,
        request_id: str | None,
        reference_audio_path: str | None = None,
    ) -> TTSGenerationResult:
        if audio_format != "wav":
            raise TTSBackendUnavailable(
                "Piper currently returns WAV audio in Reverie.",
                code="tts_format_not_supported",
                retryable=False,
                details={"requested_format": audio_format},
            )
        start = perf_counter()
        audio_bytes = await asyncio.to_thread(
            self._run_piper, text=text, voice_id=voice_id, request_id=request_id
        )
        return TTSGenerationResult(
            audio_bytes=audio_bytes,
            backend=self.name,
            voice_id=voice_id,
            audio_format="wav",
            sample_rate=self._settings.tts_sample_rate,
            duration_seconds=perf_counter() - start,
        )

    def _run_piper(self, *, text: str, voice_id: str, request_id: str | None) -> bytes:
        binary = self._settings.tts_piper_binary_path or shutil.which("piper")
        if not binary:
            raise TTSBackendUnavailable(
                "Piper binary is not configured or available on PATH.",
                code="tts_piper_binary_missing",
                retryable=False,
            )
        model_path = self._piper_model_path(voice_id)
        if not model_path.exists():
            raise TTSBackendUnavailable(
                "Configured Piper voice model does not exist.",
                code="tts_piper_model_missing",
                retryable=False,
                details={"model_path": str(model_path)},
            )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output_file:
            output_path = Path(output_file.name)
        command = [
            binary,
            "--model",
            str(model_path),
            "--output_file",
            str(output_path),
        ]
        logger.info(
            "Running Piper TTS fallback",
            extra={
                "request_id": request_id,
                "voice_id": voice_id,
                "model_path": str(model_path),
            },
        )
        try:
            completed = subprocess.run(
                command,
                input=text,
                text=True,
                capture_output=True,
                check=False,
                timeout=self._settings.tts_piper_timeout_seconds,
            )
            if completed.returncode != 0:
                raise TTSServiceError(
                    "Piper TTS generation failed.",
                    code="tts_piper_generation_failed",
                    retryable=True,
                    details={"stderr": completed.stderr[-500:]},
                )
            return output_path.read_bytes()
        except subprocess.TimeoutExpired as exc:
            raise TTSServiceError(
                "Piper TTS generation timed out.",
                code="tts_piper_timeout",
                retryable=True,
            ) from exc
        finally:
            output_path.unlink(missing_ok=True)

    def _piper_model_path(self, voice_id: str) -> Path:
        voice_dir = Path(self._settings.tts_piper_voice_dir).expanduser()
        explicit = self._settings.tts_piper_model_path
        if explicit:
            return Path(explicit).expanduser()
        return voice_dir / f"{voice_id}.onnx"


class TTSService:
    """Business workflow for local text-to-speech generation."""

    def __init__(
        self, settings: Settings, voice_manager: VoiceManager | None = None
    ) -> None:
        self._settings = settings
        self._voice_manager = voice_manager or VoiceManager(settings)
        self._voice_manager.ensure_default_narrator_voice()
        self._context_router = TTSContextRouter(self._voice_manager)
        self._orpheus = OrpheusBackend(settings)
        self._piper = PiperBackend(settings)

    @property
    def settings(self) -> Settings:
        """Expose read-only settings for route-level response metadata."""

        return self._settings

    async def generate_speech(
        self,
        *,
        text: str,
        voice_id: str | None = None,
        character_id: str | None = None,
        context: TTSContext | None = None,
        audio_format: str = "wav",
        request_id: str | None = None,
        tts_text: str | None = None,
    ) -> TTSGenerationResult:
        """Generate speech from text using context-aware voice routing and tags."""

        _visible_text, normalized_text, routing = self._prepare_request(
            text=text,
            voice_id=voice_id,
            character_id=character_id,
            context=context,
            tts_text=tts_text,
        )
        resolved_voice_id = routing.backend_voice_id
        response_voice_id = routing.voice_profile.voice_id

        errors: list[dict[str, object]] = []
        resource_decision = resource_coordinator.evaluate_vram_for_workload(
            workload="tts", required_free_mb=self._settings.tts_min_free_vram_mb
        )
        if resource_decision.should_unload_optional_models:
            self._orpheus.unload()
        async with resource_coordinator.tts_priority_section(request_id=request_id):
            for backend, fallback_used in self._backend_order(
                resource_decision.recommended_tts_backend
            ):
                try:
                    result = await asyncio.wait_for(
                        backend.generate(
                            text=normalized_text,
                            voice_id=resolved_voice_id,
                            audio_format=audio_format,
                            request_id=request_id,
                            reference_audio_path=routing.voice_profile.reference_audio_path,
                        ),
                        timeout=self._timeout_for_backend(backend.name),
                    )
                    result = TTSGenerationResult(
                        audio_bytes=result.audio_bytes,
                        backend=result.backend,
                        voice_id=response_voice_id,
                        audio_format=result.audio_format,
                        sample_rate=result.sample_rate,
                        duration_seconds=result.duration_seconds,
                        fallback_used=fallback_used,
                    )
                    logger.info(
                        "Generated TTS audio",
                        extra={
                            "request_id": request_id,
                            "backend": result.backend,
                            "voice_id": result.voice_id,
                            "tts_context_mode": routing.context.mode,
                            "tts_is_narration": routing.is_narration,
                            "tts_route_reason": routing.reason,
                            "fallback_used": result.fallback_used,
                            "audio_bytes": len(result.audio_bytes),
                        },
                    )
                    return result
                except TimeoutError as exc:
                    errors.append(
                        {"backend": backend.name, "code": "tts_backend_timeout"}
                    )
                    logger.warning(
                        "TTS backend timed out",
                        extra={"request_id": request_id, "backend": backend.name},
                    )
                    if backend.name == "orpheus":
                        self._orpheus.unload()
                    continue
                except TTSServiceError as exc:
                    errors.append(
                        {
                            "backend": backend.name,
                            "code": exc.code,
                            "details": exc.details,
                        }
                    )
                    logger.warning(
                        "TTS backend unavailable or failed",
                        extra={
                            "request_id": request_id,
                            "backend": backend.name,
                            "code": exc.code,
                        },
                    )
                    continue

        raise TTSBackendUnavailable(
            "No local TTS backend is currently available.",
            code="tts_backend_unavailable",
            retryable=False,
            details={"attempts": errors},
        )

    async def stream_speech(
        self,
        *,
        text: str,
        voice_id: str | None = None,
        character_id: str | None = None,
        context: TTSContext | None = None,
        audio_format: str = "wav",
        request_id: str | None = None,
        tts_text: str | None = None,
    ) -> AsyncIterator[bytes]:
        """Yield generated audio bytes.

        Orpheus is attempted first through a true chunk-yielding API when the
        installed package exposes one. If that is unavailable, Reverie falls
        back to full-file synthesis and yields bounded chunks so clients keep a
        single streaming contract.
        """

        async for chunk in self.stream_speech_chunks(
            text=text,
            voice_id=voice_id,
            character_id=character_id,
            context=context,
            audio_format=audio_format,
            request_id=request_id,
            tts_text=tts_text,
        ):
            if chunk.audio_bytes:
                yield chunk.audio_bytes

    async def stream_speech_chunks(
        self,
        *,
        text: str,
        voice_id: str | None = None,
        character_id: str | None = None,
        context: TTSContext | None = None,
        audio_format: str = "wav",
        request_id: str | None = None,
        tts_text: str | None = None,
    ) -> AsyncIterator[TTSStreamChunk]:
        """Yield metadata-rich chunks for near-instant frontend playback."""

        visible_text, normalized_text, routing = self._prepare_request(
            text=text,
            voice_id=voice_id,
            character_id=character_id,
            context=context,
            tts_text=tts_text,
        )
        errors: list[dict[str, object]] = []

        resource_decision = resource_coordinator.evaluate_vram_for_workload(
            workload="tts", required_free_mb=self._settings.tts_min_free_vram_mb
        )
        if resource_decision.should_unload_optional_models:
            self._orpheus.unload()

        if (
            self._settings.tts_primary_backend == "orpheus"
            and resource_decision.recommended_tts_backend != "piper"
            and hasattr(self._orpheus, "stream_generate")
        ):
            try:
                async with resource_coordinator.tts_priority_section(
                    request_id=request_id
                ):
                    async for chunk in self._orpheus.stream_generate(
                        text=normalized_text,
                        voice_id=routing.backend_voice_id,
                        response_voice_id=routing.voice_profile.voice_id,
                        audio_format=audio_format,
                        request_id=request_id,
                        reference_audio_path=routing.voice_profile.reference_audio_path,
                    ):
                        yield chunk
                return
            except TTSServiceError as exc:
                errors.append(
                    {"backend": "orpheus", "code": exc.code, "details": exc.details}
                )
                logger.info(
                    "Falling back from true Orpheus streaming to full TTS generation",
                    extra={"request_id": request_id, "code": exc.code},
                )

        result = await self.generate_speech(
            text=visible_text or text,
            voice_id=voice_id,
            character_id=character_id,
            context=context,
            audio_format="wav",
            request_id=request_id,
            tts_text=normalized_text,
        )
        chunk_size = self._settings.tts_stream_chunk_size_bytes
        sequence = 0
        with io.BytesIO(result.audio_bytes) as audio:
            while chunk_bytes := audio.read(chunk_size):
                sequence += 1
                yield TTSStreamChunk(
                    audio_bytes=chunk_bytes,
                    backend=result.backend,
                    voice_id=result.voice_id,
                    audio_format=result.audio_format,
                    sample_rate=result.sample_rate,
                    sequence=sequence,
                    fallback_used=True,
                )
        yield TTSStreamChunk(
            audio_bytes=b"",
            backend=result.backend,
            voice_id=result.voice_id,
            audio_format=result.audio_format,
            sample_rate=result.sample_rate,
            sequence=sequence + 1,
            is_final=True,
            fallback_used=True,
            duration_seconds=result.duration_seconds,
        )

    def _prepare_request(
        self,
        *,
        text: str,
        voice_id: str | None,
        character_id: str | None,
        context: TTSContext | None,
        tts_text: str | None,
    ):
        visible_text = emotion_engine.strip_emotion_tags(text.strip())
        try:
            routing = self._context_router.route(
                text=visible_text or (tts_text or text),
                context=context,
                voice_id=voice_id,
                character_id=character_id,
            )
        except VoiceManagerError as exc:
            raise TTSServiceError(
                "Requested voice profile could not be resolved.",
                code=exc.code,
                retryable=False,
                details=exc.details,
            ) from exc
        normalized_text = (
            tts_text.strip()
            if tts_text and tts_text.strip()
            else emotion_engine.analyze_and_tag(
                text=visible_text, tts_context=routing.context
            ).tts_text
        )
        self._validate_text_length(normalized_text)
        return visible_text, normalized_text, routing

    def _validate_text_length(self, text: str) -> None:
        """Keep each synthesis request bounded for local latency and 8GB safety."""

        max_chars = self._settings.tts_max_text_chars
        if len(text) <= max_chars:
            return

        raise TTSServiceError(
            "This voice line is too long to synthesize at once.",
            code="tts_text_too_long",
            retryable=False,
            details={"max_chars": max_chars, "actual_chars": len(text)},
        )

    def _backend_order(
        self, recommended_backend: str | None = None
    ) -> list[tuple[TTSBackend, bool]]:
        primary = self._settings.tts_primary_backend
        if primary == "piper" or recommended_backend == "piper":
            return [(self._piper, primary != "piper")]
        return [(self._orpheus, False), (self._piper, True)]

    def _timeout_for_backend(self, backend_name: str) -> float:
        if backend_name == "orpheus":
            return self._settings.tts_orpheus_timeout_seconds
        return self._settings.tts_piper_timeout_seconds


def estimate_wav_duration(audio_bytes: bytes) -> float | None:
    """Best-effort WAV duration helper for tests and future metadata."""

    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            return frames / float(rate) if rate else None
    except wave.Error:
        return None
