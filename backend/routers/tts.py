"""Compatibility module for the TTS FastAPI router.

The production router is mounted from `backend/app/api/routes/tts.py`; this shim
preserves the Milestone 3 path named in the task brief.
"""

from app.api.routes.tts import router

__all__ = ["router"]
