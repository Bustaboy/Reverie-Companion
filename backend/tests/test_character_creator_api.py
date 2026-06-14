"""API hardening coverage for M6 creator management and validation flows."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.routes.characters import get_creator_service
from app.main import app
from app.repositories.character_repo import CharacterRepository
from app.repositories.creator_draft_repo import CreatorDraftRepository
from app.services.character_creator_service import (
    CharacterCreatorDraft,
    CharacterCreatorDraftCreate,
    CharacterCreatorService,
)
from app.services.character_service import CharacterService


def _minimal_draft_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "draft_id": "draft-api-aria",
        "character_id": "draft_api_aria",
        "display_name": "Aria",
        "adult_age_range": "late_20s_adult",
        "adult_only_confirmed": True,
        "species_or_type": "human",
        "core_traits": ["warm", "playful"],
    }
    payload.update(overrides)
    return payload


def _service(tmp_path) -> CharacterCreatorService:
    db_path = tmp_path / "characters.sqlite3"
    return CharacterCreatorService(
        draft_repository=CreatorDraftRepository(db_path),
        character_service=CharacterService(CharacterRepository(db_path)),
    )


def _client_with_service(service: CharacterCreatorService) -> TestClient:
    app.dependency_overrides[get_creator_service] = lambda: service
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_creator_request_validation_returns_friendly_adult_guidance() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/characters/creator/validate",
        json=_minimal_draft_payload(species_or_type="childlike waif"),
    )

    assert response.status_code == 422
    body = response.json()
    assert body["message"] == "Some fields need attention before Reverie can continue."
    assert body["next_steps"] == [
        "Review the listed fields, update the values, and try again."
    ]
    assert body["details"][0]["field"] == "species_or_type"
    assert "clearly adult fictional companion" in body["details"][0]["friendly_message"]


def test_creator_missing_draft_errors_include_recovery_steps(tmp_path) -> None:
    client = _client_with_service(_service(tmp_path))

    response = client.post("/api/characters/creator/drafts/missing-draft/review")

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "creator_draft_not_found"
    assert detail["draft_id"] == "missing-draft"
    assert "Pick an existing creator draft" in detail["next_steps"][0]


def test_creator_finalize_validation_error_is_structured_and_actionable(tmp_path) -> None:
    service = _service(tmp_path)
    invalid = CharacterCreatorDraft.model_validate(_minimal_draft_payload()).model_copy(
        update={"adult_only_confirmed": False}
    )
    service.create_draft(CharacterCreatorDraftCreate(draft=invalid))
    client = _client_with_service(service)

    response = client.post(
        "/api/characters/creator/drafts/draft-api-aria/finalize",
        json={"delete_draft_after_finalize": False},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "creator_draft_invalid"
    assert detail["retryable"] is False
    assert "clearly adult" in detail["next_steps"][0]
    assert "adult" in detail["error"].lower()


def test_creator_import_validation_errors_do_not_escape_as_server_errors(tmp_path) -> None:
    client = _client_with_service(_service(tmp_path))

    response = client.post(
        "/api/characters/creator/import",
        json={
            "payload": {
                "kind": "draft",
                "data": _minimal_draft_payload(display_name="teen-coded import"),
            }
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "character_import_invalid"
    assert detail["retryable"] is False
    assert "underage" in detail["error"].lower() or "adult" in detail["error"].lower()
