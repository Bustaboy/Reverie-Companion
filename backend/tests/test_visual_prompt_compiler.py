"""VisualPromptCompiler coverage for Moment Capture prompt bundles."""

from __future__ import annotations

from app.schemas.character_blueprint import CharacterBlueprint, CharacterIdentity
from app.schemas.visual_identity import VisualIdentityProfile, VisualTrait
from app.services.visual_prompt_compiler import VisualPromptCompiler, VisualPromptBundle


def _character(
    character_id: str, name: str, anchors: list[str], rejected: list[str]
) -> CharacterBlueprint:
    return CharacterBlueprint(
        character_id=character_id,
        identity=CharacterIdentity(display_name=name, pronouns="she/her"),
        visual_identity=VisualIdentityProfile(
            identity_anchors=anchors,
            current_appearance=f"{name} wears a signature keepsake",
            evolving_traits=[
                VisualTrait(name="hair", value=f"{name} canon hair", provenance="test")
            ],
            scene_mutable_traits=["current outfit", "soft expression"],
            rejected_traits=rejected,
        ),
    )


def test_visual_prompt_bundle_is_typed_and_identity_anchors_are_positive() -> None:
    character = _character(
        "aria", "Aria", ["amber eyes", "warm brown skin", "same face"], ["blue eyes"]
    )

    bundle = VisualPromptCompiler().compile(
        character=character, capture_intent="capture a tender portrait"
    )

    assert isinstance(bundle, VisualPromptBundle)
    assert "amber eyes" in bundle.positive_prompt
    assert "warm brown skin" in bundle.positive_prompt
    assert bundle.metadata["character_id"] == "aria"
    assert bundle.metadata["identity_anchors_used"] == [
        "amber eyes",
        "warm brown skin",
        "same face",
    ]


def test_rejected_traits_only_appear_in_negative_prompt_and_metadata() -> None:
    character = _character("aria", "Aria", ["amber eyes"], ["blue eyes", "silver hair"])

    bundle = VisualPromptCompiler().compile(
        character=character, capture_intent="capture her smile"
    )

    assert "blue eyes" not in bundle.positive_prompt
    assert "silver hair" not in bundle.positive_prompt
    assert "blue eyes" in bundle.negative_prompt
    assert "silver hair" in bundle.negative_prompt
    assert bundle.metadata["rejected_traits_excluded"] == ["blue eyes", "silver hair"]
    assert bundle.metadata["wrong_appearance_excluded"] == []


def test_wrong_appearance_metadata_is_negative_only() -> None:
    character = _character("aria", "Aria", ["amber eyes"], [])

    bundle = VisualPromptCompiler().compile(
        character=character,
        scene_state={"wrong_appearance": ["green eyes", "short bob"]},
        capture_intent="capture her smile",
    )

    assert "green eyes" not in bundle.positive_prompt
    assert "short bob" not in bundle.positive_prompt
    assert "green eyes" in bundle.negative_prompt
    assert "short bob" in bundle.negative_prompt
    assert bundle.metadata["wrong_appearance_excluded"] == ["green eyes", "short bob"]
    assert " wrong_appearance_excluded " not in bundle.metadata


def test_scene_mutable_traits_can_change_without_affecting_identity_anchors() -> None:
    character = _character(
        "aria", "Aria", ["amber eyes", "velvet dress outfit", "same face"], []
    )
    compiler = VisualPromptCompiler()

    first = compiler.compile(
        character=character, scene_state={"outfit": "red dress", "pose": "standing"}
    )
    second = compiler.compile(
        character=character, scene_state={"outfit": "black coat", "pose": "sitting"}
    )

    assert first.metadata["identity_anchors_used"] == ["amber eyes", "same face"]
    assert second.metadata["identity_anchors_used"] == ["amber eyes", "same face"]
    assert "red dress" in first.positive_prompt
    assert "black coat" in second.positive_prompt


def test_long_fields_are_bounded() -> None:
    long_text = "ornate detail " * 80
    character = _character("aria", "Aria", [long_text, "amber eyes"], [long_text])

    bundle = VisualPromptCompiler().compile(
        character=character,
        scene_state={"location": long_text, "wrong_appearance": [long_text]},
        capture_intent=long_text,
    )

    assert len(bundle.positive_prompt) <= VisualPromptCompiler.MAX_POSITIVE_CHARS
    assert len(bundle.negative_prompt) <= VisualPromptCompiler.MAX_NEGATIVE_CHARS
    assert "…" in bundle.positive_prompt or "…" in bundle.negative_prompt


def test_private_notes_and_raw_blueprint_json_are_not_included() -> None:
    character = _character("aria", "Aria", ["amber eyes"], [])
    character.identity.creator_notes = "private forbidden note"
    character.metadata["raw_secret"] = {"CharacterBlueprint": "raw json leak"}

    bundle = VisualPromptCompiler().compile(
        character=character, capture_intent="capture her"
    )
    combined = bundle.positive_prompt + bundle.negative_prompt + str(bundle.metadata)

    assert "private forbidden note" not in combined
    assert "raw json leak" not in combined
    assert "CharacterBlueprint" not in combined


def test_adult_baseline_is_always_present() -> None:
    bundle = VisualPromptCompiler().compile(
        visual_identity=VisualIdentityProfile(), capture_intent="capture this moment"
    )

    assert "clearly adult" in bundle.positive_prompt
    assert "underage presentation" in bundle.negative_prompt
    assert "childlike proportions" in bundle.negative_prompt


def test_prompt_hash_is_stable_for_equivalent_inputs() -> None:
    character = _character("aria", "Aria", ["amber eyes"], ["blue eyes"])
    compiler = VisualPromptCompiler()

    first = compiler.compile(
        character=character,
        scene_state={"location": "moon garden"},
        capture_intent="capture her",
    )
    second = compiler.compile(
        character=character,
        scene_state={"location": "moon garden"},
        capture_intent="capture her",
    )

    assert first.metadata["prompt_hash"] == second.metadata["prompt_hash"]
    assert len(first.metadata["prompt_hash"]) == 16


def test_different_characters_produce_differentiated_bundles() -> None:
    aria = _character("aria", "Aria", ["amber eyes", "warm brown skin"], ["blue eyes"])
    lyra = _character(
        "lyra",
        "Lyra",
        ["emerald eyes", "fox ears", "copper tail"],
        ["human-only silhouette"],
    )
    compiler = VisualPromptCompiler()

    aria_bundle = compiler.compile(
        character=aria, capture_intent="capture her portrait"
    )
    lyra_bundle = compiler.compile(
        character=lyra, capture_intent="capture her portrait"
    )

    assert "amber eyes" in aria_bundle.positive_prompt
    assert "fox ears" in lyra_bundle.positive_prompt
    assert aria_bundle.metadata["character_id"] == "aria"
    assert lyra_bundle.metadata["character_id"] == "lyra"
    assert aria_bundle.metadata["prompt_hash"] != lyra_bundle.metadata["prompt_hash"]
