"""Coverage for deterministic Orpheus emotion/prosody tagging."""

from app.models.chat import ChatMessage, GrowthNotification
from app.models.tts import TTSContext
from app.services.emotion_engine import EmotionEngine


def test_emotion_engine_strips_visible_tags_and_injects_tts_tags() -> None:
    engine = EmotionEngine()

    result = engine.analyze_and_tag(
        text="<whisper>I trust you. <moan>Stay close.",
        tts_context=TTSContext(emotion_hint="intimate", intensity=1.4),
        recent_messages=[
            ChatMessage(role="user", content="I want you close; this is intimate.")
        ],
    )

    assert result.visible_text == "I trust you. Stay close."
    assert "<" not in result.visible_text
    assert result.is_intimate is True
    assert result.tags
    assert result.tts_text.startswith("<")


def test_emotion_engine_uses_growth_and_reflection_cues_without_llm_calls() -> None:
    result = EmotionEngine().analyze_and_tag(
        text="I am here with you, softly and steadily.",
        tts_context=TTSContext(emotion_hint="warm", intensity=1.1),
        recent_messages=[
            ChatMessage(role="user", content="I feel anxious and need reassurance.")
        ],
        memory_context="User feels safer with gentle reassurance and trust.",
        reflection_entries=[
            {
                "character_summary": "Trust and comfort have become important.",
                "themes": ["trust", "comfort"],
                "insights": [{"summary": "Use a soft voice when reassurance matters."}],
            }
        ],
        growth_notification=GrowthNotification(
            id="growth_1",
            journal_entry_id="journal_1",
            created_at="2026-06-11T00:00:00Z",
            message="Reverie seems steadier in your trust.",
            theme="trust",
        ),
    )

    assert result.scene in {"tender", "high_emotion"}
    assert result.intensity >= 1.1
    assert "growth_reflection" in result.cues
    assert any(tag in result.tags for tag in {"sigh", "whisper", "gasp"})


def test_emotion_engine_uses_per_character_mood_scene_tags() -> None:
    from app.models.tts import TTSMoodSettings

    result = EmotionEngine().analyze_and_tag(
        text="Stay with me after this kiss.",
        tts_context=TTSContext(
            emotion_hint="warm",
            intensity=0.9,
            mood_settings=TTSMoodSettings(
                baseline_expressiveness=1.2,
                emotional_sensitivity=1.5,
                nsfw_intensity=1.8,
            ),
            scene_tags=["aftercare", "intimate"],
        ),
        recent_messages=[
            ChatMessage(role="user", content="I need you close and safe.")
        ],
    )

    assert result.is_intimate is True
    assert result.intensity > 1.2
    assert "scene:intimate" in result.cues
    assert any(cue.startswith("mood:") for cue in result.cues)
