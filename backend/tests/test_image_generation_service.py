"""Tests for the queued image generation backend foundation."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from app.core.config import Settings
from app.models.image import ImageGenerateRequest, ImageJobStatus, ImageQualityPreset
from app.services.image_generation_service import ImageGenerationService
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
