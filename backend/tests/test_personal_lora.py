"""Coverage for opt-in personal LoRA foundation controls."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.core.lora import (
    PersonalLoRAError,
    PersonalLoRATrainer,
    PersonalLoRATrainerConfig,
)


def high_quality_entry() -> dict[str, object]:
    return {
        "entry_id": "journal_lora_1",
        "status": "active",
        "character_summary": "I learned that steady reassurance helps trust feel warmer.",
        "linked_memory_ids": ["mem_1"],
        "insights": [
            {
                "kind": "relationship_continuity",
                "summary": "Use gentle reassurance when the user sounds anxious.",
                "memory_worthy": True,
                "source_turn_indices": [1, 2],
            }
        ],
        "themes": ["trust", "reassurance"],
        "confidence": 0.82,
        "evidence_count": 3,
        "privacy_tags": ["local_only"],
        "sensitivity_tags": [],
        "rollback_id": "rollback_journal_lora_1",
    }


class PersonalLoRATrainerTests(unittest.TestCase):
    def test_collection_requires_opt_in_and_review_before_training(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = PersonalLoRATrainer(
                PersonalLoRATrainerConfig(
                    root_path=Path(temp_dir), dry_run_step_delay_seconds=0
                )
            )

            self.assertIsNone(trainer.collect_from_journal_entry(high_quality_entry()))

            trainer.update_settings(
                {
                    "collection_opt_in": True,
                    "training_opt_in": True,
                    "min_training_examples": 1,
                }
            )
            example = trainer.collect_from_journal_entry(high_quality_entry())

            self.assertIsNotNone(example)
            assert example is not None
            self.assertEqual(example["status"], "pending_review")
            self.assertFalse(example["approved_by_user"])
            with self.assertRaises(PersonalLoRAError):
                trainer.start_training()

            approved = trainer.approve_example(example["item_id"])
            self.assertEqual(approved["status"], "approved")
            self.assertTrue(approved["approved_by_user"])

            job = trainer.start_training()
            self.assertIn(job["status"], {"queued", "running"})
            stopped_or_finished = trainer.stop_training()
            self.assertIsNotNone(stopped_or_finished)

    def test_rank_and_training_defaults_stay_8gb_conservative(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = PersonalLoRATrainer(
                PersonalLoRATrainerConfig(root_path=Path(temp_dir))
            )
            settings = trainer.update_settings(
                {
                    "collection_opt_in": True,
                    "training_opt_in": True,
                    "rank": 99,
                    "max_steps": 999,
                    "learning_rate": 1.0,
                    "gradient_accumulation_steps": 99,
                    "max_sequence_length": 4096,
                }
            )

            self.assertEqual(settings["rank"], 16)
            self.assertEqual(settings["batch_size"], 1)
            self.assertEqual(settings["target_vram_gb"], 8)
            self.assertLessEqual(settings["max_steps"], 120)
            self.assertLessEqual(settings["learning_rate"], 0.0002)
            self.assertLessEqual(settings["max_sequence_length"], 1024)

    def test_auto_training_thresholds_and_adapter_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = PersonalLoRATrainer(
                PersonalLoRATrainerConfig(
                    root_path=Path(temp_dir), dry_run_step_delay_seconds=0
                )
            )
            trainer.update_settings(
                {
                    "collection_opt_in": True,
                    "training_opt_in": True,
                    "auto_training_enabled": True,
                    "min_training_examples": 1,
                    "min_new_examples_for_auto_training": 1,
                    "min_memory_links_for_auto_training": 1,
                    "max_steps": 1,
                }
            )
            example = trainer.collect_from_journal_entry(high_quality_entry())
            assert example is not None
            trainer.approve_example(example["item_id"])

            job = trainer.evaluate_auto_training()
            self.assertIsNotNone(job)
            assert job is not None
            while trainer.get_current_job()["status"] in {"queued", "running"}:  # type: ignore[index]
                pass
            status = trainer.get_training_status()
            self.assertEqual(status["status"], "completed")
            self.assertTrue(status["learning_feedback"])
            pending = status["pending_adapter_update"]
            self.assertIsNotNone(pending)
            assert pending is not None
            applied = trainer.approve_adapter_update(pending["adapter_id"])
            self.assertEqual(applied["apply_status"], "applied")
            self.assertEqual(trainer.get_settings()["active_adapter_id"], pending["adapter_id"])


if __name__ == "__main__":
    unittest.main()
