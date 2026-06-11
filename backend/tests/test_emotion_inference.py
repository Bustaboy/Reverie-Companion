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
        self.assertIn("strong_memory_tags", state.sources)
        self.assertIn("memory_tags", state.sources)
        self.assertGreaterEqual(state.intensity, 0.55)

    def test_assistant_tone_can_drive_expression_without_stronger_signals(
        self,
    ) -> None:
        engine = EmotionInferenceEngine()

        state = engine.infer_visual_state(
            ChatRequest(
                stream=False,
                messages=[ChatMessage(role="user", content="Show me your reaction.")],
            ),
            assistant_text="I smirk with playful teasing warmth.",
        )

        self.assertEqual(state.expression, "teasing")
        self.assertEqual(state.pose, "leaning")
        self.assertEqual(state.sources, ["assistant_response_tone"])

    def test_memory_tags_drive_reactivity_when_latest_message_is_neutral(
        self,
    ) -> None:
        engine = EmotionInferenceEngine()

        state = engine.infer_visual_state(
            ChatRequest(
                stream=False,
                messages=[
                    ChatMessage(role="user", content="Can we pick this up again?")
                ],
            ),
            memory_context="strong trust promise reassurance slow-burn",
        )

        self.assertEqual(state.expression, "tender")
        self.assertEqual(state.pose, "close")
        self.assertEqual(state.sources, ["strong_memory_tags", "memory_tags"])
        self.assertGreaterEqual(state.confidence, 0.6)

    def test_growth_priority_boost_is_bounded_by_weighted_chat_tone(self) -> None:
        engine = EmotionInferenceEngine()
        growth_notification = GrowthNotification(
            id="growth_confidence",
            journal_entry_id="journal_confidence",
            created_at="2026-06-11T00:00:00Z",
            message="Reverie seems more confident lately.",
            why="A reflection noticed her steadier self-trust.",
            theme="confidence",
        )

        state = engine.infer_visual_state(
            ChatRequest(
                stream=False,
                messages=[
                    ChatMessage(role="user", content="I am angry and frustrated.")
                ],
            ),
            assistant_text="I answer with a hurt, frustrated edge.",
            growth_notification=growth_notification,
        )

        self.assertEqual(state.expression, "angry")
        self.assertEqual(state.pose, "guarded")
        self.assertEqual(state.growth_cue, "confidence")
        self.assertIn("growth_cue", state.sources)
        self.assertIn("latest_message_tone", state.sources)
        self.assertIn("assistant_response_tone", state.sources)

    def test_strong_memory_tags_beat_conflicting_latest_message(self) -> None:
        engine = EmotionInferenceEngine()

        state = engine.infer_visual_state(
            ChatRequest(
                stream=False,
                messages=[
                    ChatMessage(
                        role="user",
                        content="I am angry right now, but remember what mattered.",
                    )
                ],
            ),
            assistant_text="I keep my voice calm.",
            memory_context="protected trust promise reassurance",
        )

        self.assertEqual(state.expression, "tender")
        self.assertEqual(state.pose, "close")
        self.assertEqual(state.sources, ["strong_memory_tags", "memory_tags"])

    def test_reflection_themes_shape_visuals_without_memory(self) -> None:
        engine = EmotionInferenceEngine()

        state = engine.infer_visual_state(
            ChatRequest(
                stream=False,
                messages=[ChatMessage(role="user", content="What changed lately?")],
            ),
            reflection_entries=[
                {
                    "themes": ["confidence"],
                    "character_summary": "I am steadier and more assured.",
                    "insights": [
                        {
                            "summary": "She learned to answer with quiet confidence."
                        }
                    ],
                }
            ],
        )

        self.assertEqual(state.expression, "confident")
        self.assertEqual(state.pose, "assertive")
        self.assertEqual(state.sources, ["reflection_themes"])

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
