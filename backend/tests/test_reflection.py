"""Smoke coverage for the local-first ReflectionManager."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from app.core.reflection import ReflectionManager, ReflectionManagerConfig


class FakeMemory:
    """Small MemoryManager stand-in that keeps tests offline and deterministic."""

    def __init__(
        self,
        *,
        add_failure: Exception | None = None,
        search_failure: Exception | None = None,
    ) -> None:
        self.add_failure = add_failure
        self.search_failure = search_failure
        self.stored: list[dict[str, Any]] = []

    def add_memory(self, text: str, metadata: dict[str, Any]) -> dict[str, Any]:
        if self.add_failure:
            raise self.add_failure
        memory_id = f"mem_fake_{len(self.stored) + 1}"
        self.stored.append({"id": memory_id, "text": text, "metadata": metadata})
        return {"id": memory_id, "text": text, "metadata": metadata}

    def search_memories(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        if self.search_failure:
            raise self.search_failure
        return [
            {
                "id": item["id"],
                "text": item["text"],
                "score": 0.91,
                "metadata": item["metadata"],
            }
            for item in self.stored[:limit]
        ]


class ReflectionManagerSmokeTests(unittest.TestCase):
    def test_trigger_reflection_saves_journal_and_promotes_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_memory = FakeMemory()
            manager = self._manager(temp_dir, fake_memory)

            entry = manager.trigger_reflection(
                [
                    {
                        "role": "user",
                        "content": (
                            "I love when you remember our gentle routines; "
                            "please reassure me when I feel anxious."
                        ),
                    },
                    {
                        "role": "assistant",
                        "content": "I will remember that and keep us feeling safe.",
                    },
                ]
            )

            self.assertTrue(entry["entry_id"].startswith("journal_"))
            self.assertEqual(entry["linked_memory_ids"], ["mem_fake_1"])
            self.assertEqual(len(fake_memory.stored), 1)
            self.assertEqual(manager.get_recent_journal_entries(limit=1)[0], entry)

            stored_memory = fake_memory.stored[0]
            metadata = stored_memory["metadata"]
            self.assertEqual(metadata["source"], "reflection_journal")
            self.assertEqual(metadata["journal_entry_id"], entry["entry_id"])
            self.assertEqual(metadata["rollback_id"], entry["rollback_id"])
            self.assertEqual(metadata["privacy_tags"], ["local_only"])
            self.assertEqual(metadata["training_eligibility"], "eligible")
            self.assertIsNotNone(entry.get("growth_notification"))
            growth_notification = entry["growth_notification"]
            self.assertIn("Reverie seems to be growing", growth_notification["message"])
            self.assertIn("no raw conversation text", growth_notification["why"])
            self.assertEqual(growth_notification["journal_entry_id"], entry["entry_id"])
            self.assertIn("dismiss", growth_notification["controls"])
            self.assertGreaterEqual(
                metadata["promotion_score"],
                entry["metadata"]["memory_promotion"]["threshold"],
            )
            self.assertIn("provenance", metadata)
            self.assertIn("source_turn_indices", metadata)
            self.assertIn("Use as reflective context only", stored_memory["text"])

            journal_lines = self._journal_lines(temp_dir)
            self.assertEqual(len(journal_lines), 1)
            self.assertEqual(journal_lines[0]["linked_memory_ids"], ["mem_fake_1"])

    def test_relevant_reflections_fall_back_to_journal_keywords(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_memory = FakeMemory(search_failure=RuntimeError("vectors offline"))
            manager = self._manager(temp_dir, fake_memory)
            entry = manager.trigger_reflection(
                [
                    {
                        "role": "user",
                        "content": "Please remember that reassurance helps me trust you.",
                    },
                    {
                        "role": "assistant",
                        "content": "I will keep that trust and reassurance in mind.",
                    },
                ]
            )

            relevant = manager.get_relevant_reflections("trust and reassurance")

            self.assertEqual(
                [item["entry_id"] for item in relevant], [entry["entry_id"]]
            )

    def test_memory_promotion_failure_does_not_discard_journal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_memory = FakeMemory(add_failure=RuntimeError("memory store offline"))
            manager = self._manager(temp_dir, fake_memory)

            entry = manager.trigger_reflection(
                [
                    {
                        "role": "user",
                        "content": "I love when you remember our routine and reassure me.",
                    },
                    {"role": "assistant", "content": "I will remember the feeling."},
                ]
            )

            self.assertEqual(entry["linked_memory_ids"], [])
            self.assertEqual(len(manager.get_recent_journal_entries(limit=5)), 1)
            self.assertTrue(entry["metadata"]["memory_promotion"]["should_promote"])
            self.assertEqual(
                self._journal_lines(temp_dir)[0]["entry_id"], entry["entry_id"]
            )

    def _manager(self, temp_dir: str, fake_memory: FakeMemory) -> ReflectionManager:
        return ReflectionManager(
            memory_manager=fake_memory,  # type: ignore[arg-type]
            config=ReflectionManagerConfig(
                journal_path=Path(temp_dir) / "reflection" / "journal.jsonl",
                user_id="local_user",
                session_id="test_session",
            ),
        )

    def _journal_lines(self, temp_dir: str) -> list[dict[str, Any]]:
        journal_path = Path(temp_dir) / "reflection" / "journal.jsonl"
        return [json.loads(line) for line in journal_path.read_text().splitlines()]


if __name__ == "__main__":
    unittest.main()
