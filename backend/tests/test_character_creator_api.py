"""Integration coverage for M6 creator management API error clarity."""

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


def _service(tmp_path) -> CharacterCreatorService:
    db_path = tmp_path / "characters.sqlite3"
    return CharacterCreatorService(
        draft_repository=CreatorDraftRepository(db_path),
        character_service=CharacterService(CharacterRepository(db_path)),
    )


def test_creator_api_returns_helpful_not_found_for_draft(tmp_path) -> None:
    service = _service(tmp_path)
    app.dependency_overrides[get_creator_service] = lambda: service
    try:
        client = TestClient(app)
        response = client.get("/api/characters/creator/drafts/missing-draft")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "creator_draft_not_found"
    assert detail["draft_id"] == "missing-draft"
    assert "Refresh the draft list" in detail["error"]


def test_creator_api_import_unknown_kind_returns_accessible_422(tmp_path) -> None:
    service = _service(tmp_path)
    app.dependency_overrides[get_creator_service] = lambda: service
    try:
        client = TestClient(app)
        response = client.post(
            "/api/characters/creator/import",
            json={
                "payload": {
                    "kind": "legacy_card",
                    "data": CharacterCreatorDraft(display_name="Aria").model_dump(
                        mode="json"
                    ),
                }
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "character_import_invalid"
    assert "Choose 'draft'" in detail["error"]
    assert "'character'" in detail["error"]


def test_creator_api_delete_finalized_character_requires_exact_name(tmp_path) -> None:
    service = _service(tmp_path)
    service.create_draft(
        CharacterCreatorDraftCreate(
            draft=CharacterCreatorDraft(
                draft_id="draft-aria", character_id="aria", display_name="Aria"
            )
        )
    )
    service.finalize_draft("draft-aria")
    app.dependency_overrides[get_creator_service] = lambda: service
    try:
        client = TestClient(app)
        response = client.request(
            "DELETE",
            "/api/characters/aria",
            json={"confirm": True, "expected_display_name": "Wrong"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "character_delete_confirmation_required"
    assert "'Aria'" in detail["error"]
    assert "accidental deletion" in detail["error"]
