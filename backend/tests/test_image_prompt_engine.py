"""Tests for deterministic image prompt enrichment."""

from app.services.image_prompt_engine import ImagePromptEngine


def test_prompt_engine_uses_character_scene_memory_and_style_context() -> None:
    engine = ImagePromptEngine()

    result = engine.build(
        prompt="portrait at the cafe",
        context={
            "character": {
                "name": "Mira",
                "appearance": "silver hair, violet eyes, soft athletic build",
                "clothing": "oversized cream sweater",
                "personality": "warm, teasing, attentive",
                "style_tags": ["soft anime lighting"],
            },
            "visual_state": {
                "background": "rainy neon cafe",
                "pose": "leaning over the table",
                "expression": "fond smile",
            },
            "memory_tags": ["favorite rainy dates", "likes quiet corners"],
            "reflection_themes": ["becoming more openly affectionate"],
            "growth_cues": ["trust is deepening"],
            "mood_settings": {
                "baseline_expressiveness": 1.4,
                "emotional_sensitivity": 1.3,
            },
        },
    )

    assert "Mira as the main character" in result.prompt
    assert "silver hair, violet eyes" in result.prompt
    assert "rainy neon cafe" in result.prompt
    assert "favorite rainy dates" in result.prompt
    assert "becoming more openly affectionate" in result.prompt
    assert "preserve canonical hair" in result.prompt
    assert "same character identity across generations" in result.prompt
    assert "low quality" in result.negative_prompt


def test_prompt_engine_adds_user_face_avoidance_for_intimate_user_scenes() -> None:
    engine = ImagePromptEngine()

    result = engine.build(
        prompt="intimate bedroom embrace with us together",
        context={
            "participants": ["character", "user"],
            "scene_tags": ["nsfw", "intimate"],
            "recent_messages": [
                {"role": "user", "content": "Pull me close on the bed."},
            ],
        },
        negative_prompt="harsh shadows",
    )

    assert "avoid showing the user's face" in result.prompt
    assert "over-shoulder" in result.prompt
    assert "keep the character's face and emotion readable" in result.prompt
    assert "user face visible" in result.negative_prompt
    assert "harsh shadows" in result.negative_prompt


def test_prompt_engine_does_not_add_user_face_rule_for_solo_character_scene() -> None:
    result = ImagePromptEngine().build(
        prompt="solo character reading in a library",
        context={"scene_tags": ["cozy"], "participants": ["character"]},
    )

    assert "avoid showing the user's face" not in result.prompt
    assert "user face visible" not in result.negative_prompt
