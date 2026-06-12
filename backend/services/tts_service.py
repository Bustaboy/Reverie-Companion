"""Compatibility import for the canonical TTS service.

The active FastAPI app keeps services under `backend/app/services`; this module
exists so milestone references to `backend/services/tts_service.py` resolve to
the same implementation without duplicating logic.
"""

from app.services.tts_service import (  # noqa: F401
    OrpheusBackend,
    PiperBackend,
    TTSBackendUnavailable,
    TTSGenerationResult,
    TTSInsufficientVRAM,
    TTSService,
    TTSServiceError,
    estimate_wav_duration,
)
