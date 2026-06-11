"""Coverage for central growth loop orchestration."""

from __future__ import annotations

import unittest

from app.core.config import Settings
from app.core.growth import GrowthOrchestrator
from app.core.personal_lora import PersonalLoRATrainer, PersonalLoRATrainerConfig
from app.models.chat import ChatMessage


class FakeMemory:
    def get_relevant_context(self, query: str) -> str:
        return f"memory for {query}"


class FakeReflection:
    def __init__(self) -> None:
        self.entries = [
            {
                "entry_id": "journal_growth",
                "status": "active",
                "confidence": 0.82,
                "character_summary": "I am learning to be steadier with trust.",
                "insights": [
                    {
                        "kind": "growth_hypothesis",
                        "summary": "The character should answer with steadier reassurance.",
                    }
                ],
                "growth_notification": {
                    "id": "growth_journal_growth",
                    "journal_entry_id": "journal_growth",
                    "created_at": "2026-06-11T12:00:00+00:00",
                    "message": "Reverie seems to be growing around trust.",
                    "why": "A private reflection found a recurring trust signal.",
                    "theme": "trust",
                    "style": "whisper",
                    "controls": ["dismiss", "review", "disable_similar"],
                },
            }
        ]

    def get_recent_journal_entries(self, limit: int = 5):
        return self.entries[:limit]

    def build_growth_notification(self, entry):
        return entry.get("growth_notification")

    def trigger_reflection(self, history):
        return self.entries[0]


class GrowthOrchestratorTests(unittest.TestCase):
    def test_builds_prompt_guidance_and_natural_notification_decision(self) -> None:
        settings = Settings(
            growth_notification_min_user_messages=2,
            growth_notification_message_interval=2,
            growth_notification_min_interval_seconds=0,
            personal_lora_enabled=True,
            personal_lora_collect_examples=False,
        )
        trainer = PersonalLoRATrainer(
            PersonalLoRATrainerConfig(root_path=__import__("pathlib").Path("/tmp/reverie-test-lora"))
        )
        orchestrator = GrowthOrchestrator(
            settings=settings,
            memory_manager=FakeMemory(),  # type: ignore[arg-type]
            reflection_manager=FakeReflection(),  # type: ignore[arg-type]
            lora_trainer=trainer,
        )

        entries = orchestrator.recent_reflections(limit=1)
        guidance = orchestrator.build_growth_guidance(entries)
        self.assertIn("<character_growth_guidance>", guidance)
        self.assertIn("journal_growth", guidance)
        self.assertIn("steadier reassurance", guidance)

        decision = orchestrator.choose_growth_notification(
            entries,
            user_message_count=2,
            now=100,
            last_notification_at=0,
            emitted_notification_ids=set(),
        )
        self.assertIsNotNone(decision.notification)
        assert decision.notification is not None
        self.assertEqual(decision.notification["id"], "growth_journal_growth")

    def test_reflection_timing_delegates_to_scheduler(self) -> None:
        orchestrator = GrowthOrchestrator(
            settings=Settings(reflection_min_interval_seconds=0),
            memory_manager=FakeMemory(),  # type: ignore[arg-type]
            reflection_manager=FakeReflection(),  # type: ignore[arg-type]
        )
        decision = orchestrator.evaluate_reflection_timing(
            [ChatMessage(role="user", content="Please remember this promise.")],
            now=100,
            last_started_at=0,
            inflight_count=0,
        )
        self.assertTrue(decision.should_schedule)
        self.assertIn("promise", decision.matched_keywords)


if __name__ == "__main__":
    unittest.main()
