"""Runnable visual consistency eval harness for M5-P08.

These tests are intentionally deterministic and text/metadata based. They give
Grok a compact contract-by-contract signal for comparing Codex Run A vs Run B
without requiring CLIP, GPUs, external image services, or cloud evaluators.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from typing import Callable

import pytest

from app.core.config import Settings
from app.models.image import ImageGenerateRequest, ImageQualityPreset
from app.schemas.character_blueprint import CharacterBlueprint, CharacterIdentity
from app.schemas.moment_capture import (
    MomentCaptureRecord,
    MomentCaptureRequest,
    SceneState,
    VisualChangeCanonStatus,
    VisualChangeReviewRequest,
    VisualFeedbackAction,
    VisualFeedbackRequest,
)
from app.schemas.relationship_state import RelationshipPhase
from app.schemas.visual_identity import VisualIdentityProfile, VisualTrait
from app.services.character_service import CharacterNotFoundError
from app.services.image_generation_service import (
    ImageGenerationError,
    ImageGenerationService,
)
from app.services.moment_capture_service import MomentCaptureService
from app.services.visual_prompt_compiler import VisualPromptBundle, VisualPromptCompiler

from test_image_generation_service import FakeAdapter, FakeCoordinator
from test_moment_capture_service import FakeMemoryManager, FakeReflectionManager


@dataclass(frozen=True)
class VisualEvalResult:
    """Structured per-contract result surfaced in assertion failures."""

    contract: str
    passed: bool
    detail: str
    evidence: dict[str, object]


def _pass(contract: str, detail: str, **evidence: object) -> VisualEvalResult:
    return VisualEvalResult(contract, True, detail, evidence)


def _fail(contract: str, detail: str, **evidence: object) -> VisualEvalResult:
    return VisualEvalResult(contract, False, detail, evidence)


def _assert_eval(result: VisualEvalResult) -> None:
    assert result.passed, asdict(result)


def _character(
    character_id: str,
    name: str,
    anchors: list[str],
    *,
    rejected: list[str] | None = None,
    current: str | None = None,
    evolving: list[VisualTrait] | None = None,
    scene_mutable: list[str] | None = None,
) -> CharacterBlueprint:
    return CharacterBlueprint(
        character_id=character_id,
        identity=CharacterIdentity(display_name=name, pronouns="she/her"),
        visual_identity=VisualIdentityProfile(
            identity_anchors=anchors,
            current_appearance=current or f"{name} keeps her familiar silhouette",
            evolving_traits=evolving or [],
            scene_mutable_traits=scene_mutable or [],
            rejected_traits=rejected or [],
        ),
    )


def _compile(character: CharacterBlueprint, **kwargs: object) -> VisualPromptBundle:
    return VisualPromptCompiler().compile(character=character, **kwargs)


def _contains_all(text: str, values: list[str]) -> bool:
    return all(value in text for value in values)


class EvalCharacterService:
    def __init__(self, characters: list[CharacterBlueprint]) -> None:
        self.characters = {
            character.character_id: character for character in characters
        }

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
            visual = visual.model_copy(
                update={"rejected_traits": patch["rejected_traits"]}
            )
        self.characters[character_id] = character.model_copy(
            update={"visual_identity": visual}
        )
        return visual


def _request(character: CharacterBlueprint) -> MomentCaptureRequest:
    visual = character.visual_identity
    return MomentCaptureRequest(
        character_id=character.character_id,
        conversation_id="conv-eval",
        session_id="session-eval",
        source_message_id="msg-eval",
        source_turn_index=4,
        scene_state=SceneState(
            location="rainy balcony", pose="looking back", emotional_tone="tender"
        ),
        relationship_phase_snapshot=RelationshipPhase.newly_met,
        visual_identity_snapshot=visual,
        visual_identity_version=visual.schema_version,
        visual_identity_updated_at=visual.updated_at,
        prompt_hash="evalseedhash",
        quality_preset=ImageQualityPreset.preview_8gb,
        metadata={"capture_intent": "capture this visual eval moment"},
    )


def _record(request: MomentCaptureRequest, image_job_id: str) -> MomentCaptureRecord:
    return MomentCaptureRecord(
        capture_id=f"cap-{image_job_id}",
        character_id=request.character_id,
        conversation_id=request.conversation_id,
        session_id=request.session_id,
        source_message_id=request.source_message_id,
        source_turn_index=request.source_turn_index,
        scene_state=request.scene_state,
        relationship_phase_snapshot=request.relationship_phase_snapshot,
        visual_identity_version=request.visual_identity_version,
        visual_identity_updated_at=request.visual_identity_updated_at,
        prompt_hash=request.prompt_hash,
        image_job_id=image_job_id,
        output_paths=[f"/tmp/{image_job_id}.png"],
    )


def _image_service(
    tmp_path, *, queue_size: int = 8, free_vram_mb: int | None = 6000
) -> ImageGenerationService:
    settings = Settings(
        image_generation_output_dir=str(tmp_path / "images"),
        image_generation_history_path=str(tmp_path / "history.json"),
        character_assets_dir=str(tmp_path / "characters"),
        image_generation_resume_poll_seconds=0.01,
        image_generation_comfy_timeout_seconds=2.0,
        image_generation_max_queue_size=queue_size,
    )
    return ImageGenerationService(settings, coordinator=FakeCoordinator(free_vram_mb=free_vram_mb), adapter=FakeAdapter())  # type: ignore[arg-type]


def _capture_service(
    tmp_path, character_service: EvalCharacterService, *, memory=None
) -> MomentCaptureService:
    return MomentCaptureService(
        character_service=character_service,  # type: ignore[arg-type]
        image_service=_image_service(tmp_path),
        records_path=tmp_path / "moment_captures.json",
        memory_manager=memory or FakeMemoryManager(),  # type: ignore[arg-type]
        reflection_manager=FakeReflectionManager(),  # type: ignore[arg-type]
    )


def eval_identity_anchor_inclusion() -> VisualEvalResult:
    anchors = ["amber eyes", "warm brown skin", "same heart-shaped face"]
    bundle = _compile(_character("aria", "Aria", anchors), capture_intent="portrait")
    if (
        _contains_all(bundle.positive_prompt, anchors)
        and bundle.metadata["identity_anchors_used"] == anchors
    ):
        return _pass(
            "identity_anchor_inclusion",
            "stable anchors are present in positive prompt and metadata",
            anchors=anchors,
        )
    return _fail(
        "identity_anchor_inclusion",
        "missing identity anchor from positive prompt",
        positive_prompt=bundle.positive_prompt,
        metadata=bundle.metadata,
    )


def eval_rejected_trait_exclusion() -> VisualEvalResult:
    rejected = ["blue eyes", "silver hair"]
    bundle = _compile(_character("aria", "Aria", ["amber eyes"], rejected=rejected))
    leaked = [trait for trait in rejected if trait in bundle.positive_prompt]
    if not leaked and _contains_all(bundle.negative_prompt, rejected):
        return _pass(
            "rejected_trait_exclusion",
            "rejected traits stay negative-only",
            rejected=rejected,
        )
    return _fail(
        "rejected_trait_exclusion",
        "rejected trait leaked into positive prompt or negative prompt missed it",
        leaked=leaked,
        negative_prompt=bundle.negative_prompt,
    )


def eval_scene_trait_mutability() -> VisualEvalResult:
    character = _character(
        "aria", "Aria", ["amber eyes", "same face", "red dress outfit"]
    )
    first = _compile(
        character, scene_state={"outfit": "red raincoat", "location": "balcony"}
    )
    second = _compile(
        character, scene_state={"outfit": "black cafe coat", "location": "cafe"}
    )
    expected = ["amber eyes", "same face"]
    if (
        first.metadata["identity_anchors_used"] == expected
        and second.metadata["identity_anchors_used"] == expected
    ):
        return _pass(
            "scene_trait_mutability",
            "scene changes affect scene block without mutating anchors",
            first_hash=first.metadata["prompt_hash"],
            second_hash=second.metadata["prompt_hash"],
        )
    return _fail(
        "scene_trait_mutability",
        "scene-mutable terms contaminated identity anchors",
        first=first.metadata,
        second=second.metadata,
    )


def eval_same_character_consistency_across_scenes() -> VisualEvalResult:
    character = _character(
        "aria", "Aria", ["amber eyes", "warm brown skin", "same face"]
    )
    scenes = [
        _compile(
            character, scene_state={"location": "moon garden", "pose": "standing"}
        ),
        _compile(character, scene_state={"location": "busy cafe", "pose": "seated"}),
        _compile(character, scene_state={"location": "library", "pose": "reading"}),
    ]
    anchor_sets = [bundle.metadata["identity_anchors_used"] for bundle in scenes]
    if all(anchor_set == anchor_sets[0] for anchor_set in anchor_sets):
        return _pass(
            "same_character_consistency_across_scenes",
            "same character preserves identity anchor set across mutable scenes",
            anchor_sets=anchor_sets,
        )
    return _fail(
        "same_character_consistency_across_scenes",
        "same character produced inconsistent identity anchors",
        anchor_sets=anchor_sets,
    )


def eval_distinct_characters_differ() -> VisualEvalResult:
    aria = _compile(
        _character("aria", "Aria", ["amber eyes", "warm brown skin", "same face"])
    )
    lyra = _compile(
        _character("lyra", "Lyra", ["emerald eyes", "fox ears", "copper tail"])
    )
    if (
        aria.metadata["prompt_hash"] != lyra.metadata["prompt_hash"]
        and "fox ears" not in aria.positive_prompt
        and "amber eyes" not in lyra.positive_prompt
    ):
        return _pass(
            "distinct_characters_differ",
            "visually distinct characters compile to distinct prompts",
            aria_hash=aria.metadata["prompt_hash"],
            lyra_hash=lyra.metadata["prompt_hash"],
        )
    return _fail(
        "distinct_characters_differ",
        "distinct character prompts overlapped or hashed identically",
        aria=aria.metadata,
        lyra=lyra.metadata,
    )


def eval_outfit_reuse_without_identity_overwrite(tmp_path) -> VisualEvalResult:
    character = _character(
        "aria", "Aria", ["amber eyes", "same face"], current="long black-violet hair"
    )
    character_service = EvalCharacterService([character])
    service = _capture_service(tmp_path, character_service)
    record = _record(_request(character), "job-outfit")
    service._records[record.capture_id] = record
    response = service.submit_feedback(
        record.capture_id,
        VisualFeedbackRequest(
            character_id="aria",
            action=VisualFeedbackAction.use_outfit_again,
            trait_value="green velvet jacket",
        ),
    )
    unchanged = character_service.get_visual_identity("aria")
    future = _compile(
        character_service.load_by_id("aria"), scene_state={"outfit": "silver gown"}
    )
    if (
        response.visual_change_event
        and response.visual_change_event.changed_trait == "outfit"
        and unchanged.identity_anchors == ["amber eyes", "same face"]
        and "green velvet jacket" not in future.metadata["identity_anchors_used"]
    ):
        return _pass(
            "outfit_reuse_without_identity_overwrite",
            "outfit reuse is reviewable and does not overwrite anchors",
            event_id=response.visual_change_event.event_id,
        )
    return _fail(
        "outfit_reuse_without_identity_overwrite",
        "outfit feedback overwrote identity anchors or failed to create review event",
        identity=unchanged.model_dump(),
        event=(
            response.visual_change_event.model_dump()
            if response.visual_change_event
            else None
        ),
    )


def eval_feedback_and_review_flows(tmp_path) -> list[VisualEvalResult]:
    character = _character(
        "aria",
        "Aria",
        ["amber eyes", "same face"],
        current="long black-violet hair",
        evolving=[
            VisualTrait(name="hair", value="long black-violet hair", provenance="seed")
        ],
        rejected=[],
    )
    character_service = EvalCharacterService([character])
    service = _capture_service(tmp_path, character_service)
    record = _record(_request(character), "job-feedback")
    service._records[record.capture_id] = record

    wrong = service.submit_feedback(
        record.capture_id,
        VisualFeedbackRequest(
            character_id="aria",
            action=VisualFeedbackAction.wrong_appearance,
            trait_value="blue eyes",
        ),
    )
    assert wrong.visual_change_event is not None
    service.approve_visual_change(
        wrong.visual_change_event.event_id,
        VisualChangeReviewRequest(character_id="aria"),
    )
    after_wrong = _compile(character_service.load_by_id("aria"))

    canon = service.submit_feedback(
        record.capture_id,
        VisualFeedbackRequest(
            character_id="aria",
            action=VisualFeedbackAction.make_canon,
            trait_name="hair",
            trait_value="short copper bob",
        ),
    )
    assert canon.visual_change_event is not None
    before_approval = (
        character_service.get_visual_identity("aria").evolving_traits[-1].value
    )
    approved = service.approve_visual_change(
        canon.visual_change_event.event_id,
        VisualChangeReviewRequest(character_id="aria"),
    )
    after_approval = (
        character_service.get_visual_identity("aria").evolving_traits[-1].value
    )

    results = []
    results.append(
        _pass(
            "wrong_appearance_correction",
            "approved wrong appearance becomes future negative prompt",
            negative=after_wrong.negative_prompt,
        )
        if "blue eyes" in after_wrong.negative_prompt
        and "blue eyes" not in after_wrong.positive_prompt
        else _fail(
            "wrong_appearance_correction",
            "wrong appearance did not become negative-only future constraint",
            positive=after_wrong.positive_prompt,
            negative=after_wrong.negative_prompt,
        )
    )
    results.append(
        _pass(
            "make_canon_approval_flow",
            "canon is pending until approval and then updates identity",
            before=before_approval,
            after=after_approval,
            status=approved.event.canon_status.value,
        )
        if before_approval == "long black-violet hair"
        and after_approval == "short copper bob"
        and approved.event.canon_status == VisualChangeCanonStatus.canonized
        else _fail(
            "make_canon_approval_flow",
            "make-canon mutated too early or failed approval update",
            before=before_approval,
            after=after_approval,
            status=approved.event.canon_status.value,
        )
    )
    return results


def eval_character_scoped_visual_memory(tmp_path) -> VisualEvalResult:
    memory = FakeMemoryManager()
    character = _character("aria", "Aria", ["amber eyes", "same face"])
    service = _capture_service(
        tmp_path, EvalCharacterService([character]), memory=memory
    )
    record = _record(_request(character), "job-memory")
    service._records[record.capture_id] = record
    service.submit_feedback(
        record.capture_id,
        VisualFeedbackRequest(
            character_id="aria",
            action=VisualFeedbackAction.looks_right,
            note="Keep the moon pendant.",
        ),
    )
    if (
        memory.search_memories("pendant", character_id="aria")
        and memory.search_memories("pendant", character_id="other") == []
    ):
        return _pass(
            "character_scoped_visual_memory",
            "approved visual memory is character-private by default",
            memory_count=len(memory.memories),
        )
    return _fail(
        "character_scoped_visual_memory",
        "visual memory leaked across character scope or was not written",
        memories=memory.memories,
    )


@pytest.mark.parametrize(
    "eval_fn",
    [
        eval_identity_anchor_inclusion,
        eval_rejected_trait_exclusion,
        eval_scene_trait_mutability,
        eval_same_character_consistency_across_scenes,
        eval_distinct_characters_differ,
    ],
)
def test_visual_prompt_contract_eval_harness(
    eval_fn: Callable[[], VisualEvalResult],
) -> None:
    _assert_eval(eval_fn())


def test_visual_feedback_contract_eval_harness(tmp_path) -> None:
    results = [
        eval_outfit_reuse_without_identity_overwrite(tmp_path),
        *eval_feedback_and_review_flows(tmp_path),
        eval_character_scoped_visual_memory(tmp_path),
    ]
    failures = [asdict(result) for result in results if not result.passed]
    assert not failures, failures


def test_8gb_queue_pressure_eval_harness(tmp_path) -> None:
    async def run_test() -> VisualEvalResult:
        service = _image_service(tmp_path, queue_size=1, free_vram_mb=900)
        first = await service.submit(
            ImageGenerateRequest(
                prompt="first eval image",
                quality_preset=ImageQualityPreset.high_8gb,
            )
        )
        try:
            second = await service.submit(
                ImageGenerateRequest(
                    prompt="second eval image",
                    quality_preset=ImageQualityPreset.high_8gb,
                )
            )
            accepted_jobs: list[str] = [first.job_id, second.job_id]
            await service.submit(
                ImageGenerateRequest(
                    prompt="third eval image",
                    quality_preset=ImageQualityPreset.high_8gb,
                )
            )
        except ImageGenerationError as exc:
            if exc.code == "image_queue_full" and exc.retryable:
                return _pass(
                    "8gb_queue_pressure",
                    "queue rejects overload gracefully without blocking caller",
                    first_job=first.job_id,
                    error_code=exc.code,
                )
            return _fail(
                "8gb_queue_pressure",
                "queue overload returned non-retryable or wrong error",
                code=exc.code,
                retryable=exc.retryable,
            )
        return _fail(
            "8gb_queue_pressure",
            "queue accepted unbounded overload instead of degrading gracefully",
            accepted_jobs=accepted_jobs,
        )

    _assert_eval(asyncio.run(run_test()))
