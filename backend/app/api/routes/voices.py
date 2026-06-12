"""Voice profile and zero-shot cloning routes."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.config import Settings, get_settings
from app.models.voice import VoiceProfile, VoiceProfileUpdate
from app.services.voice_manager import VoiceManager, VoiceManagerError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/voices", tags=["voices"])


def get_voice_manager(
    settings: Annotated[Settings, Depends(get_settings)],
) -> VoiceManager:
    return VoiceManager(settings)


@router.get("", response_model=list[VoiceProfile])
def list_voices(
    voice_manager: Annotated[VoiceManager, Depends(get_voice_manager)],
) -> list[VoiceProfile]:
    """Return local voice profiles for voice settings UI."""

    voice_manager.ensure_default_narrator_voice()
    return voice_manager.list_voice_profiles()


@router.post("/clone", response_model=VoiceProfile, status_code=status.HTTP_201_CREATED)
async def create_cloned_voice(
    voice_manager: Annotated[VoiceManager, Depends(get_voice_manager)],
    name: Annotated[str, Form(min_length=1, max_length=120)],
    reference_audio: Annotated[
        UploadFile, File(description="6-15 second reference audio clip")
    ],
    character_id: Annotated[str | None, Form(max_length=120)] = None,
    duration_seconds: Annotated[float | None, Form(ge=0, le=120)] = None,
) -> VoiceProfile:
    """Create a lightweight Orpheus zero-shot voice profile from reference audio."""

    try:
        profile = voice_manager.create_zero_shot_voice_profile(
            name=name,
            audio_file=reference_audio.file,
            filename=reference_audio.filename or "reference.wav",
            content_type=reference_audio.content_type,
            character_id=character_id,
            duration_seconds=duration_seconds,
        )
    except VoiceManagerError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "retryable": False,
                }
            },
        ) from exc
    finally:
        await reference_audio.close()

    logger.info(
        "Created zero-shot voice profile",
        extra={"voice_id": profile.voice_id, "character_id": character_id},
    )
    return profile


@router.patch("/{voice_id}", response_model=VoiceProfile)
def update_voice_profile(
    voice_id: str,
    update: VoiceProfileUpdate,
    voice_manager: Annotated[VoiceManager, Depends(get_voice_manager)],
) -> VoiceProfile:
    """Update voice profile metadata such as per-character mood controls."""

    try:
        return voice_manager.update_voice_profile(voice_id, update)
    except VoiceManagerError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "retryable": False,
                }
            },
        ) from exc
