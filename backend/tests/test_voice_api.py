"""Tests for zero-shot voice clone API."""

import base64

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app


def test_create_voice_clone_stores_reference_and_assigns_character(tmp_path) -> None:
    app = create_app()
    settings = Settings(voice_profile_store_path=str(tmp_path / "voices.json"))
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    response = client.post(
        "/api/voices/clone",
        json={
            "name": "Tara Clone",
            "character_id": "tara",
            "mime_type": "audio/wav",
            "duration_seconds": 8.0,
            "audio_base64": base64.b64encode(b"fake wav bytes").decode("ascii"),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["assigned_character_id"] == "tara"
    assert body["profile"]["metadata"]["cloning_mode"] == "zero_shot"
    assert body["profile"]["reference_audio_path"].endswith(".wav")
    assert (tmp_path / "references").exists()
