"""Local resource status routes for 8GB-aware UI warnings."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.resources import ResourceStatusResponse, VRAMStatus
from app.services.resource_coordinator import (
    ResourcePressureLevel,
    resource_coordinator,
)

router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.get("/status", response_model=ResourceStatusResponse)
async def resource_status() -> ResourceStatusResponse:
    """Return lightweight local resource pressure diagnostics.

    This route intentionally avoids heavyweight dependencies and is safe to poll
    slowly from Settings or status chips. Optional media features use the same
    coordinator policy, so the UI explanations match backend behavior.
    """

    decision = resource_coordinator.evaluate_vram_for_workload(workload="status")
    notes = [
        "TTS has priority over image generation.",
        "Image generation is serialized and should run ComfyUI with --lowvram on 8GB GPUs.",
    ]
    if decision.level in {ResourcePressureLevel.high, ResourcePressureLevel.critical}:
        notes.append(
            "Close other GPU-heavy apps or wait for current media work to finish before raising quality."
        )
    if decision.snapshot.free_mb is None:
        notes.append(
            "Install NVIDIA drivers/nvidia-smi or torch with CUDA for live VRAM telemetry."
        )

    return ResourceStatusResponse(
        pressure=decision.level.value,
        message=decision.message,
        vram=VRAMStatus(
            free_mb=decision.snapshot.free_mb,
            total_mb=decision.snapshot.total_mb,
            used_mb=decision.snapshot.used_mb,
            source=decision.snapshot.source,
        ),
        active_tts=resource_coordinator.tts_active,
        active_image_jobs=resource_coordinator.active_image_jobs,
        can_start_optional_gpu_work=decision.can_start,
        should_downgrade=decision.should_downgrade,
        should_unload_optional_models=decision.should_unload_optional_models,
        recommended_image_preset=decision.recommended_image_preset,
        recommended_tts_backend=decision.recommended_tts_backend,
        notes=notes,
    )
