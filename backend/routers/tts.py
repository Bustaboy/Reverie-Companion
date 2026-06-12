"""Compatibility import for the canonical TTS FastAPI router.

The active FastAPI app keeps routers under `backend/app/api/routes`; this module
exists so milestone references to `backend/routers/tts.py` resolve to the same
router without duplicating route logic.
"""

from app.api.routes.tts import get_tts_service, generate_tts, router  # noqa: F401
