"""Tests for Moment Capture visual prompt compilation."""

from app.schemas.character_blueprint import (
    CharacterBlueprint,
    CharacterIdentity,
    PersonalityProfile,
)
from app.schemas.relationship_state import RelationshipState
from app.schemas.visual_identity import VisualIdentityProfile, VisualTrait
from app.services.visual_prompt_compiler import VisualPromptCompiler


def _blueprint(character_id: str = "mira", name: str = "Mira") -> CharacterBlueprint:
    return CharacterBlueprint(
        character_id=character_id,
        identity=CharacterIdentity(
            display_name=name,
            pronouns="she/her",
            species_or_type="moon elf",
            creator_notes="PRIVATE CREATOR NOTE: never leak this",
        ),
        relationship=RelationshipState(
            character_id=character_id,
            relationship_dynamic="warm teasing romance",
            user_desired_experience="private note should not appear",
            affection_level=0.72,
            trust_level=0.66,
        ),
        personality=PersonalityProfile(core_traits=["playful", "devoted"]),
        visual_identity=VisualIdentityProfile(
            identity_anchors=["silver hair", "violet eyes", "crescent moon cheek mark"],
            evolving_traits=[
                VisualTrait(name="hair style", value="long braid with pearl pins")
            ],
            scene_mutable_traits=["wearing a cream sweater"],
            rejected_traits=["blue eyes", "short red hair"],
            current_appearance="soft athletic adult build and gentle confident smile",
        ),
        metadata={"raw_secret": "CharacterBlueprint JSON must not leak"},
    )


def test_identity_anchors_positive_and_rejected_only_negative() -> None:
    bundle = VisualPromptCompiler().compile_bundle(
        _blueprint(),
        scene_state={"setting": "rainy balcony", "mood": "tender"},
        user_capture_instruction="Capture us sharing a quiet romantic look.",
    )

    assert "silver hair" in bundle.positive_prompt
    assert "violet eyes" in bundle.positive_prompt
    assert "crescent moon cheek mark" in bundle.positive_prompt
    assert "blue eyes" not in bundle.positive_prompt
    assert "short red hair" not in bundle.positive_prompt
    assert "blue eyes" in bundle.negative_prompt
    assert bundle.metadata["rejected_traits_excluded"] == [
        "blue eyes",
        "short red hair",
    ]


def test_scene_mutable_traits_can_change_without_affecting_identity_anchors() -> None:
    compiler = VisualPromptCompiler()
    character = _blueprint()
    first = compiler.compile_bundle(
        character,
        scene_state={"outfit": "black dress"},
        user_capture_instruction="portrait",
    )
    second = compiler.compile_bundle(
        character,
        scene_state={"outfit": "silver armor"},
        user_capture_instruction="portrait",
    )

    assert (
        first.metadata["identity_anchors_used"]
        == second.metadata["identity_anchors_used"]
    )
    assert "black dress" in first.positive_prompt
    assert "silver armor" in second.positive_prompt


def test_long_fields_are_bounded_and_private_raw_json_excluded() -> None:
    long_text = "ornate detail " * 400
    bundle = VisualPromptCompiler().compile_bundle(
        _blueprint(),
        scene_state={"setting": long_text, "wrong_appearance": ["green skin"]},
        user_capture_instruction=long_text,
    )

    assert len(bundle.positive_prompt) <= 2400
    assert len(bundle.negative_prompt) <= 1200
    assert "PRIVATE CREATOR NOTE" not in bundle.positive_prompt
    assert "private note should not appear" not in bundle.positive_prompt
    assert "raw_secret" not in bundle.positive_prompt
    assert "CharacterBlueprint" not in bundle.positive_prompt
    assert "green skin" not in bundle.positive_prompt
    assert "green skin" in bundle.negative_prompt


def test_adult_baseline_and_default_user_face_negative_are_present() -> None:
    bundle = VisualPromptCompiler().compile_bundle(
        _blueprint(),
        scene_state={},
        user_capture_instruction="solo portrait",
    )

    assert "clearly adult" in bundle.positive_prompt
    assert "underage presentation" in bundle.negative_prompt
    assert "childlike" in bundle.negative_prompt
    assert "user face visible" in bundle.negative_prompt


def test_prompt_hash_is_stable_for_equivalent_inputs() -> None:
    compiler = VisualPromptCompiler()
    kwargs = {
        "scene_state": {"setting": "library", "mood": "soft"},
        "user_capture_instruction": "Capture her reading beside candlelight.",
    }
    first = compiler.compile_bundle(_blueprint(), **kwargs)
    second = compiler.compile_bundle(_blueprint(), **kwargs)

    assert first.metadata["prompt_hash"] == second.metadata["prompt_hash"]


def test_different_characters_produce_differentiated_bundles() -> None:
    mira = _blueprint("mira", "Mira")
    nyx = _blueprint("nyx", "Nyx").model_copy(
        update={
            "identity": CharacterIdentity(
                display_name="Nyx", pronouns="she/her", species_or_type="dragon knight"
            ),
            "visual_identity": VisualIdentityProfile(
                identity_anchors=[
                    "obsidian horns",
                    "gold eyes",
                    "crimson scale tattoos",
                ],
                current_appearance="tall muscular adult warrior silhouette",
                rejected_traits=["silver hair"],
            ),
        }
    )
    compiler = VisualPromptCompiler()
    a = compiler.compile_bundle(
        mira, scene_state={}, user_capture_instruction="portrait"
    )
    b = compiler.compile_bundle(
        nyx, scene_state={}, user_capture_instruction="portrait"
    )

    assert "silver hair" in a.positive_prompt
    assert "obsidian horns" in b.positive_prompt
    assert a.metadata["character_id"] == "mira"
    assert b.metadata["character_id"] == "nyx"
    assert a.metadata["prompt_hash"] != b.metadata["prompt_hash"]
