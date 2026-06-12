"""Compatibility module for the TTS service.

The active FastAPI backend lives under `backend/app/*`; this shim preserves the
Milestone 3 path named in the task brief while re-exporting the production
service implementation.
"""

from app.services.tts_service import TTSGenerationResult, TTSService, TTSServiceError

__all__ = ["TTSGenerationResult", "TTSService", "TTSServiceError"]
