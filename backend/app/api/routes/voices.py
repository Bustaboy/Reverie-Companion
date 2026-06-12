"""Voice profile and zero-shot cloning API routes."""

from __future__ import annotations

import base64
import binascii
import re
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.models.voice import VoiceCloneRequest, VoiceCloneResponse, VoiceProfile
from app.services.voice_manager import VoiceManager, VoiceManagerError

router = APIRouter(prefix="/api/voices", tags=["voices"])

_MAX_REFERENCE_AUDIO_BYTES = 16 * 1024 * 1024
_ALLOWED_AUDIO_MIME_TYPES = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
}


def get_voice_manager(
    settings: Annotated[Settings, Depends(get_settings)],
) -> VoiceManager:
    """Provide a lightweight local voice manager."""

    return VoiceManager(settings=settings)


@router.get("", response_model=list[VoiceProfile])
async def list_voice_profiles(
    voice_manager: Annotated[VoiceManager, Depends(get_voice_manager)],
) -> list[VoiceProfile]:
    """List durable local voice profiles for settings UI."""

    voice_manager.ensure_default_narrator_voice()
    return voice_manager.list_voice_profiles()


@router.post("/clone", response_model=VoiceCloneResponse, status_code=status.HTTP_201_CREATED)
async def create_voice_clone(
    request: VoiceCloneRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    voice_manager: Annotated[VoiceManager, Depends(get_voice_manager)],
) -> VoiceCloneResponse:
    """Store reference audio and create an Orpheus zero-shot voice profile.

    This does not preload Orpheus or train an adapter. The reference is saved
    locally and attached to the profile so synthesis can pass it to Orpheus only
    when a voice line is requested.
    """

    extension = _extension_for_mime_type(request.mime_type)
    try:
        audio_bytes = base64.b64decode(request.audio_base64, validate=True)
    except binascii.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Reference audio was not valid base64."},
        ) from exc

    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Reference audio cannot be empty."},
        )
    if len(audio_bytes) > _MAX_REFERENCE_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": "Reference audio must be 16 MB or smaller."},
        )

    voice_id = f"clone_{_slugify(request.name)}_{uuid4().hex[:8]}"
    reference_dir = Path(settings.voice_profile_store_path).expanduser().parent / "references"
    reference_dir.mkdir(parents=True, exist_ok=True)
    reference_path = reference_dir / f"{voice_id}{extension}"
    reference_path.write_bytes(audio_bytes)

    profile = VoiceProfile(
        voice_id=voice_id,
        name=request.name,
        type="character",
        reference_audio_path=str(reference_path),
        metadata={
            "backend": "orpheus",
            "backend_voice_id": voice_id,
            "cloning_ready": True,
            "cloning_mode": "zero_shot",
            "created_by": "voice_clone_ui",
            "mime_type": request.mime_type,
            "duration_seconds": request.duration_seconds,
            "reference_audio_bytes": len(audio_bytes),
        },
    )

    try:
        created = voice_manager.create_voice_profile(profile)
        assigned_character_id = None
        if request.character_id:
            voice_manager.assign_voice_to_character(request.character_id, created.voice_id)
            assigned_character_id = request.character_id
    except VoiceManagerError as exc:
        reference_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        ) from exc

    return VoiceCloneResponse(
        profile=created,
        assigned_character_id=assigned_character_id,
        message=(
            "Voice profile saved locally. Orpheus zero-shot cloning will use "
            "the reference audio at synthesis time."
        ),
    )


def _extension_for_mime_type(mime_type: str) -> str:
    normalized = mime_type.split(";", 1)[0].strip().lower()
    if normalized not in _ALLOWED_AUDIO_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"error": "Use WAV, WebM, OGG, or MP3 reference audio."},
        )
    return _ALLOWED_AUDIO_MIME_TYPES[normalized]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return slug[:40] or "voice"
