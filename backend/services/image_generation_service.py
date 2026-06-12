"""Compatibility import for the canonical image generation service.

The active FastAPI app keeps services under `backend/app/services`; this module
exists so milestone references to `backend/services/image_generation_service.py`
resolve to the same implementation without duplicating queue logic.
"""

from app.services.image_generation_service import (  # noqa: F401
    ComfyUIAdapter,
    ImageGenerationService,
    ImageGenerationServiceError,
    ImagePresetBudget,
    VRAMMonitor,
    VRAMSnapshot,
    get_image_generation_service,
)
