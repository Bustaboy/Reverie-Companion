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
                    "require_review_before_training": True,
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

    def test_automated_training_uses_approved_growth_thresholds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = PersonalLoRATrainer(
                PersonalLoRATrainerConfig(
                    root_path=Path(temp_dir),
                    min_training_examples=1,
                    min_new_examples_since_training=1,
                    dry_run_step_delay_seconds=0,
                )
            )
            trainer.update_settings(
                {
                    "collection_opt_in": True,
                    "training_opt_in": True,
                    "auto_training_enabled": True,
                    "min_training_examples": 1,
                    "min_new_examples_since_training": 1,
                }
            )
            example = trainer.collect_from_journal_entry(high_quality_entry())

            self.assertIsNotNone(example)
            assert example is not None
            self.assertEqual(example["status"], "approved")
            decision = trainer.auto_training_decision(trigger_reason="test_growth")
            self.assertTrue(decision["should_train"])

            job = trainer.evaluate_auto_training(trigger_reason="test_growth")
            self.assertIsNotNone(job)
            assert job is not None
            self.assertEqual(job["trigger_reason"], "test_growth")
            self.assertIn("learning_focus", job)
            stopped_or_finished = trainer.stop_training()
            self.assertIsNotNone(stopped_or_finished)

    def test_adapter_application_can_wait_for_manual_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = PersonalLoRATrainer(
                PersonalLoRATrainerConfig(
                    root_path=Path(temp_dir),
                    min_training_examples=1,
                    min_new_examples_since_training=1,
                    dry_run_step_delay_seconds=0,
                )
            )
            trainer.update_settings(
                {
                    "collection_opt_in": True,
                    "training_opt_in": True,
                    "require_approval_before_applying": True,
                    "min_training_examples": 1,
                    "min_new_examples_since_training": 1,
                    "max_steps": 10,
                }
            )
            trainer.collect_from_journal_entry(high_quality_entry())
            trainer.start_training()
            worker = trainer._worker
            if worker is not None:
                worker.join(timeout=2)
            completed = trainer.get_current_job()

            self.assertIsNotNone(completed)
            assert completed is not None
            self.assertEqual(completed["application_status"], "pending_approval")
            adapter_id = completed["adapter_id"]
            assert adapter_id is not None
            approved = trainer.approve_adapter_application(adapter_id)
            self.assertEqual(approved["application_status"], "applied")
            self.assertEqual(trainer.get_settings()["active_adapter_id"], adapter_id)


if __name__ == "__main__":
    unittest.main()
