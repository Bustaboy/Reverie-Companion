"""API coverage for editable Memory Browser controls."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from app.api.routes.memory import get_memory_browser_service
from app.core.memory import MemoryManager
from app.main import app


class FakeMemoryBrowserService:
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


class MemoryManagerBrowserEditTests(unittest.TestCase):
    def test_browser_edit_preserves_original_provenance_metadata(self) -> None:
        manager = MemoryManager.__new__(MemoryManager)
        existing_metadata = {
            "source": "reflection_journal",
            "journal_entry_id": "journal_original",
            "provenance": {"source_turn_indices": [1, 2]},
            "source_turn_indices": [1, 2],
            "user_id": "local_user",
            "tags": ["gentle"],
            "importance": 0.72,
            "content_version": 2,
        }

        merged = manager._merge_browser_edit_metadata(  # type: ignore[attr-defined]
            existing_metadata,
            {
                "source": "manual_overwrite",
                "journal_entry_id": "journal_wrong",
                "provenance": {"source_turn_indices": [99]},
                "browser_reviewed": True,
                "review_note": "User corrected the wording.",
            },
            tags=["Grounding", "gentle", "grounding"],
            importance=0.91,
            previous_text="Old reassurance note.",
            previous_updated_at="2026-06-11T12:00:00+00:00",
            text_changed=True,
        )

        self.assertEqual(merged["source"], "reflection_journal")
        self.assertEqual(merged["journal_entry_id"], "journal_original")
        self.assertEqual(merged["provenance"], {"source_turn_indices": [1, 2]})
        self.assertEqual(merged["source_turn_indices"], [1, 2])
        self.assertTrue(merged["browser_reviewed"])
        self.assertEqual(merged["review_note"], "User corrected the wording.")
        self.assertEqual(merged["tags"], ["grounding", "gentle"])
        self.assertEqual(merged["importance"], 0.91)
        self.assertEqual(merged["content_version"], 3)
        self.assertEqual(
            merged["last_ignored_provenance_patch_keys"],
            ["journal_entry_id", "provenance", "source"],
        )
        self.assertEqual(len(merged["edit_history"]), 1)
        self.assertIn("text", merged["edit_history"][0]["changed_fields"])
        self.assertIn("previous_text_hash", merged["edit_history"][0])


class MemoryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_manager = FakeMemoryBrowserService()
        app.dependency_overrides[get_memory_browser_service] = lambda: self.fake_manager
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

        self.fake_manager.memories.append(
            {"id": "mem_old", "text": "Old note", "metadata": {}}
        )
        bulk_response = self.client.post(
            "/memory/memories/bulk-delete", json={"ids": ["mem_old"]}
        )
        self.assertEqual(bulk_response.status_code, 200)
        self.assertEqual(bulk_response.json()["deleted_count"], 1)


if __name__ == "__main__":
    unittest.main()


class MemoryManagerScopeHardeningTests(unittest.TestCase):
    def test_visual_private_write_without_character_id_is_refused(self) -> None:
        manager = MemoryManager.__new__(MemoryManager)
        with self.assertRaises(ValueError):
            manager._enforce_write_scope(  # type: ignore[attr-defined]
                {"source": "visual_feedback", "memory_type": "visual_memory"}
            )

    def test_explicit_shared_or_global_scope_does_not_require_character_id(
        self,
    ) -> None:
        manager = MemoryManager.__new__(MemoryManager)
        shared = {"source": "visual_feedback", "memory_scope": "shared"}
        global_memory = {"source": "visual_feedback", "memory_scope": "global"}
        manager._enforce_write_scope(shared)  # type: ignore[attr-defined]
        manager._enforce_write_scope(global_memory)  # type: ignore[attr-defined]
        self.assertEqual(shared["memory_scope"], "shared")
        self.assertEqual(global_memory["memory_scope"], "global")

    def test_character_filter_excludes_other_private_visual_memories(self) -> None:
        manager = MemoryManager.__new__(MemoryManager)
        self.assertTrue(
            manager._memory_matches_character_scope(  # type: ignore[attr-defined]
                {
                    "metadata": {
                        "character_id": "aria",
                        "memory_scope": "character_private",
                    }
                },
                "aria",
            )
        )
        self.assertFalse(
            manager._memory_matches_character_scope(  # type: ignore[attr-defined]
                {
                    "metadata": {
                        "character_id": "bryn",
                        "memory_scope": "character_private",
                    }
                },
                "aria",
            )
        )
        self.assertTrue(
            manager._memory_matches_character_scope(  # type: ignore[attr-defined]
                {"metadata": {"memory_scope": "shared"}},
                "aria",
            )
        )
