"""API coverage for editable Memory Browser controls."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from app.api.routes.memory import get_memory_browser_manager
from app.main import app


class FakeMemoryBrowserManager:
    """Small dependency stand-in that keeps Memory Browser API tests offline."""

    def __init__(self) -> None:
        self.memories: list[dict[str, Any]] = [
            {
                "id": "mem_trust",
                "text": "User prefers gentle reassurance after anxious moments.",
                "score": 1.0,
                "created_at": "2026-06-11T12:00:00+00:00",
                "updated_at": "2026-06-11T12:00:00+00:00",
                "source": "reflection_journal",
                "metadata": {
                    "character": "Reverie",
                    "themes": ["trust", "reassurance"],
                    "tags": ["gentle"],
                    "importance": 0.86,
                    "journal_entry_id": "journal_1",
                    "provenance": {"source_turn_indices": [1, 2]},
                },
            }
        ]

    def list_memories(self, **kwargs: Any) -> dict[str, Any]:
        query = kwargs.get("query", "").lower()
        items = [item for item in self.memories if query in item["text"].lower()]
        return {"items": items, "total": len(items), "page": 1, "page_size": 20}

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        return next((item for item in self.memories if item["id"] == memory_id), None)

    def update_memory(self, memory_id: str, **kwargs: Any) -> dict[str, Any]:
        memory = self.get_memory(memory_id)
        if memory is None:
            raise KeyError(memory_id)
        memory["text"] = kwargs["text"]
        memory["updated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
        memory["metadata"] = {
            **memory["metadata"],
            **kwargs.get("metadata", {}),
            "tags": kwargs.get("tags", []),
            "importance": kwargs.get("importance"),
        }
        return memory

    def delete_memory(self, memory_id: str) -> bool:
        before = len(self.memories)
        self.memories = [item for item in self.memories if item["id"] != memory_id]
        return len(self.memories) != before

    def bulk_delete_memories(self, **kwargs: Any) -> int:
        ids = set(kwargs.get("ids") or [])
        before = len(self.memories)
        self.memories = [item for item in self.memories if item["id"] not in ids]
        return before - len(self.memories)


class MemoryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_manager = FakeMemoryBrowserManager()
        app.dependency_overrides[get_memory_browser_manager] = lambda: self.fake_manager
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_list_memories_returns_paginated_browser_records(self) -> None:
        response = self.client.get("/memory/memories?q=reassurance&page_size=20")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["id"], "mem_trust")
        self.assertEqual(body["items"][0]["metadata"]["importance"], 0.86)

    def test_update_memory_edits_content_tags_and_importance(self) -> None:
        response = self.client.patch(
            "/memory/memories/mem_trust",
            json={
                "text": "User prefers quiet grounding and gentle reassurance.",
                "tags": ["Grounding", "gentle"],
                "importance": 0.92,
                "metadata": {"review_note": "User-confirmed preference."},
            },
        )

        self.assertEqual(response.status_code, 200)
        memory = response.json()["memory"]
        self.assertEqual(memory["metadata"]["tags"], ["grounding", "gentle"])
        self.assertEqual(memory["metadata"]["importance"], 0.92)
        self.assertIn("quiet grounding", memory["text"])

    def test_delete_and_bulk_delete_remove_memory_records(self) -> None:
        delete_response = self.client.delete("/memory/memories/mem_trust")
        self.assertEqual(delete_response.status_code, 204)
        self.assertIsNone(self.fake_manager.get_memory("mem_trust"))

        self.fake_manager.memories.append({"id": "mem_old", "text": "Old note", "metadata": {}})
        bulk_response = self.client.post(
            "/memory/memories/bulk-delete", json={"ids": ["mem_old"]}
        )
        self.assertEqual(bulk_response.status_code, 200)
        self.assertEqual(bulk_response.json()["deleted_count"], 1)


if __name__ == "__main__":
    unittest.main()
