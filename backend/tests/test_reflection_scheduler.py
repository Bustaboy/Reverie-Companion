"""Coverage for lightweight reflection scheduling controls."""

from __future__ import annotations

import unittest

from app.core.config import Settings
from app.core.reflection import ReflectionScheduler
from app.models.chat import ChatMessage


class ReflectionSchedulerTests(unittest.TestCase):
    def test_frequency_adjusts_message_interval_and_cooldown(self) -> None:
        low = ReflectionScheduler.from_settings(
            Settings(
                reflection_frequency="low",
                reflection_user_message_interval=6,
                reflection_min_interval_seconds=120,
            )
        )
        high = ReflectionScheduler.from_settings(
            Settings(
                reflection_frequency="high",
                reflection_user_message_interval=6,
                reflection_min_interval_seconds=120,
            )
        )

        self.assertEqual(low.effective_user_message_interval(), 12)
        self.assertEqual(low.effective_min_interval_seconds(), 240)
        self.assertEqual(high.effective_user_message_interval(), 3)
        self.assertEqual(high.effective_min_interval_seconds(), 60)

    def test_sensitivity_controls_keyword_triggers(self) -> None:
        messages = [
            ChatMessage(role="user", content="hello"),
            ChatMessage(role="assistant", content="hi"),
            ChatMessage(role="user", content="I felt safe after that repair."),
        ]
        conservative = ReflectionScheduler.from_settings(
            Settings(
                reflection_sensitivity="conservative",
                reflection_min_interval_seconds=0,
            )
        )
        responsive = ReflectionScheduler.from_settings(
            Settings(
                reflection_sensitivity="responsive",
                reflection_min_interval_seconds=0,
            )
        )

        conservative_decision = conservative.evaluate(
            messages, now=100, last_started_at=0
        )
        responsive_decision = responsive.evaluate(messages, now=100, last_started_at=0)

        self.assertFalse(conservative_decision.should_schedule)
        self.assertTrue(responsive_decision.should_schedule)
        self.assertIn("repair", responsive_decision.matched_keywords)

    def test_explicit_remember_can_trigger_before_gradual_minimum(self) -> None:
        scheduler = ReflectionScheduler.from_settings(
            Settings(
                reflection_min_interval_seconds=0,
                reflection_min_user_messages=3,
            )
        )

        decision = scheduler.evaluate(
            [ChatMessage(role="user", content="Please remember this boundary.")],
            now=100,
            last_started_at=0,
        )

        self.assertTrue(decision.should_schedule)
        self.assertEqual(decision.user_message_count, 1)
        self.assertIn("boundary", decision.matched_keywords)


if __name__ == "__main__":
    unittest.main()
