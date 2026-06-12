"""Tests for deterministic Orpheus emotion/prosody tagging."""

from app.models.chat import ChatMessage, GrowthNotification
from app.models.tts import TTSContext
from app.services.emotion_engine import EmotionEngine, OrpheusTagStreamFilter, strip_orpheus_tags


def test_emotion_engine_strips_visible_tags_and_boosts_intimate_tts() -> None:
    result = EmotionEngine().analyze(
        text="<whisper> I need you close. Please kiss me until I gasp.",
        context=TTSContext(character_id="tara", intensity=1.2),
        recent_messages=[ChatMessage(role="user", content="This is intimate and I want you closer.")],
        reflection_entries=[{"themes": ["trust", "intimacy"], "character_summary": "Trust feels safe."}],
        growth_notification=GrowthNotification(
            id="growth_voice",
            journal_entry_id="journal_voice",
            created_at="2026-06-12T00:00:00Z",
            message="Reverie feels safer with intimate trust.",
            theme="trust",
        ),
    )

    assert "<whisper>" not in result.clean_text
    assert result.metadata.intimate_scene is True
    assert result.metadata.intensity > 1.2
    assert any(tag in result.tts_text for tag in ("<whisper>", "<gasp>", "<moan>"))


def test_tag_stream_filter_handles_split_tags() -> None:
    tag_filter = OrpheusTagStreamFilter()

    assert tag_filter.filter("<whis") == ""
    assert tag_filter.filter("per> Hello") == "Hello"
    assert tag_filter.flush() == ""


def test_strip_orpheus_tags_removes_known_and_short_unknown_tags() -> None:
    assert strip_orpheus_tags("<moan> Visible <style> text") == "Visible text"
