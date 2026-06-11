"""Coverage for central growth loop orchestration."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.growth import GrowthOrchestrator
from app.core.lora import PersonalLoRATrainer, PersonalLoRATrainerConfig
from app.models.chat import ChatMessage, ChatRequest


class FakeReflectionManager:
    def __init__(self) -> None:
        self.triggered = 0

    def get_recent_journal_entries(self, limit: int = 5) -> list[dict[str, Any]]:
        return []

    def trigger_reflection(self, history: list[dict[str, str]]) -> dict[str, Any]:
        self.triggered += 1
        return {
            "entry_id": "journal_growth_loop",
            "status": "active",
            "character_summary": "I learned to carry reassurance forward gradually.",
            "linked_memory_ids": ["mem_growth"],
            "insights": [
                {
                    "kind": "relationship_continuity",
                    "summary": "Keep reassurance steady without overreacting.",
                    "memory_worthy": True,
                    "source_turn_indices": [0, 1],
                }
            ],
            "themes": ["trust", "reassurance"],
            "confidence": 0.86,
            "evidence_count": 3,
            "privacy_tags": ["local_only"],
            "sensitivity_tags": [],
            "rollback_id": "rollback_growth_loop",
            "growth_notification": None,
        }


class GrowthOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        GrowthOrchestrator._reflection_lock = None
        GrowthOrchestrator._last_reflection_started_at = 0.0
        GrowthOrchestrator._inflight_reflection_tasks.clear()
        GrowthOrchestrator._last_growth_notification_at = 0.0
        GrowthOrchestrator._emitted_growth_notification_ids.clear()

    def test_background_reflection_collects_lora_candidate_when_opted_in(self) -> None:
        asyncio.run(self._assert_background_reflection_collects_lora_candidate())

    async def _assert_background_reflection_collects_lora_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = PersonalLoRATrainer(
                PersonalLoRATrainerConfig(
                    root_path=Path(temp_dir), dry_run_step_delay_seconds=0
                )
            )
            trainer.update_settings({"collection_opt_in": True})
            reflection = FakeReflectionManager()
            orchestrator = GrowthOrchestrator(
                settings=Settings(
                    memory_enabled=False,
                    reflection_min_interval_seconds=0,
                    reflection_user_message_interval=1,
                    personal_lora_enabled=True,
                ),
                reflection_manager=reflection,  # type: ignore[arg-type]
                lora_trainer=trainer,
            )
            request = ChatRequest(
                stream=False,
                messages=[
                    ChatMessage(
                        role="user", content="Please remember that reassurance helps."
                    ),
                    ChatMessage(role="assistant", content="I will hold that gently."),
                ],
            )

            orchestrator.schedule_reflection_if_due(request, request_id="req-growth")
            await asyncio.gather(*GrowthOrchestrator._inflight_reflection_tasks)

            examples = trainer.list_examples()
            self.assertEqual(reflection.triggered, 1)
            self.assertEqual(len(examples), 1)
            self.assertEqual(examples[0]["status"], "pending_review")
            self.assertEqual(examples[0]["source_journal_id"], "journal_growth_loop")


if __name__ == "__main__":
    unittest.main()
