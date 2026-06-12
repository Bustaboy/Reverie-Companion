"""Tests for the 8GB-safe image generation queue foundation."""

from __future__ import annotations

import asyncio

from app.core.config import Settings
from app.models.image import ImageGenerateRequest
from app.services.image_generation_service import ImageGenerationService, VRAMSnapshot
from app.services.tts_service import tts_activity


class FakeVRAMMonitor:
    def __init__(self, snapshots: list[VRAMSnapshot]) -> None:
        self.snapshots = snapshots
        self.index = 0
        self.clear_calls = 0

    def snapshot(self) -> VRAMSnapshot:
        if self.index >= len(self.snapshots):
            return self.snapshots[-1]
        snapshot = self.snapshots[self.index]
        self.index += 1
        return snapshot

    def clear_cuda_cache(self) -> None:
        self.clear_calls += 1


class FakeComfyAdapter:
    def __init__(self, delay: float = 0.01) -> None:
        self.delay = delay
        self.calls = []

    async def generate(self, *, job, budget, device_mode, progress):
        self.calls.append({"job_id": job.job_id, "preset": budget.preset, "device_mode": device_mode})
        progress(0.5, "fake_render", "Rendering test image.")
        await asyncio.sleep(self.delay)
        return [f"reverie/{job.job_id}_00001.png"]


def make_settings(tmp_path) -> Settings:
    return Settings(
        voice_profile_store_path=str(tmp_path / "voices.json"),
        image_resource_poll_seconds=0.01,
        image_comfyui_poll_seconds=0.01,
        image_queue_max_jobs=4,
    )


def test_image_job_completes_with_progress_events(tmp_path) -> None:
    async def run_test() -> None:
        service = ImageGenerationService(
            make_settings(tmp_path),
            adapter=FakeComfyAdapter(),
            vram_monitor=FakeVRAMMonitor([VRAMSnapshot(7000, 8192, 1192, "test")]),
        )

        job = await service.submit(ImageGenerateRequest(prompt="soft moonlit portrait", quality_preset="preview_8gb"))
        events = []
        async for event in service.events(job.job_id):
            events.append(event)

        final = service.get_job(job.job_id)
        assert final.status == "completed"
        assert final.output_paths == [f"reverie/{job.job_id}_00001.png"]
        assert [event.status for event in events][-1] == "completed"
        assert any(event.phase == "fake_render" for event in events)

    asyncio.run(run_test())


def test_high_preset_downgrades_when_vram_only_fits_preview(tmp_path) -> None:
    async def run_test() -> None:
        adapter = FakeComfyAdapter()
        service = ImageGenerationService(
            make_settings(tmp_path),
            adapter=adapter,
            vram_monitor=FakeVRAMMonitor([VRAMSnapshot(4500, 8192, 3692, "test")]),
        )

        job = await service.submit(ImageGenerateRequest(prompt="preview safe scene", quality_preset="high_8gb"))
        async for _event in service.events(job.job_id):
            pass

        final = service.get_job(job.job_id)
        assert final.status == "completed"
        assert final.requested_preset == "high_8gb"
        assert final.effective_preset == "preview_8gb"
        assert adapter.calls[0]["preset"] == "preview_8gb"

    asyncio.run(run_test())


def test_tts_activity_pauses_then_auto_resumes_image_job(tmp_path) -> None:
    async def run_test() -> None:
        await tts_activity.begin()
        service = ImageGenerationService(
            make_settings(tmp_path),
            adapter=FakeComfyAdapter(),
            vram_monitor=FakeVRAMMonitor([VRAMSnapshot(7000, 8192, 1192, "test")]),
        )
        job = await service.submit(ImageGenerateRequest(prompt="wait for voice", quality_preset="preview_8gb"))

        await asyncio.sleep(0.03)
        paused = service.get_job(job.job_id)
        assert paused.status == "paused"
        assert paused.resource_mode == "tts_priority"

        await tts_activity.end()
        async for _event in service.events(job.job_id):
            pass

        final = service.get_job(job.job_id)
        assert final.status == "completed"

    asyncio.run(run_test())
