"""Visual consistency eval harness v1 for Moment Capture.

These tests are intentionally contract-level and deterministic: they compare
prompt bundles, feedback state, visual memory metadata, and 8GB queue behavior
without invoking image similarity models or external image services. Assertion
messages include a small structured payload so Grok can compare Run A vs Run B
failures by contract name.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from typing import Any

from app.models.image import ImageGenerateRequest, ImageJobStatus, ImageQualityPreset
from app.schemas.character_blueprint import CharacterBlueprint, CharacterIdentity
from app.schemas.moment_capture import (
    MomentCaptureRequest,
    SceneState,
    VisualChangeCanonStatus,
    VisualFeedbackAction,
)
from app.schemas.relationship_state import RelationshipPhase
from app.schemas.visual_identity import VisualIdentityProfile, VisualTrait
from app.services.character_service import CharacterNotFoundError
from app.services.moment_capture_service import MomentCaptureService
from app.services.visual_prompt_compiler import VisualPromptCompiler

from test_image_generation_service import FakeAdapter, FakeCoordinator, make_service
from test_moment_capture_service import FakeMemoryManager, FakeReflectionManager


@dataclass(frozen=True)
class VisualEvalResult:
    """Readable contract result emitted in assertion failures."""

    contract: str
    passed: bool
    details: dict[str, Any]


def _fail(contract: str, **details: Any) -> None:
    result = VisualEvalResult(contract=contract, passed=False, details=details)
    raise AssertionError(json.dumps(asdict(result), sort_keys=True, indent=2))


def _assert_contains(contract: str, haystack: str, needle: str) -> None:
    if needle.casefold() not in haystack.casefold():
        _fail(contract, expected=needle, prompt=haystack)


def _assert_not_contains(contract: str, haystack: str, needle: str) -> None:
    if needle.casefold() in haystack.casefold():
        _fail(contract, forbidden=needle, prompt=haystack)


class MultiCharacterService:
    """Small in-memory CharacterService test double with real update semantics."""

    def __init__(self, *characters: CharacterBlueprint) -> None:
        self.characters = {character.character_id: character for character in characters}

    def load_by_id(self, character_id: str) -> CharacterBlueprint:
        try:
            return self.characters[character_id]
        except KeyError as exc:
            raise CharacterNotFoundError(character_id) from exc

    def get_visual_identity(self, character_id: str) -> VisualIdentityProfile:
        return self.load_by_id(character_id).visual_identity

    def update_visual_identity(
        self, character_id: str, patch: dict[str, object]
    ) -> VisualIdentityProfile:
        character = self.load_by_id(character_id)
        visual = character.visual_identity
        if "evolving_trait" in patch and isinstance(patch["evolving_trait"], dict):
            trait = patch["evolving_trait"]
            visual = visual.with_evolving_trait(
                str(trait["name"]),
                str(trait["value"]),
                provenance=str(trait["provenance"]),
            )
        if "rejected_traits" in patch:
            visual = visual.model_copy(update={"rejected_traits": patch["rejected_traits"]})
        self.characters[character_id] = character.model_copy(
            update={"visual_identity": visual}
        )
        return visual


def _aria() -> CharacterBlueprint:
    return CharacterBlueprint(
        character_id="aria",
        identity=CharacterIdentity(display_name="Aria", pronouns="she/her"),
        visual_identity=VisualIdentityProfile(
            identity_anchors=[
                "amber eyes",
                "warm brown skin",
                "heart-shaped face",
                "small star scar under left eye",
            ],
            current_appearance="long black-violet hair and a crescent moon pendant",
            evolving_traits=[
                VisualTrait(
                    name="hair",
                    value="long black-violet hair",
                    provenance="creator_seed",
                )
            ],
            scene_mutable_traits=["outfit may change by scene"],
            rejected_traits=["blue eyes", "pale skin"],
        ),
    )


def _mira() -> CharacterBlueprint:
    return CharacterBlueprint(
        character_id="mira",
        identity=CharacterIdentity(display_name="Mira", pronouns="she/her"),
        visual_identity=VisualIdentityProfile(
            identity_anchors=[
                "violet eyes",
                "deep umber skin",
                "angular face",
                "gold cheek freckles",
            ],
            current_appearance="short silver curls and a red glass choker",
            evolving_traits=[
                VisualTrait(name="hair", value="short silver curls", provenance="seed")
            ],
            rejected_traits=["amber eyes", "moon pendant"],
        ),
    )


def _capture_request(character: CharacterBlueprint, *, outfit: str) -> MomentCaptureRequest:
    visual_identity = character.visual_identity
    return MomentCaptureRequest(
        character_id=character.character_id,
        conversation_id="conv-visual-eval",
        session_id="session-visual-eval",
        source_message_id="msg-visual-eval",
        source_turn_index=5,
        scene_state=SceneState(
            location="moonlit balcony",
            emotional_tone="tender and relieved",
            pose="looking back over her shoulder",
            outfit=outfit,
            wrong_appearance=["blue eyes"],
        ),
        relationship_phase_snapshot=RelationshipPhase.newly_met,
        visual_identity_snapshot=visual_identity,
        visual_identity_version=visual_identity.schema_version,
        visual_identity_updated_at=visual_identity.updated_at,
        prompt_hash="visual-eval-request-hash",
        quality_preset=ImageQualityPreset.preview_8gb,
        metadata={"capture_intent": "capture this continuity eval moment"},
    )


def test_visual_eval_prompt_identity_scene_and_distinct_character_contracts() -> None:
    compiler = VisualPromptCompiler()
    rainy = compiler.compile(
        character=_aria(),
        scene_state={"location": "rainy balcony", "outfit": "emerald raincoat"},
        capture_intent="capture a rainy reunion",
    )
    desert = compiler.compile(
        character=_aria(),
        scene_state={"location": "desert market", "outfit": "linen travel cloak"},
        capture_intent="capture a sunny marketplace walk",
    )
    mira = compiler.compile(
        character=_mira(),
        scene_state={"location": "rainy balcony", "outfit": "emerald raincoat"},
        capture_intent="capture a rainy reunion",
    )

    for anchor in ("amber eyes", "warm brown skin", "heart-shaped face"):
        _assert_contains("identity_anchor_inclusion", rainy.positive_prompt, anchor)
        _assert_contains("same_character_different_scene", desert.positive_prompt, anchor)
        if anchor not in rainy.metadata["identity_anchors_used"]:
            _fail(
                "identity_anchor_metadata",
                expected_anchor=anchor,
                metadata=rainy.metadata,
            )

    for rejected in ("blue eyes", "pale skin"):
        _assert_not_contains(
            "rejected_trait_exclusion_from_positive", rainy.positive_prompt, rejected
        )
        _assert_contains("rejected_trait_negative_prompt", rainy.negative_prompt, rejected)

    _assert_contains("scene_trait_mutability", rainy.positive_prompt, "emerald raincoat")
    _assert_contains("scene_trait_mutability", desert.positive_prompt, "linen travel cloak")
    _assert_not_contains("scene_trait_mutability", desert.positive_prompt, "emerald raincoat")
    if rainy.metadata["identity_anchors_used"] != desert.metadata["identity_anchors_used"]:
        _fail(
            "scene_changes_do_not_mutate_identity_anchors",
            rainy=rainy.metadata["identity_anchors_used"],
            desert=desert.metadata["identity_anchors_used"],
        )

    _assert_contains("distinct_character_output", mira.positive_prompt, "violet eyes")
    _assert_contains("distinct_character_output", mira.positive_prompt, "short silver curls")
    _assert_not_contains("distinct_character_output", mira.positive_prompt, "amber eyes")
    if rainy.metadata["prompt_hash"] == mira.metadata["prompt_hash"]:
        _fail(
            "distinct_character_prompt_hash",
            aria_hash=rainy.metadata["prompt_hash"],
            mira_hash=mira.metadata["prompt_hash"],
        )


def test_visual_eval_feedback_corrections_canon_outfit_and_memory_scope(tmp_path) -> None:
    character_service = MultiCharacterService(_aria(), _mira())
    memory = FakeMemoryManager()
    service = MomentCaptureService(
        character_service=character_service,  # type: ignore[arg-type]
        image_service=make_service(tmp_path, FakeCoordinator(), FakeAdapter()),
        records_path=tmp_path / "moment_captures.json",
        memory_manager=memory,  # type: ignore[arg-type]
        reflection_manager=FakeReflectionManager(),  # type: ignore[arg-type]
    )
    record = asyncio.run(service.capture(_capture_request(_aria(), outfit="red silk coat"))).record

    from app.services.moment_capture_service import (
        VisualChangeReviewRequest,
        VisualFeedbackRequest,
    )

    wrong = service.submit_feedback(
        record.capture_id,
        VisualFeedbackRequest(
            character_id="aria",
            action=VisualFeedbackAction.wrong_appearance,
            trait_name="rejected_trait",
            trait_value="blue eyes",
            note="The eyes drifted blue; keep Aria amber-eyed.",
        ),
    )
    if wrong.visual_change_event is None:
        _fail("wrong_appearance_creates_reviewable_correction")
    service.approve_visual_change(
        wrong.visual_change_event.event_id,
        VisualChangeReviewRequest(character_id="aria"),
    )
    corrected = VisualPromptCompiler().compile(
        character=character_service.load_by_id("aria")
    )
    _assert_not_contains("wrong_appearance_positive_exclusion", corrected.positive_prompt, "blue eyes")
    _assert_contains("wrong_appearance_negative_inclusion", corrected.negative_prompt, "blue eyes")

    canon = service.submit_feedback(
        record.capture_id,
        VisualFeedbackRequest(
            character_id="aria",
            action=VisualFeedbackAction.make_canon,
            trait_name="hair",
            trait_value="shoulder-length black-violet hair",
        ),
    )
    if canon.visual_change_event is None:
        _fail("make_canon_pending_event_created")
    if canon.visual_change_event.canon_status != VisualChangeCanonStatus.proposed:
        _fail("make_canon_pending_state", event=canon.visual_change_event.model_dump())
    _assert_not_contains(
        "pending_make_canon_does_not_update_identity",
        VisualPromptCompiler().compile(character=character_service.load_by_id("aria")).positive_prompt,
        "shoulder-length black-violet hair",
    )
    service.approve_visual_change(
        canon.visual_change_event.event_id,
        VisualChangeReviewRequest(character_id="aria"),
    )
    _assert_contains(
        "approved_make_canon_updates_identity",
        VisualPromptCompiler().compile(character=character_service.load_by_id("aria")).positive_prompt,
        "shoulder-length black-violet hair",
    )

    outfit = service.submit_feedback(
        record.capture_id,
        VisualFeedbackRequest(
            character_id="aria",
            action=VisualFeedbackAction.use_outfit_again,
            trait_name="outfit",
            trait_value="red silk coat",
        ),
    )
    if outfit.visual_change_event is None:
        _fail("outfit_reuse_creates_reviewable_event")
    service.approve_visual_change(
        outfit.visual_change_event.event_id,
        VisualChangeReviewRequest(character_id="aria"),
    )
    outfit_prompt = VisualPromptCompiler().compile(character=character_service.load_by_id("aria"))
    _assert_contains("outfit_reuse_preserves_identity_anchor", outfit_prompt.positive_prompt, "amber eyes")
    _assert_contains("outfit_reuse_preserves_identity_anchor", outfit_prompt.positive_prompt, "warm brown skin")
    _assert_contains("outfit_reuse_adds_outfit_without_overwrite", outfit_prompt.positive_prompt, "red silk coat")

    memory_response = service.submit_feedback(
        record.capture_id,
        VisualFeedbackRequest(
            character_id="aria",
            action=VisualFeedbackAction.looks_right,
            note="Favorite continuity image: moon pendant stayed right.",
        ),
    )
    if not memory_response.record.visual_memory_artifacts:
        _fail("visual_memory_artifact_created")
    if not memory.search_memories("moon pendant", character_id="aria"):
        _fail("character_scoped_visual_memory_visible_to_owner", memories=memory.memories)
    if memory.search_memories("moon pendant", character_id="mira"):
        _fail("character_scoped_visual_memory_leaked", memories=memory.memories)


def test_visual_eval_8gb_queue_under_pressure_is_non_blocking_and_graceful(tmp_path) -> None:
    async def run_test() -> None:
        coordinator = FakeCoordinator(free_vram_mb=1100)
        service = make_service(tmp_path, coordinator, FakeAdapter())
        submissions = []
        for index in range(3):
            submissions.append(
                await service.submit(
                    ImageGenerateRequest(
                        prompt=f"pressure eval portrait {index}",
                        quality_preset=ImageQualityPreset.high_8gb,
                        source="moment_capture",
                    )
                )
            )
        await asyncio.sleep(0.03)

        first = service.get_job(submissions[0].job_id)
        if first.status != ImageJobStatus.waiting_for_resources:
            _fail("8gb_pressure_first_job_waits_gracefully", job=first.model_dump(mode="json"))
        if first.pressure != "critical" or not first.warning:
            _fail("8gb_pressure_warning", job=first.model_dump(mode="json"))
        queued_count = sum(
            service.get_job(job.job_id).status == ImageJobStatus.queued
            for job in submissions[1:]
        )
        if queued_count != 2:
            _fail(
                "8gb_pressure_load_remains_queued_non_blocking",
                jobs=[service.get_job(job.job_id).model_dump(mode="json") for job in submissions],
            )

        for job in submissions:
            cancelled = await service.cancel(job.job_id)
            if cancelled.status != ImageJobStatus.cancelled:
                _fail("8gb_pressure_cancellation", job=cancelled.model_dump(mode="json"))

    asyncio.run(run_test())
