"""8GB-safe ComfyUI image generation queue for Reverie chat media.

Resource budget (RTX 4070 8GB mobile target):
  feature: "in-chat image generation foundation"
  interactive_required: false
  primary_gpu_models: ["ComfyUI Flux GGUF Q4/Q5 or FP8, batch size 1"]
  peak_vram_mb_estimate: 3500-5700 depending on preset
  steady_vram_mb_estimate: 0 while idle; ComfyUI is optional/external
  cpu_ram_mb_estimate: 1500-6000 depending on fallback/offload path
  concurrency_limit: 1 exclusive media job
  fallbacks:
    - wait while Orpheus/TTS is active
    - downgrade high_8gb -> balanced_8gb -> preview_8gb when VRAM is low
    - optional CPU/offload mode when no preset fits
  cleanup:
    - send one bounded ComfyUI job, drop local payload references, clear CUDA cache
    - keep Reverie chat/TTS independent from media failures
  telemetry:
    - log queue, pause/resume, VRAM snapshots, preset downgrade, completion/failure
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import json
import logging
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic, sleep
from typing import Any
from uuid import uuid4

from app.core.config import Settings
from app.models.image import (
    ImageGenerateRequest,
    ImageJobEvent,
    ImageJobRead,
    ImageJobStatus,
    ImageQualityPreset,
)
from app.services.tts_service import tts_activity

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES: set[ImageJobStatus] = {"completed", "failed", "cancelled"}
_PRESET_ORDER: tuple[ImageQualityPreset, ...] = (
    "preview_8gb",
    "balanced_8gb",
    "high_8gb",
)


class ImageGenerationServiceError(Exception):
    """Recoverable image-generation domain error."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "image_generation_failed",
        retryable: bool = False,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable
        self.details = details or {}


@dataclass(frozen=True)
class VRAMSnapshot:
    """Best-effort local GPU memory snapshot."""

    free_mb: int | None
    total_mb: int | None
    used_mb: int | None
    source: str

    @property
    def is_known(self) -> bool:
        return self.free_mb is not None and self.total_mb is not None


@dataclass(frozen=True)
class ImagePresetBudget:
    """8GB-safe quality tier limits for one ComfyUI job."""

    preset: ImageQualityPreset
    width: int
    height: int
    steps: int
    cfg: float
    min_free_vram_mb: int
    estimated_peak_vram_mb: int
    sampler: str = "euler"
    scheduler: str = "simple"


@dataclass
class ImageJob:
    """Mutable in-memory job record for the Task 3A foundation."""

    job_id: str
    prompt: str
    context: dict[str, Any]
    requested_preset: ImageQualityPreset
    effective_preset: ImageQualityPreset
    status: ImageJobStatus = "queued"
    progress: float = 0.0
    phase: str = "queued"
    message: str = "Image generation is queued."
    resource_mode: str = "queued"
    paused_reason: str | None = None
    output_paths: list[str] = field(default_factory=list)
    error: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    sequence: int = 0
    events: list[ImageJobEvent] = field(default_factory=list)
    cancel_requested: bool = False
    user_paused: bool = False
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)

    def to_read(self) -> ImageJobRead:
        return ImageJobRead(
            job_id=self.job_id,
            status=self.status,
            requested_preset=self.requested_preset,
            effective_preset=self.effective_preset,
            progress=self.progress,
            phase=self.phase,
            message=self.message,
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
            started_at=self.started_at.isoformat() if self.started_at else None,
            completed_at=self.completed_at.isoformat() if self.completed_at else None,
            paused_reason=self.paused_reason,
            resource_mode=self.resource_mode,
            output_paths=list(self.output_paths),
            error=self.error,
        )


