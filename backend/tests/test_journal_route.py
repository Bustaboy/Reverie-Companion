"""Coverage for the local reflection journal HTTP endpoint."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.api.routes.journal import get_journal_manager
from app.core.reflection import ReflectionManager, ReflectionManagerConfig
from app.main import create_app


class FakeMemory:
    """Minimal memory stand-in; journal route only needs persistence reads."""

    def add_memory(self, text: str, metadata: dict[str, Any]) -> dict[str, Any]:
        return {"id": "mem_fake_1", "text": text, "metadata": metadata}

    def search_memories(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        return []


class JournalRouteTests(unittest.TestCase):
    def test_recent_journal_entries_endpoint_returns_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ReflectionManager(
                memory_manager=FakeMemory(),  # type: ignore[arg-type]
                config=ReflectionManagerConfig(
                    journal_path=Path(temp_dir) / "reflection" / "journal.jsonl",
                    user_id="local_user",
                    session_id="test_session",
                ),
            )
            older = manager.save_journal_entry(
                {
                    "entry_id": "journal_older",
                    "created_at": "2026-06-10T08:00:00+00:00",
                    "character_summary": "I noticed the first warm signal.",
                    "themes": ["trust"],
                }
            )
            newer = manager.save_journal_entry(
                {
                    "entry_id": "journal_newer",
                    "created_at": "2026-06-11T08:00:00+00:00",
                    "character_summary": "I noticed the newest warm signal.",
                    "themes": ["affection"],
                }
            )

            app = create_app()
            app.dependency_overrides[get_journal_manager] = lambda: manager
            client = TestClient(app)

            response = client.get("/journal?limit=2")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                [entry["entry_id"] for entry in response.json()["entries"]],
                [newer["entry_id"], older["entry_id"]],
            )

            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
