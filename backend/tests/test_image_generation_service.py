"""Tests for the queued image generation backend foundation."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from app.core.config import Settings
from app.models.image import ImageGenerateRequest, ImageJobStatus, ImageQualityPreset
from app.services.image_generation_service import (
    ImageGenerationError,
    ImageGenerationService,
)
from app.services.resource_coordinator import VRAMSnapshot


class FakeCoordinator:
    def __init__(self, *, free_vram_mb: int | None = 6000) -> None:
        self._tts_active = False
        self.free_vram_mb = free_vram_mb
        self.wait_calls = 0

    @property
    def tts_active(self) -> bool:
        return self._tts_active

    @tts_active.setter
    def tts_active(self, value: bool) -> None:
        self._tts_active = value

    async def wait_for_tts_idle(self) -> None:
        self.wait_calls += 1
        self._tts_active = False

    @asynccontextmanager
    async def image_job_section(self, *, job_id: str):
        yield

    def snapshot_vram(self) -> VRAMSnapshot:
        return VRAMSnapshot(
            free_mb=self.free_vram_mb,
            total_mb=8192 if self.free_vram_mb is not None else None,
            used_mb=8192 - self.free_vram_mb if self.free_vram_mb is not None else None,
            source="test",
        )


class FakeAdapter:
    def __init__(self) -> None:
        self.calls = []
        self.interrupt_calls = 0

    async def generate(self, job, preset):
        self.calls.append((job.active_preset, preset.width, preset.height))
        await asyncio.sleep(0.01)
        return [f"{job.job_id}.png"]

    async def interrupt(self) -> None:
        self.interrupt_calls += 1


def make_service(
    tmp_path, coordinator: FakeCoordinator, adapter: FakeAdapter
) -> ImageGenerationService:
    settings = Settings(
        image_generation_output_dir=str(tmp_path / "images"),
        image_generation_history_path=str(tmp_path / "history.json"),
        character_assets_dir=str(tmp_path / "characters"),
        image_generation_resume_poll_seconds=0.01,
        image_generation_comfy_timeout_seconds=2.0,
    )
    return ImageGenerationService(settings, coordinator=coordinator, adapter=adapter)  # type: ignore[arg-type]


def test_image_job_completes_with_progress_events(tmp_path) -> None:
    async def run_test() -> None:
        coordinator = FakeCoordinator(free_vram_mb=7000)
        adapter = FakeAdapter()
        service = make_service(tmp_path, coordinator, adapter)

        job = await service.submit(
            ImageGenerateRequest(
                prompt="quiet moonlit portrait",
                quality_preset=ImageQualityPreset.preview_8gb,
            )
        )
        while service.get_job(job.job_id).status not in {
            ImageJobStatus.completed,
            ImageJobStatus.failed,
        }:
            await asyncio.sleep(0.01)

        completed = service.get_job(job.job_id)
        assert completed.status == ImageJobStatus.completed
        assert completed.output_paths == [f"{job.job_id}.png"]
        assert adapter.calls[0][0] == ImageQualityPreset.preview_8gb

    asyncio.run(run_test())


def test_image_job_degrades_high_preset_when_vram_is_low(tmp_path) -> None:
    async def run_test() -> None:
        coordinator = FakeCoordinator(free_vram_mb=3200)
        adapter = FakeAdapter()
        service = make_service(tmp_path, coordinator, adapter)

        job = await service.submit(
            ImageGenerateRequest(
                prompt="soft scenic background",
                quality_preset=ImageQualityPreset.high_8gb,
            )
        )
        while service.get_job(job.job_id).status not in {
            ImageJobStatus.completed,
            ImageJobStatus.failed,
        }:
            await asyncio.sleep(0.01)

        completed = service.get_job(job.job_id)
        assert completed.status == ImageJobStatus.completed
        assert completed.requested_preset == ImageQualityPreset.high_8gb
        assert completed.active_preset == ImageQualityPreset.preview_8gb
        assert completed.fallback_used is True

    asyncio.run(run_test())


def test_image_job_pauses_while_tts_is_active(tmp_path) -> None:
    async def run_test() -> None:
        coordinator = FakeCoordinator(free_vram_mb=7000)
        coordinator.tts_active = True
        adapter = FakeAdapter()
        service = make_service(tmp_path, coordinator, adapter)

        job = await service.submit(ImageGenerateRequest(prompt="simple preview"))
        while service.get_job(job.job_id).status not in {
            ImageJobStatus.completed,
            ImageJobStatus.failed,
        }:
            await asyncio.sleep(0.01)

        completed = service.get_job(job.job_id)
        assert completed.status == ImageJobStatus.completed
        assert coordinator.wait_calls == 1
        events = [event.phase for event in service._jobs[job.job_id].events]
        assert "tts_priority" in events

    asyncio.run(run_test())


def test_image_job_stores_engineered_prompt_and_negative_prompt(tmp_path) -> None:
    async def run_test() -> None:
        coordinator = FakeCoordinator(free_vram_mb=7000)
        adapter = FakeAdapter()
        service = make_service(tmp_path, coordinator, adapter)

        job = await service.submit(
            ImageGenerateRequest(
                prompt="intimate bedroom embrace with us together",
                negative_prompt="flat lighting",
                context={
                    "character": {
                        "name": "Mira",
                        "appearance": "silver hair and violet eyes",
                    },
                    "participants": ["user", "character"],
                    "scene_tags": ["nsfw", "intimate"],
                },
            )
        )

        queued = service.get_job(job.job_id)
        assert "Mira as the main character" in queued.prompt
        assert "silver hair and violet eyes" in queued.prompt
        assert "avoid showing the user's face" in queued.prompt
        assert "user face visible" in queued.negative_prompt
        assert "flat lighting" in queued.negative_prompt
        assert (
            service._jobs[job.job_id].context["image_prompt_engine"]["deterministic"]
            is True
        )

    asyncio.run(run_test())


def test_image_output_reference_serves_only_attached_local_files(tmp_path) -> None:
    async def run_test() -> None:
        coordinator = FakeCoordinator(free_vram_mb=7000)
        adapter = FakeAdapter()
        service = make_service(tmp_path, coordinator, adapter)

        job = await service.submit(ImageGenerateRequest(prompt="safe local output"))
        while service.get_job(job.job_id).status not in {
            ImageJobStatus.completed,
            ImageJobStatus.failed,
        }:
            await asyncio.sleep(0.01)

        output_dir = tmp_path / "images"
        output_file = output_dir / f"{job.job_id}.png"
        output_file.write_bytes(b"fake png")

        reference = service.get_output_reference(job.job_id, 0)
        assert reference.local_path == output_file.resolve()
        assert reference.comfyui_view_url.endswith(
            f"/view?filename={job.job_id}.png&type=output"
        )

    asyncio.run(run_test())


def test_image_output_reference_rejects_unattached_or_unsafe_paths(tmp_path) -> None:
    async def run_test() -> None:
        coordinator = FakeCoordinator(free_vram_mb=7000)
        adapter = FakeAdapter()
        service = make_service(tmp_path, coordinator, adapter)

        job = await service.submit(ImageGenerateRequest(prompt="safe fallback output"))
        while service.get_job(job.job_id).status not in {
            ImageJobStatus.completed,
            ImageJobStatus.failed,
        }:
            await asyncio.sleep(0.01)

        # Simulate a malformed ComfyUI output that is attached to the job but
        # points outside Reverie's output directory. The resolver must not serve
        # it as a local file; it may only offer the ComfyUI /view fallback.
        service._jobs[job.job_id].output_paths = ["../private.png"]
        reference = service.get_output_reference(job.job_id, 0)
        assert reference.local_path is None
        assert reference.comfyui_view_url is None

        try:
            service.get_output_reference(job.job_id, 1)
        except ImageGenerationError as exc:
            assert exc.code == "image_output_not_found"
        else:  # pragma: no cover - defensive assertion clarity.
            raise AssertionError("Unattached output index should be rejected")

    asyncio.run(run_test())


def test_image_history_persists_completed_jobs_per_conversation(tmp_path) -> None:
    async def run_test() -> None:
        coordinator = FakeCoordinator(free_vram_mb=7000)
        adapter = FakeAdapter()
        service = make_service(tmp_path, coordinator, adapter)

        job = await service.submit(
            ImageGenerateRequest(
                conversation_id="conv-a",
                prompt="warm candlelit portrait",
                source="chat-message",
                source_message_id="msg-1",
            )
        )
        while service.get_job(job.job_id).status not in {
            ImageJobStatus.completed,
            ImageJobStatus.failed,
        }:
            await asyncio.sleep(0.01)

        history = service.list_history("conv-a")
        assert len(history.items) == 1
        assert history.items[0].job_id == job.job_id
        assert history.items[0].source_message_id == "msg-1"
        assert service.list_history("other").items == []

        history_payload = json.loads((tmp_path / "history.json").read_text())
        assert history_payload["schema_version"] == 2
        assert history_payload["conversations"]["conv-a"][0]["job_id"] == job.job_id

        reloaded = make_service(tmp_path, coordinator, adapter)
        assert reloaded.list_history("conv-a").items[0].job_id == job.job_id

    asyncio.run(run_test())


def test_image_history_delete_and_save_asset_manifest(tmp_path) -> None:
    async def run_test() -> None:
        coordinator = FakeCoordinator(free_vram_mb=7000)
        adapter = FakeAdapter()
        service = make_service(tmp_path, coordinator, adapter)

        job = await service.submit(
            ImageGenerateRequest(conversation_id="conv-a", prompt="asset portrait")
        )
        while service.get_job(job.job_id).status not in {
            ImageJobStatus.completed,
            ImageJobStatus.failed,
        }:
            await asyncio.sleep(0.01)

        output_file = tmp_path / "images" / f"{job.job_id}.png"
        output_file.write_bytes(b"fake png")

        saved = await service.save_to_character_assets(
            job.job_id, character_id="Mira", asset_label="Portrait"
        )
        assert saved.item.saved_to_assets is True
        assert "mira" in saved.asset_path
        assert "manifest.json" in saved.manifest_path
        manifest = json.loads(
            (tmp_path / "characters" / "mira" / "assets" / "manifest.json").read_text()
        )
        assert manifest["schema_version"] == 2
        assert manifest["character_id"] == "mira"
        assert manifest["images"][0]["asset_id"] == f"image:{job.job_id}:0"
        assert manifest["images"][0]["path"] == f"images/{job.job_id}_0.png"

        saved_again = await service.save_to_character_assets(
            job.job_id, character_id="Mira", asset_label="Portrait"
        )
        manifest = json.loads(
            (tmp_path / "characters" / "mira" / "assets" / "manifest.json").read_text()
        )
        assert saved_again.item.saved_to_assets is True
        assert len(manifest["images"]) == 1

        remaining = await service.delete_history_item(job.job_id)
        assert remaining.items == []

    asyncio.run(run_test())


def test_image_history_reloads_legacy_flat_items(tmp_path) -> None:
    async def run_test() -> None:
        coordinator = FakeCoordinator(free_vram_mb=7000)
        adapter = FakeAdapter()
        service = make_service(tmp_path, coordinator, adapter)

        job = await service.submit(
            ImageGenerateRequest(
                conversation_id="legacy-conv", prompt="legacy portrait"
            )
        )
        while service.get_job(job.job_id).status not in {
            ImageJobStatus.completed,
            ImageJobStatus.failed,
        }:
            await asyncio.sleep(0.01)

        flat_item = service.list_history("legacy-conv").items[0].model_dump(mode="json")
        (tmp_path / "history.json").write_text(json.dumps({"items": [flat_item]}))

        reloaded = make_service(tmp_path, coordinator, adapter)
        assert reloaded.list_history("legacy-conv").items[0].job_id == job.job_id

    asyncio.run(run_test())


def test_image_job_unloads_idle_auxiliary_models_before_generation(tmp_path) -> None:
    async def run_test() -> None:
        coordinator = FakeCoordinator(free_vram_mb=7000)
        unloaded: list[str] = []
        coordinator.unload_auxiliary_models = lambda reason: unloaded.append(reason) or ["orpheus_tts"]  # type: ignore[attr-defined]
        adapter = FakeAdapter()
        service = make_service(tmp_path, coordinator, adapter)

        job = await service.submit(ImageGenerateRequest(prompt="headroom portrait"))
        while service.get_job(job.job_id).status not in {
            ImageJobStatus.completed,
            ImageJobStatus.failed,
        }:
            await asyncio.sleep(0.01)

        assert unloaded == ["image_generation_start"]
        phases = [event.phase for event in service._jobs[job.job_id].events]
        assert "unloaded_auxiliary_models" in phases

    asyncio.run(run_test())


def test_image_job_exposes_resource_pressure_warning(tmp_path) -> None:
    async def run_test() -> None:
        coordinator = FakeCoordinator(free_vram_mb=1100)
        adapter = FakeAdapter()
        service = make_service(tmp_path, coordinator, adapter)

        job = await service.submit(ImageGenerateRequest(prompt="tight vram portrait"))
        await asyncio.sleep(0.03)
        waiting = service.get_job(job.job_id)

        assert waiting.status == ImageJobStatus.waiting_for_resources
        assert waiting.pressure == "critical"
        assert waiting.warning is not None
        assert waiting.vram_free_mb == 1100

        await service.cancel(job.job_id)

    asyncio.run(run_test())


def test_history_records_capture_gallery_metadata_and_filters(tmp_path) -> None:
    async def run_test() -> None:
        coordinator = FakeCoordinator(free_vram_mb=7000)
        adapter = FakeAdapter()
        service = make_service(tmp_path, coordinator, adapter)

        job = await service.submit(
            ImageGenerateRequest(
                conversation_id="conv-a",
                source="moment_capture",
                source_message_id="msg-a",
                prompt="aria at sunrise",
                context={
                    "character_id": "aria",
                    "session_id": "session-a",
                    "moment_capture_id": "mc-a",
                    "scene_summary": "Sunrise garden confession",
                    "prompt_hash": "abc12345",
                    "feedback_state": "pending",
                    "review_state": "unreviewed",
                    "canon_status": "not_canon",
                },
            )
        )
        while service.get_job(job.job_id).status not in {
            ImageJobStatus.completed,
            ImageJobStatus.failed,
        }:
            await asyncio.sleep(0.01)

        [item] = service.list_history("conv-a", character_id="aria").items
        assert item.character_id == "aria"
        assert item.session_id == "session-a"
        assert item.moment_capture_id == "mc-a"
        assert item.scene_summary == "Sunrise garden confession"
        assert item.prompt_hash == "abc12345"
        assert service.list_history("conv-a", character_id="other").items == []

    asyncio.run(run_test())


def test_delete_keeps_normalized_history_consistent(tmp_path) -> None:
    async def run_test() -> None:
        service = make_service(
            tmp_path, FakeCoordinator(free_vram_mb=7000), FakeAdapter()
        )
        job = await service.submit(
            ImageGenerateRequest(
                conversation_id="conv-del",
                prompt="delete me",
                context={"character_id": "aria"},
            )
        )
        while service.get_job(job.job_id).status not in {
            ImageJobStatus.completed,
            ImageJobStatus.failed,
        }:
            await asyncio.sleep(0.01)
        response = await service.delete_history_item(job.job_id)
        assert response.items == []
        assert service.get_job(job.job_id).output_paths == []
        assert service.list_history("conv-del", character_id="aria").items == []

    asyncio.run(run_test())