class VRAMMonitor:
    """Best-effort VRAM monitor that never requires GPU dependencies."""

    def snapshot(self) -> VRAMSnapshot:
        torch_snapshot = self._torch_snapshot()
        if torch_snapshot is not None:
            return torch_snapshot
        nvidia_snapshot = self._nvidia_smi_snapshot()
        if nvidia_snapshot is not None:
            return nvidia_snapshot
        return VRAMSnapshot(free_mb=None, total_mb=None, used_mb=None, source="unknown")

    def clear_cuda_cache(self) -> None:
        if importlib.util.find_spec("torch") is None:
            return
        torch = importlib.import_module("torch")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _torch_snapshot(self) -> VRAMSnapshot | None:
        if importlib.util.find_spec("torch") is None:
            return None
        torch = importlib.import_module("torch")
        if not torch.cuda.is_available():
            return None
        free_bytes, total_bytes = torch.cuda.mem_get_info()
        free_mb = int(free_bytes // (1024 * 1024))
        total_mb = int(total_bytes // (1024 * 1024))
        return VRAMSnapshot(
            free_mb=free_mb,
            total_mb=total_mb,
            used_mb=max(total_mb - free_mb, 0),
            source="torch.cuda.mem_get_info",
        )

    def _nvidia_smi_snapshot(self) -> VRAMSnapshot | None:
        binary = shutil.which("nvidia-smi")
        if not binary:
            return None
        completed = subprocess.run(
            [
                binary,
                "--query-gpu=memory.total,memory.used,memory.free",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=2,
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            return None
        first_line = completed.stdout.strip().splitlines()[0]
        total_text, used_text, free_text = [part.strip() for part in first_line.split(",")[:3]]
        return VRAMSnapshot(
            free_mb=int(free_text),
            total_mb=int(total_text),
            used_mb=int(used_text),
            source="nvidia-smi",
        )


class ComfyUIAdapter:
    """Small HTTP adapter for local ComfyUI prompt submission and polling."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def generate(
        self,
        *,
        job: ImageJob,
        budget: ImagePresetBudget,
        device_mode: str,
        progress: Callable[[float, str, str], None],
    ) -> list[str]:
        return await asyncio.to_thread(
            self._generate_sync,
            job=job,
            budget=budget,
            device_mode=device_mode,
            progress=progress,
        )

    def _generate_sync(
        self,
        *,
        job: ImageJob,
        budget: ImagePresetBudget,
        device_mode: str,
        progress: Callable[[float, str, str], None],
    ) -> list[str]:
        progress(0.18, "comfyui_submit", "Submitting local ComfyUI workflow.")
        workflow = self._workflow(job=job, budget=budget, device_mode=device_mode)
        client_id = f"reverie_{job.job_id}"
        response = self._request_json(
            "POST",
            "/prompt",
            {"prompt": workflow, "client_id": client_id},
            timeout=self._settings.image_comfyui_timeout_seconds,
        )
        prompt_id = response.get("prompt_id")
        if not isinstance(prompt_id, str):
            raise ImageGenerationServiceError(
                "ComfyUI did not return a prompt id.",
                code="image_comfyui_prompt_rejected",
                retryable=True,
                details={"response": response},
            )

        deadline = monotonic() + self._settings.image_comfyui_timeout_seconds
        while monotonic() < deadline:
            if job.cancel_requested:
                self._interrupt_comfyui()
                raise ImageGenerationServiceError(
                    "Image generation was cancelled.",
                    code="image_generation_cancelled",
                    retryable=False,
                )
            progress(0.35, "comfyui_render", "ComfyUI is rendering the image.")
            history = self._request_json("GET", f"/history/{prompt_id}", None, timeout=5)
            if prompt_id in history:
                outputs = self._extract_outputs(history[prompt_id])
                if outputs:
                    progress(0.95, "comfyui_complete", "ComfyUI finished rendering.")
                    return outputs
            sleep(self._settings.image_comfyui_poll_seconds)

        raise ImageGenerationServiceError(
            "ComfyUI image generation timed out.",
            code="image_comfyui_timeout",
            retryable=True,
            details={"timeout_seconds": self._settings.image_comfyui_timeout_seconds},
        )

    def _workflow(self, *, job: ImageJob, budget: ImagePresetBudget, device_mode: str) -> dict[str, Any]:
        configured = self._settings.image_comfyui_workflow_path
        if configured:
            path = Path(configured).expanduser()
            if not path.exists():
                raise ImageGenerationServiceError(
                    "Configured ComfyUI workflow file does not exist.",
                    code="image_workflow_missing",
                    retryable=False,
                    details={"workflow_path": str(path)},
                )
            workflow = json.loads(path.read_text(encoding="utf-8"))
            return self._inject_workflow_values(workflow, job=job, budget=budget, device_mode=device_mode)

        # Low-VRAM Flux GGUF skeleton. Users can replace this with an exported
        # ComfyUI workflow; this default documents the intended local node stack
        # without making chat/TTS depend on ComfyUI custom nodes at startup.
        return {
            "1": {
                "class_type": "UnetLoaderGGUF",
                "inputs": {"unet_name": self._settings.image_flux_gguf_model_name},
            },
            "2": {
                "class_type": "DualCLIPLoader",
                "inputs": {
                    "clip_name1": self._settings.image_flux_clip_l_name,
                    "clip_name2": self._settings.image_flux_t5xxl_name,
                    "type": "flux",
                },
            },
            "3": {"class_type": "VAELoader", "inputs": {"vae_name": self._settings.image_flux_vae_name}},
            "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": job.prompt}},
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": budget.width, "height": budget.height, "batch_size": 1},
            },
            "6": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["4", 0],
                    "negative": ["4", 0],
                    "latent_image": ["5", 0],
                    "seed": int(datetime.now(UTC).timestamp() * 1000) % 2_147_483_647,
                    "steps": budget.steps,
                    "cfg": budget.cfg,
                    "sampler_name": budget.sampler,
                    "scheduler": budget.scheduler,
                    "denoise": 1.0,
                },
            },
            "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
            "8": {
                "class_type": "SaveImage",
                "inputs": {"images": ["7", 0], "filename_prefix": f"reverie/{job.job_id}"},
            },
        }

    def _inject_workflow_values(
        self,
        workflow: dict[str, Any],
        *,
        job: ImageJob,
        budget: ImagePresetBudget,
        device_mode: str,
    ) -> dict[str, Any]:
        patched = json.loads(json.dumps(workflow))
        for node in patched.values():
            inputs = node.get("inputs") if isinstance(node, dict) else None
            if not isinstance(inputs, dict):
                continue
            for key, value in list(inputs.items()):
                if value == "{{prompt}}":
                    inputs[key] = job.prompt
                elif value == "{{width}}":
                    inputs[key] = budget.width
                elif value == "{{height}}":
                    inputs[key] = budget.height
                elif value == "{{steps}}":
                    inputs[key] = budget.steps
                elif value == "{{cfg}}":
                    inputs[key] = budget.cfg
                elif value == "{{device_mode}}":
                    inputs[key] = device_mode
        return patched

    def _request_json(
        self, method: str, path: str, payload: dict[str, Any] | None, *, timeout: float
    ) -> dict[str, Any]:
        url = urllib.parse.urljoin(self._settings.image_comfyui_url.rstrip("/") + "/", path.lstrip("/"))
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise ImageGenerationServiceError(
                "Local ComfyUI is not reachable. Start ComfyUI with --lowvram or configure its URL.",
                code="image_comfyui_unavailable",
                retryable=True,
                details={"url": self._settings.image_comfyui_url},
            ) from exc
        return json.loads(body) if body else {}

    def _extract_outputs(self, history_item: dict[str, Any]) -> list[str]:
        outputs: list[str] = []
        for output in history_item.get("outputs", {}).values():
            for image in output.get("images", []):
                filename = image.get("filename")
                subfolder = image.get("subfolder", "")
                if not filename:
                    continue
                outputs.append(str(Path(subfolder) / filename) if subfolder else str(filename))
        return outputs

    def _interrupt_comfyui(self) -> None:
        try:
            self._request_json("POST", "/interrupt", {}, timeout=2)
        except ImageGenerationServiceError:
            logger.info("ComfyUI interrupt request could not be delivered")


class ImageGenerationService:
    """Business service for queued, TTS-priority image generation."""

    def __init__(
        self,
        settings: Settings,
        *,
        adapter: ComfyUIAdapter | None = None,
        vram_monitor: VRAMMonitor | None = None,
    ) -> None:
        self._settings = settings
        self._adapter = adapter or ComfyUIAdapter(settings)
        self._vram = vram_monitor or VRAMMonitor()
        self._jobs: dict[str, ImageJob] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=settings.image_queue_max_jobs)
        self._worker_task: asyncio.Task[None] | None = None
        self._worker_lock = asyncio.Lock()

    async def submit(self, request: ImageGenerateRequest) -> ImageJobRead:
        await self._ensure_worker()
        if self._queue.full():
            raise ImageGenerationServiceError(
                "Image generation queue is full. Please wait for another job to finish.",
                code="image_queue_full",
                retryable=True,
                details={"max_jobs": self._settings.image_queue_max_jobs},
            )
        context = request.context.model_dump() if hasattr(request.context, "model_dump") else (request.context or {})
        job = ImageJob(
            job_id=f"img_{uuid4().hex}",
            prompt=request.prompt,
            context=dict(context),
            requested_preset=request.quality_preset,
            effective_preset=request.quality_preset,
        )
        self._jobs[job.job_id] = job
        await self._record_event(job, event="job.queued", message="Image generation is queued.")
        await self._queue.put(job.job_id)
        logger.info(
            "Queued image generation job",
            extra={"job_id": job.job_id, "quality_preset": job.requested_preset},
        )
        return job.to_read()

    def get_job(self, job_id: str) -> ImageJobRead:
        return self._job_or_error(job_id).to_read()

    async def cancel(self, job_id: str) -> ImageJobRead:
        job = self._job_or_error(job_id)
        job.cancel_requested = True
        if job.status not in _TERMINAL_STATUSES:
            await self._transition(
                job,
                status="cancelled",
                phase="cancelled",
                progress=job.progress,
                message="Image generation was cancelled.",
                resource_mode="cancelled",
            )
        return job.to_read()

    async def pause(self, job_id: str) -> ImageJobRead:
        job = self._job_or_error(job_id)
        if job.status in _TERMINAL_STATUSES:
            return job.to_read()
        job.user_paused = True
        await self._transition(
            job,
            status="paused",
            phase="user_paused",
            progress=job.progress,
            message="Image generation is paused.",
            resource_mode="manual_pause",
            paused_reason="Paused by user.",
        )
        return job.to_read()

    async def resume(self, job_id: str) -> ImageJobRead:
        job = self._job_or_error(job_id)
        if job.status in _TERMINAL_STATUSES:
            return job.to_read()
        job.user_paused = False
        await self._transition(
            job,
            status="waiting_resources",
            phase="waiting_resources",
            progress=job.progress,
            message="Image generation will resume when TTS and VRAM are available.",
            resource_mode="waiting",
            paused_reason=None,
        )
        return job.to_read()

    async def events(self, job_id: str) -> AsyncIterator[ImageJobEvent]:
        job = self._job_or_error(job_id)
        next_index = 0
        while True:
            async with job.condition:
                while next_index >= len(job.events) and job.status not in _TERMINAL_STATUSES:
                    await job.condition.wait()
                pending = job.events[next_index:]
                next_index = len(job.events)
                should_stop = job.status in _TERMINAL_STATUSES
            for event in pending:
                yield event
            if should_stop:
                break

    async def _ensure_worker(self) -> None:
        async with self._worker_lock:
            if self._worker_task is None or self._worker_task.done():
                self._worker_task = asyncio.create_task(self._worker(), name="reverie_image_generation_worker")

    async def _worker(self) -> None:
        while True:
            job_id = await self._queue.get()
            job = self._jobs.get(job_id)
            if job is None:
                self._queue.task_done()
                continue
            try:
                await self._run_job(job)
            finally:
                self._queue.task_done()

    async def _run_job(self, job: ImageJob) -> None:
        if job.cancel_requested:
            await self.cancel(job.job_id)
            return
        try:
            budget, device_mode = await self._wait_for_resources(job)
            if job.cancel_requested:
                await self.cancel(job.job_id)
                return
            job.started_at = datetime.now(UTC)
            await self._transition(
                job,
                status="running",
                phase="starting_comfyui",
                progress=max(job.progress, 0.12),
                message="Starting local ComfyUI image generation.",
                resource_mode=device_mode,
                paused_reason=None,
            )
            outputs = await self._adapter.generate(
                job=job,
                budget=budget,
                device_mode=device_mode,
                progress=lambda progress, phase, message: self._threadsafe_progress(job, progress, phase, message, device_mode),
            )
            job.output_paths = outputs
            await self._transition(
                job,
                status="completed",
                phase="completed",
                progress=1.0,
                message="Image generation completed.",
                resource_mode=device_mode,
            )
        except ImageGenerationServiceError as exc:
            if exc.code == "image_generation_cancelled":
                await self.cancel(job.job_id)
                return
            logger.warning(
                "Image generation job failed",
                extra={"job_id": job.job_id, "code": exc.code, "retryable": exc.retryable},
            )
            await self._transition(
                job,
                status="failed",
                phase="failed",
                progress=job.progress,
                message=exc.message,
                resource_mode="failed",
                error={"code": exc.code, "message": exc.message, "details": exc.details, "retryable": exc.retryable},
            )
        finally:
            self._vram.clear_cuda_cache()

    async def _wait_for_resources(self, job: ImageJob) -> tuple[ImagePresetBudget, str]:
        while True:
            if job.cancel_requested:
                raise ImageGenerationServiceError("Image generation was cancelled.", code="image_generation_cancelled")
            if job.user_paused:
                await self._transition(
                    job,
                    status="paused",
                    phase="user_paused",
                    progress=job.progress,
                    message="Image generation is paused.",
                    resource_mode="manual_pause",
                    paused_reason="Paused by user.",
                )
                await asyncio.sleep(self._settings.image_resource_poll_seconds)
                continue
            if tts_activity.is_active:
                await self._transition(
                    job,
                    status="paused",
                    phase="tts_priority_pause",
                    progress=job.progress,
                    message="Image generation is paused while Reverie is speaking.",
                    resource_mode="tts_priority",
                    paused_reason="TTS is active; voice always has priority over image generation.",
                )
                await asyncio.sleep(self._settings.image_resource_poll_seconds)
                continue

            snapshot = self._vram.snapshot()
            budget = self._select_budget(job.requested_preset, snapshot)
            if budget is not None:
                if budget.preset != job.effective_preset:
                    logger.info(
                        "Downgrading image preset for VRAM safety",
                        extra={
                            "job_id": job.job_id,
                            "requested_preset": job.requested_preset,
                            "effective_preset": budget.preset,
                            "free_vram_mb": snapshot.free_mb,
                        },
                    )
                job.effective_preset = budget.preset
                await self._transition(
                    job,
                    status="waiting_resources",
                    phase="resources_ready",
                    progress=max(job.progress, 0.1),
                    message="Resources are available; image generation can start.",
                    resource_mode="gpu_lowvram",
                    paused_reason=None,
                )
                return budget, "gpu_lowvram"

            if self._settings.image_allow_cpu_fallback:
                budget = self._budget_for("preview_8gb")
                job.effective_preset = "preview_8gb"
                await self._transition(
                    job,
                    status="waiting_resources",
                    phase="cpu_fallback",
                    progress=max(job.progress, 0.08),
                    message="VRAM is low; falling back to CPU/offload preview mode.",
                    resource_mode="cpu_fallback",
                    paused_reason=None,
                )
                return budget, "cpu_fallback"

            await self._transition(
                job,
                status="paused",
                phase="low_vram_pause",
                progress=job.progress,
                message="Image generation is paused until enough VRAM is free.",
                resource_mode="low_vram",
                paused_reason="Free VRAM is below the preview_8gb safety budget.",
            )
            await asyncio.sleep(self._settings.image_resource_poll_seconds)

    def _select_budget(self, requested: ImageQualityPreset, snapshot: VRAMSnapshot) -> ImagePresetBudget | None:
        requested_index = _PRESET_ORDER.index(requested)
        for preset in reversed(_PRESET_ORDER[: requested_index + 1]):
            budget = self._budget_for(preset)
            if not snapshot.is_known or (snapshot.free_mb is not None and snapshot.free_mb >= budget.min_free_vram_mb):
                return budget
        return None

    def _budget_for(self, preset: ImageQualityPreset) -> ImagePresetBudget:
        if preset == "high_8gb":
            return ImagePresetBudget(preset=preset, width=896, height=896, steps=24, cfg=3.5, min_free_vram_mb=self._settings.image_high_min_free_vram_mb, estimated_peak_vram_mb=5700)
        if preset == "balanced_8gb":
            return ImagePresetBudget(preset=preset, width=768, height=768, steps=18, cfg=3.0, min_free_vram_mb=self._settings.image_balanced_min_free_vram_mb, estimated_peak_vram_mb=4700)
        return ImagePresetBudget(preset=preset, width=512, height=512, steps=12, cfg=2.5, min_free_vram_mb=self._settings.image_preview_min_free_vram_mb, estimated_peak_vram_mb=3500)

    def _threadsafe_progress(self, job: ImageJob, progress: float, phase: str, message: str, resource_mode: str) -> None:
        loop = self._worker_task.get_loop() if self._worker_task is not None else None
        if loop is None:
            return
        coroutine = self._transition(
            job,
            status="running",
            phase=phase,
            progress=progress,
            message=message,
            resource_mode=resource_mode,
        )
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        if running_loop is loop:
            loop.create_task(coroutine)
            return
        future = asyncio.run_coroutine_threadsafe(coroutine, loop)
        future.result(timeout=2)

    async def _transition(
        self,
        job: ImageJob,
        *,
        status: ImageJobStatus,
        phase: str,
        progress: float,
        message: str,
        resource_mode: str,
        paused_reason: str | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        job.status = status
        job.phase = phase
        job.progress = min(max(progress, 0.0), 1.0)
        job.message = message
        job.resource_mode = resource_mode
        job.paused_reason = paused_reason
        job.error = error
        job.updated_at = datetime.now(UTC)
        if status in _TERMINAL_STATUSES:
            job.completed_at = job.updated_at
        await self._record_event(job, event=f"job.{status}", message=message)

    async def _record_event(self, job: ImageJob, *, event: str, message: str) -> None:
        job.sequence += 1
        payload = ImageJobEvent(
            event=event,
            job_id=job.job_id,
            sequence=job.sequence,
            timestamp=datetime.now(UTC).isoformat(),
            status=job.status,
            phase=job.phase,
            progress=job.progress,
            message=message,
            resource_mode=job.resource_mode,
            effective_preset=job.effective_preset,
            paused_reason=job.paused_reason,
            output_paths=list(job.output_paths),
            error=job.error,
        )
        job.events.append(payload)
        if len(job.events) > self._settings.image_job_event_history_limit:
            job.events = job.events[-self._settings.image_job_event_history_limit :]
        async with job.condition:
            job.condition.notify_all()

    def _job_or_error(self, job_id: str) -> ImageJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise ImageGenerationServiceError(
                "Image generation job was not found.",
                code="image_job_not_found",
                retryable=False,
                details={"job_id": job_id},
            )
        return job


_image_generation_service: ImageGenerationService | None = None


def get_image_generation_service(settings: Settings) -> ImageGenerationService:
    """Return the process-local image generation queue singleton."""

    global _image_generation_service
    if _image_generation_service is None or _image_generation_service._settings is not settings:
        _image_generation_service = ImageGenerationService(settings)
    return _image_generation_service
