"""Compatibility import for the canonical emotion/prosody engine."""

from app.services.emotion_engine import (  # noqa: F401
    EmotionEngine,
    EmotionResult,
    OrpheusTagStreamFilter,
    emotion_engine,
    strip_orpheus_tags,
)
