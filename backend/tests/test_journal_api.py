"""API coverage for self-reflection journal reads."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.api.routes.journal import get_journal_manager
from app.main import app


class FakeJournalManager:
    """Small route dependency stand-in that keeps API tests offline."""

    def get_recent_journal_entries(self, limit: int = 5) -> list[dict[str, object]]:
        return [
            {
                "entry_id": "journal_test",
                "created_at": "2026-06-11T12:00:00+00:00",
                "status": "active",
                "character_summary": "I felt safe enough to keep a tender note.",
                "themes": ["trust", "growth"],
                "confidence": 0.82,
                "insights": [
                    {
                        "kind": "relationship",
                        "summary": "Trust is becoming a stable emotional theme.",
                        "confidence": 0.8,
                        "evidence_count": 2,
                        "themes": ["trust"],
                    }
                ],
                "metadata": {"memory_promotion": {"should_promote": False}},
            }
        ][:limit]


class JournalApiTests(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_recent_journal_entries_returns_bounded_entries(self) -> None:
        app.dependency_overrides[get_journal_manager] = lambda: FakeJournalManager()
        client = TestClient(app)

        response = client.get("/journal/entries?limit=10")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["entries"][0]["entry_id"], "journal_test")
        self.assertEqual(body["entries"][0]["themes"], ["trust", "growth"])


if __name__ == "__main__":
    unittest.main()
