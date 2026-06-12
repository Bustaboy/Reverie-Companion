"""Growth loop controls: reflections, notifications, and personal LoRA foundation."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.lora import (
    PersonalLoRAError,
    PersonalLoRATrainer,
    get_personal_lora_trainer,
)

router = APIRouter(prefix="/growth", tags=["growth"])


class PersonalLoRASettingsUpdate(BaseModel):
    """Patchable opt-in and conservative training controls."""

    collection_opt_in: bool | None = None
    training_opt_in: bool | None = None
    rank: int | None = Field(default=None, ge=8, le=16)
    max_steps: int | None = Field(default=None, ge=10, le=120)
    learning_rate: float | None = Field(default=None, ge=0.00001, le=0.0002)
    batch_size: int | None = Field(default=None, ge=1, le=2)
    gradient_accumulation_steps: int | None = Field(default=None, ge=4, le=16)
    max_sequence_length: int | None = Field(default=None, ge=256, le=1024)
    pause_during_chat: bool | None = None
    require_review_before_training: bool | None = None
    require_approval_before_applying: bool | None = None
    auto_training_enabled: bool | None = None
    training_frequency_hours: int | None = Field(default=None, ge=6, le=168)
    min_training_examples: int | None = Field(default=None, ge=1, le=256)
    min_new_examples_for_auto_training: int | None = Field(default=None, ge=1, le=64)
    min_memory_links_for_auto_training: int | None = Field(default=None, ge=0, le=64)
    max_auto_jobs_per_day: int | None = Field(default=None, ge=1, le=3)
    active_adapter_id: str | None = None
    rollback_adapter_id: str | None = None


def get_lora_trainer() -> PersonalLoRATrainer:
    """Provide the process-local personal LoRA trainer."""

    return get_personal_lora_trainer()


@router.get("/personal-lora")
async def personal_lora_status(
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
) -> dict[str, Any]:
    """Return settings, current job, and local review queue summary."""

    try:
        examples = trainer.list_examples()
        return {
            "settings": trainer.get_settings(),
            "current_job": trainer.get_current_job(),
            "training_status": trainer.get_training_status(),
            "examples": examples[:50],
            "counts": {
                "pending_review": sum(
                    1 for item in examples if item.get("status") == "pending_review"
                ),
                "approved": sum(
                    1 for item in examples if item.get("status") == "approved"
                ),
                "rejected": sum(
                    1 for item in examples if item.get("status") == "rejected"
                ),
            },
        }
    except PersonalLoRAError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


@router.patch("/personal-lora/settings")
async def update_personal_lora_settings(
    update: PersonalLoRASettingsUpdate,
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
) -> dict[str, Any]:
    """Update explicit opt-in, review, rollback, and small-rank settings."""

    updates = {
        key: value for key, value in update.model_dump().items() if value is not None
    }
    try:
        return {"settings": trainer.update_settings(updates)}
    except PersonalLoRAError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


@router.post("/personal-lora/examples/{item_id}/approve")
async def approve_personal_lora_example(
    item_id: str,
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
) -> dict[str, Any]:
    """Approve a collected training example for future adapter training."""

    try:
        return {"example": trainer.approve_example(item_id)}
    except PersonalLoRAError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post("/personal-lora/examples/{item_id}/reject")
async def reject_personal_lora_example(
    item_id: str,
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
) -> dict[str, Any]:
    """Reject a collected example so training cannot use it."""

    try:
        return {"example": trainer.reject_example(item_id)}
    except PersonalLoRAError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.delete("/personal-lora/examples/{item_id}")
async def delete_personal_lora_example(
    item_id: str,
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
) -> dict[str, Any]:
    """Tombstone a local training example for rollback/deletion."""

    try:
        return {"example": trainer.delete_example(item_id)}
    except PersonalLoRAError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post("/personal-lora/evaluate-auto")
async def evaluate_personal_lora_auto_training(
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
) -> dict[str, Any]:
    """Evaluate automated thresholds and queue training if eligible."""

    try:
        return {"job": trainer.evaluate_auto_training()}
    except PersonalLoRAError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.post("/personal-lora/adapters/{adapter_id}/approve")
async def approve_personal_lora_adapter(
    adapter_id: str,
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
) -> dict[str, Any]:
    """Approve and apply a completed adapter update."""

    try:
        return {"job": trainer.approve_adapter_update(adapter_id)}
    except PersonalLoRAError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post("/personal-lora/adapters/{adapter_id}/reject")
async def reject_personal_lora_adapter(
    adapter_id: str,
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
) -> dict[str, Any]:
    """Reject a completed adapter update without applying it."""

    try:
        return {"job": trainer.reject_adapter_update(adapter_id)}
    except PersonalLoRAError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post("/personal-lora/start")
async def start_personal_lora_training(
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
) -> dict[str, Any]:
    """Start a safe, single background personal LoRA foundation job."""

    try:
        return {"job": trainer.start_training()}
    except PersonalLoRAError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.post("/personal-lora/stop")
async def stop_personal_lora_training(
    trainer: Annotated[PersonalLoRATrainer, Depends(get_lora_trainer)],
) -> dict[str, Any]:
    """Cancel the active background personal LoRA job if one is running."""

    try:
        return {"job": trainer.stop_training()}
    except PersonalLoRAError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
