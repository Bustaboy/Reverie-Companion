"""Compatibility import for the canonical voice manager service.

The active FastAPI app keeps services under `backend/app/services`; this module
exists so milestone references to `backend/services/voice_manager.py` resolve to
the same implementation without duplicating logic.
"""

from app.services.voice_manager import (  # noqa: F401
    VoiceManager,
    VoiceManagerError,
    VoiceProfileAlreadyExists,
    VoiceProfileNotFound,
    VoiceProfileStore,
)
