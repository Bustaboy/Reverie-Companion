"""Coverage for opt-in personal LoRA training foundations."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from app.core.personal_lora import PersonalLoRATrainer, PersonalLoRATrainerConfig


class PersonalLoRATrainerTests(unittest.TestCase):
    def test_collect_requires_opt_in_and_user_approval_before_training(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = PersonalLoRATrainer(self._config(temp_dir))
            entry = self._entry()

            item = trainer.collect_from_journal_entry(entry)

            self.assertIsNotNone(item)
            assert item is not None
            self.assertFalse(item["approved_by_user"])
            self.assertEqual(item["review_status"], "needs_review")
            self.assertTrue(item["safety"]["raw_transcript_excluded"])
            self.assertEqual(trainer.status()["example_counts"]["needs_review"], 1)

            with self.assertRaises(ValueError):
                trainer.start_training(character_id="default_companion")

            approved = trainer.approve_example(item["item_id"], approved=True)
            self.assertTrue(approved["approved_by_user"])
            self.assertEqual(approved["review_status"], "approved")

            job = trainer.start_training(character_id="default_companion", rank=8, max_steps=2)
            self.assertEqual(job["status"], "queued")
            self.assertEqual(job["config"]["rank"], 8)
            self.assertTrue(job["safety"]["chat_non_blocking"])

            self._wait_for_job_terminal(trainer, job["job_id"])
            completed = trainer.get_job(job["job_id"])
            self.assertIsNotNone(completed)
            assert completed is not None
            self.assertEqual(completed["status"], "completed")
            manifest = trainer.rollback_adapter(completed["adapter_id"])
            self.assertFalse(manifest["enabled"])

    def test_sensitive_entries_are_not_collected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = PersonalLoRATrainer(self._config(temp_dir))
            entry = self._entry()
            entry["sensitivity_tags"] = ["intimate_content"]

            self.assertIsNone(trainer.collect_from_journal_entry(entry))
            self.assertEqual(trainer.status()["example_counts"]["total"], 0)

    def _config(self, temp_dir: str) -> PersonalLoRATrainerConfig:
        return PersonalLoRATrainerConfig(
            root_path=Path(temp_dir) / "personal_lora",
            enabled=True,
            collect_examples=True,
            max_steps=2,
        )

    def _entry(self) -> dict[str, object]:
        return {
            "entry_id": "journal_training_test",
            "created_at": "2026-06-11T12:00:00+00:00",
            "status": "active",
            "character_summary": "I learned to keep reassurance gentle and consistent.",
            "structured_summary": {
                "growth_hypotheses": [
                    "Future responses should preserve reassurance before moving on."
                ]
            },
            "insights": [
                {
                    "kind": "growth_hypothesis",
                    "summary": "Reassurance should become more consistent.",
                    "confidence": 0.82,
                    "memory_worthy": True,
                }
            ],
            "themes": ["trust", "reassurance"],
            "confidence": 0.84,
            "evidence_count": 3,
            "sensitivity_tags": [],
            "training_eligibility": "eligible",
            "linked_memory_ids": ["mem_test"],
            "rollback_id": "rollback_training_test",
        }

    def _wait_for_job_terminal(self, trainer: PersonalLoRATrainer, job_id: str) -> None:
        for _ in range(40):
            job = trainer.get_job(job_id)
            if job and job.get("status") in {"completed", "cancelled", "failed"}:
                return
            time.sleep(0.05)
        self.fail("training job did not reach a terminal state")


if __name__ == "__main__":
    unittest.main()
