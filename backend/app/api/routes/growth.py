"""Growth loop and personal LoRA control routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.growth import GrowthOrchestrator, get_growth_orchestrator
from app.core.personal_lora import PersonalLoRATrainer

router = APIRouter(prefix="/growth", tags=["growth"])


class TrainingStartRequest(BaseModel):
    """Request to start an explicit local personal LoRA job."""

    character_id: str | None = Field(default=None, min_length=1, max_length=128)
    rank: int | None = Field(default=None, ge=1, le=16)
    max_steps: int | None = Field(default=None, ge=1, le=1000)


class ExampleReviewRequest(BaseModel):
    """Approve or reject a local dataset candidate."""

    approved: bool


def get_growth_manager() -> GrowthOrchestrator:
    """Provide process-local growth orchestration for route handlers."""

    return get_growth_orchestrator()


def get_lora_trainer(
    growth: Annotated[GrowthOrchestrator, Depends(get_growth_manager)],
) -> PersonalLoRATrainer:
    """Expose the trainer owned by the growth orchestrator."""

    return growth.lora_trainer


@router.get("/status")
async def growth_status(
    growth: Annotated[GrowthOrchestrator, Depends(get_growth_manager)],
) -> dict[str, Any]:
    """Return local growth settings, controls, and training artifact counts."""

    return growth.status()


@router.get("/lora/examples")
async def list_lora_examples(
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    """Return reviewable personal LoRA dataset candidates."""

    examples = trainer.list_examples(limit=limit)
    return {"examples": examples, "count": len(examples)}


@router.patch("/lora/examples/{item_id}")
async def review_lora_example(
    item_id: str,
    request: ExampleReviewRequest,
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
) -> dict[str, Any]:
    """Approve or reject a dataset candidate before training."""

    try:
        example = trainer.approve_example(item_id, approved=request.approved)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Training example not found.", "details": str(exc)},
        ) from exc
    return {"example": example}


@router.delete("/lora/examples/{item_id}")
async def delete_lora_example(
    item_id: str,
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
) -> dict[str, Any]:
    """Tombstone a dataset candidate so it cannot be trained on."""

    try:
        example = trainer.delete_example(item_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Training example not found.", "details": str(exc)},
        ) from exc
    return {"example": example}


@router.post("/lora/train")
async def start_lora_training(
    request: TrainingStartRequest,
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
) -> dict[str, Any]:
    """Start explicit local personal LoRA training in the background."""

    try:
        job = trainer.start_training(
            character_id=request.character_id,
            rank=request.rank,
            max_steps=request.max_steps,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "Personal LoRA training cannot start.", "details": str(exc)},
        ) from exc
    return {"job": job}


@router.post("/lora/train/{job_id}/stop")
async def stop_lora_training(
    job_id: str,
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
) -> dict[str, Any]:
    """Cancel a queued or running personal LoRA training job."""

    try:
        job = trainer.stop_training(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Training job not found.", "details": str(exc)},
        ) from exc
    return {"job": job}


@router.get("/lora/jobs")
async def list_lora_jobs(
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, Any]:
    """Return recent personal LoRA job statuses."""

    jobs = trainer.list_jobs(limit=limit)
    return {"jobs": jobs, "count": len(jobs)}


@router.post("/lora/adapters/{adapter_id}/rollback")
async def rollback_lora_adapter(
    adapter_id: str,
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
) -> dict[str, Any]:
    """Disable a personal LoRA adapter manifest for rollback."""

    try:
        manifest = trainer.rollback_adapter(adapter_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Adapter not found.", "details": str(exc)},
        ) from exc
    return {"adapter": manifest}
