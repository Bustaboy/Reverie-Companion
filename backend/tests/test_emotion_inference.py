"""Coverage for deterministic VN visual-state inference."""

from __future__ import annotations

import unittest

from app.core.emotion import EmotionInferenceEngine
from app.models.chat import ChatMessage, ChatRequest, GrowthNotification


class EmotionInferenceEngineTests(unittest.TestCase):
    def test_falls_back_to_neutral_without_signals(self) -> None:
        engine = EmotionInferenceEngine()
        state = engine.infer_visual_state(
            ChatRequest(
                stream=False,
                messages=[ChatMessage(role="user", content="Tell me something.")],
            )
        )

        self.assertEqual(state.expression, "neutral")
        self.assertEqual(state.pose, "idle")
        self.assertEqual(state.sources, ["fallback_neutral"])

    def test_recent_growth_and_strong_memory_tags_outweigh_latest_tone(self) -> None:
        engine = EmotionInferenceEngine()
        request = ChatRequest(
            stream=False,
            messages=[
                ChatMessage(
                    role="user",
                    content="I feel nervous and a little sad about this.",
                )
            ],
        )
        growth_notification = GrowthNotification(
            id="growth_confidence",
            journal_entry_id="journal_confidence",
            created_at="2026-06-11T00:00:00Z",
            message="Reverie seems steadier and more confident lately.",
            why="A private reflection noticed trust becoming easier.",
            theme="confidence",
        )

        state = engine.infer_visual_state(
            request,
            assistant_text="I can hold this with a steady voice.",
            memory_context="trust milestone confidence learned reassurance",
            reflection_entries=[
                {
                    "themes": ["trust", "growth"],
                    "character_summary": "I learned to be steadier with reassurance.",
                }
            ],
            growth_notification=growth_notification,
        )

        self.assertEqual(state.expression, "confident")
        self.assertEqual(state.pose, "assertive")
        self.assertEqual(state.growth_cue, "confidence")
        self.assertIn("growth_cue", state.sources)
        self.assertIn("memory_tags", state.sources)

    def test_scene_keywords_select_background_without_assets(self) -> None:
        engine = EmotionInferenceEngine()
        state = engine.infer_visual_state(
            ChatRequest(
                stream=False,
                messages=[
                    ChatMessage(
                        role="user",
                        content="Stay with me in the glowing slime cave.",
                    )
                ],
            ),
            assistant_text="The cave light catches my smile.",
        )

        self.assertEqual(state.background, "slime-cave")


if __name__ == "__main__":
    unittest.main()
