"""Coverage for the lightweight weighted emotion inference layer."""

from app.core.emotion import EmotionInferenceEngine
from app.models.chat import ChatMessage, GrowthNotification


def test_weighted_engine_falls_back_to_neutral_when_confidence_is_low() -> None:
    result = EmotionInferenceEngine().infer_visual_state(
        messages=[ChatMessage(role="user", content="Can we talk for a bit?")],
        assistant_response="Of course. I'm here with you.",
    )

    assert result.expression == "neutral"
    assert result.confidence == 0.0


def test_weighted_engine_uses_memory_reflection_and_growth_cues() -> None:
    result = EmotionInferenceEngine().infer_visual_state(
        messages=[ChatMessage(role="user", content="I feel anxious and need reassurance.")],
        assistant_response="I remember that gentle comfort helps you feel safe.",
        memory_context="User prefers gentle reassurance and safety when anxious.",
        reflection_entries=[
            {
                "entry_id": "journal_1",
                "status": "active",
                "character_summary": "Trust and reassurance have become meaningful.",
                "themes": ["trust", "comfort"],
                "insights": [{"summary": "Offer comfort before problem solving."}],
                "confidence": 0.9,
            }
        ],
        growth_notification=GrowthNotification(
            id="growth_1",
            journal_entry_id="journal_1",
            created_at="2026-06-11T00:00:00Z",
            message="Reverie seems steadier in your trust.",
            why="A private reflection noticed reassurance helps you feel safe.",
            theme="trust",
        ),
    )

    assert result.expression in {"happy", "concerned", "thinking"}
    assert result.growth_cue == "relationship_trust"
    assert result.decay_ms == 45_000
    assert result.confidence >= 0.32
