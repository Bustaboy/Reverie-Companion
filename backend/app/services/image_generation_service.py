"""Queued local image generation foundation with 8GB VRAM safety.

Resource budget (RTX 4070 laptop 8GB target):
feature: "in-chat image generation"
interactive_required: false
primary_gpu_models: ["ComfyUI Flux GGUF Q4/Q5 lowvram"]
peak_vram_mb_estimate: 4200-6200 depending preset
steady_vram_mb_estimate: 0 in Reverie process; ComfyUI owns model memory
cpu_ram_mb_estimate: 1500-6000 depending ComfyUI model/offload behavior
concurrency_limit: 1
fallbacks:
  - wait while TTS is active
  - wait/degrade preset when free VRAM is below budget
  - interrupt/requeue generation if TTS starts mid-job
  - request CPU fallback workflow metadata if no GPU snapshot is available/low
cleanup:
  - cancel ComfyUI prompt on cancellation/preemption
  - emit terminal event and drop no files from chat/TTS hot paths
telemetry:
  - log VRAM snapshots, fallback decisions, queue wait, ComfyUI failures
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
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
from app.services.image_prompt_engine import ImagePromptEngine
from app.services.resource_coordinator import (
    LocalResourceCoordinator,
    resource_coordinator,
)

logger = logging.getLogger(__name__)


class ImageGenerationError(Exception):
    """Recoverable image generation failure with user-facing metadata."""

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
class ImagePresetConfig:
    width: int
    height: int
    steps: int
    guidance: float
    min_free_vram_mb: int
    model_hint: str
    allow_cpu_fallback: bool = True


PRESET_ORDER = [
    ImageQualityPreset.preview_8gb,
    ImageQualityPreset.balanced_8gb,
    ImageQualityPreset.high_8gb,
]

PRESET_CONFIGS: dict[ImageQualityPreset, ImagePresetConfig] = {
    ImageQualityPreset.preview_8gb: ImagePresetConfig(
        width=512,
        height=512,
        steps=12,
        guidance=3.0,
        min_free_vram_mb=2800,
        model_hint="flux1-dev-q4_0.gguf lowvram preview",
    ),
    ImageQualityPreset.balanced_8gb: ImagePresetConfig(
        width=768,
        height=768,
        steps=20,
        guidance=3.5,
        min_free_vram_mb=4200,
        model_hint="flux1-dev-q4_k_m.gguf lowvram balanced",
    ),
    ImageQualityPreset.high_8gb: ImagePresetConfig(
        width=896,
        height=896,
        steps=28,
        guidance=4.0,
        min_free_vram_mb=5600,
        model_hint="flux1-dev-q5_k_m.gguf lowvram high",
    ),
}

TERMINAL_STATUSES = {
    ImageJobStatus.completed,
    ImageJobStatus.failed,
    ImageJobStatus.cancelled,
}


@dataclass(frozen=True)
class ImageOutputReference:
    """Safe, job-attached image output resolution for the API layer."""

    output_path: str
    local_path: Path | None
    comfyui_view_url: str | None


@dataclass
class ImageJob:
    job_id: str
    prompt: str
    negative_prompt: str
    context: dict[str, Any] | None
    requested_preset: ImageQualityPreset
    active_preset: ImageQualityPreset
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: ImageJobStatus = ImageJobStatus.queued
    progress: float = 0.0
    phase: str = "queued"
    message: str = "Image job is queued."
    output_paths: list[str] = field(default_factory=list)
    error: dict[str, Any] | None = None
    fallback_used: bool = False
    resource_mode: str = "queued"
    vram_free_mb: int | None = None
    vram_required_mb: int | None = None
    sequence: int = 0
    cancel_requested: bool = False
    comfy_prompt_id: str | None = None
    events: list[ImageJobEvent] = field(default_factory=list)
    watchers: set[asyncio.Queue[ImageJobEvent]] = field(default_factory=set)

    def to_read(self) -> ImageJobRead:
        return ImageJobRead(
            job_id=self.job_id,
            status=self.status,
            prompt=self.prompt,
            negative_prompt=self.negative_prompt,
            requested_preset=self.requested_preset,
            active_preset=self.active_preset,
            created_at=self.created_at,
            updated_at=self.updated_at,
            progress=self.progress,
            phase=self.phase,
            message=self.message,
            output_paths=list(self.output_paths),
            error=self.error,
            fallback_used=self.fallback_used,
            resource_mode=self.resource_mode,
            vram_free_mb=self.vram_free_mb,
            vram_required_mb=self.vram_required_mb,
        )


class ComfyUIFluxAdapter:
    """Minimal ComfyUI HTTP adapter for Flux GGUF lowvram workflows."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.image_generation_comfyui_url.rstrip("/")

    async def generate(self, job: ImageJob, preset: ImagePresetConfig) -> list[str]:
        """Submit a conservative Flux GGUF workflow and wait for completion."""

        client_id = f"reverie-{job.job_id}"
        workflow = self._build_flux_workflow(job, preset)
        prompt_response = await asyncio.to_thread(
            self._post_json,
            "/prompt",
            {"prompt": workflow, "client_id": client_id},
        )
        prompt_id = str(prompt_response.get("prompt_id") or "")
        if not prompt_id:
            raise ImageGenerationError(
                "ComfyUI did not return a prompt ID.",
                code="image_comfy_prompt_rejected",
                retryable=True,
            )
        job.comfy_prompt_id = prompt_id
        deadline = (
            asyncio.get_running_loop().time()
            + self._settings.image_generation_comfy_timeout_seconds
        )
        while asyncio.get_running_loop().time() < deadline:
            history = await asyncio.to_thread(self._get_json, f"/history/{prompt_id}")
            if prompt_id in history:
                return self._extract_output_paths(history[prompt_id])
            await asyncio.sleep(1.0)
        raise ImageGenerationError(
            "ComfyUI image generation timed out.",
            code="image_comfy_timeout",
            retryable=True,
            details={"prompt_id": prompt_id},
        )

    async def interrupt(self) -> None:
        """Ask ComfyUI to stop the active prompt so TTS can take priority."""

        try:
            await asyncio.to_thread(self._post_json, "/interrupt", {})
        except ImageGenerationError:
            logger.info("ComfyUI interrupt was unavailable or rejected")

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._open_json(request)

    def _get_json(self, path: str) -> dict[str, Any]:
        request = urllib.request.Request(f"{self._base_url}{path}", method="GET")
        return self._open_json(request)

    def _open_json(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(
                request, timeout=10.0
            ) as response:  # noqa: S310 - local ComfyUI URL from settings.
                return json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.URLError as exc:
            raise ImageGenerationError(
                "Local ComfyUI is not reachable. Start ComfyUI with --lowvram and Flux GGUF models, then retry.",
                code="image_comfy_unreachable",
                retryable=True,
                details={"url": self._base_url},
            ) from exc
        except (json.JSONDecodeError, TimeoutError) as exc:
            raise ImageGenerationError(
                "ComfyUI returned an unreadable response.",
                code="image_comfy_bad_response",
                retryable=True,
            ) from exc

    def _build_flux_workflow(
        self, job: ImageJob, preset: ImagePresetConfig
    ) -> dict[str, Any]:
        # This foundation keeps workflow metadata explicit and conservative. Users
        # can map these class_type names to their installed Flux GGUF ComfyUI nodes
        # without Reverie importing diffusion libraries or holding model memory.
        return {
            "1": {
                "class_type": "ReverieFluxGGUFLowVRAMConfig",
                "inputs": {
                    "model_hint": preset.model_hint,
                    "lowvram": True,
                    "batch_size": 1,
                    "cpu_fallback": self._settings.image_generation_cpu_fallback,
                },
            },
            "2": {
                "class_type": "ReveriePrompt",
                "inputs": {
                    "text": job.prompt,
                    "negative_text": job.negative_prompt,
                    "context": job.context or {},
                    "seed": 0,
                    "width": preset.width,
                    "height": preset.height,
                    "steps": preset.steps,
                    "guidance": preset.guidance,
                },
            },
            "3": {
                "class_type": "ReverieSaveImage",
                "inputs": {"filename_prefix": f"reverie_{job.job_id}"},
            },
        }

    def _extract_output_paths(self, history_entry: dict[str, Any]) -> list[str]:
        outputs: list[str] = []
        for node_output in (history_entry.get("outputs") or {}).values():
            for image in (
                node_output.get("images", []) if isinstance(node_output, dict) else []
            ):
                filename = image.get("filename")
                if filename:
                    outputs.append(str(filename))
        return outputs


class ImageGenerationService:
    """Queued, TTS-preemptible local image generation workflow service."""

    def __init__(
        self,
        settings: Settings,
        *,
        coordinator: LocalResourceCoordinator = resource_coordinator,
        adapter: ComfyUIFluxAdapter | None = None,
        prompt_engine: ImagePromptEngine | None = None,
    ) -> None:
        self._settings = settings
        self._coordinator = coordinator
        self._adapter = adapter or ComfyUIFluxAdapter(settings)
        self._prompt_engine = prompt_engine or ImagePromptEngine()
        self._jobs: dict[str, ImageJob] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue(
            maxsize=settings.image_generation_max_queue_size
        )
        self._worker_task: asyncio.Task[None] | None = None
        Path(settings.image_generation_output_dir).mkdir(parents=True, exist_ok=True)

    async def submit(self, request: ImageGenerateRequest) -> ImageJobRead:
        self._ensure_worker()
        if self._queue.full():
            raise ImageGenerationError(
                "The local image queue is full. Please wait for a current job to finish.",
                code="image_queue_full",
                retryable=True,
            )
        job_id = f"img_{uuid4().hex}"
        context = (
            request.context.model_dump(mode="json")
            if hasattr(request.context, "model_dump")
            else request.context
        )
        normalized_context = context if isinstance(context, dict) else None
        engineered = self._prompt_engine.build(
            prompt=request.prompt,
            context=normalized_context,
            negative_prompt=request.negative_prompt,
        )
        enriched_context = dict(normalized_context or {})
        enriched_context["image_prompt_engine"] = {
            "style_notes": engineered.style_notes,
            "framing_notes": engineered.framing_notes,
            "detected_scene_tags": engineered.detected_scene_tags,
            "deterministic": True,
        }
        job = ImageJob(
            job_id=job_id,
            prompt=engineered.prompt,
            negative_prompt=engineered.negative_prompt,
            context=enriched_context,
            requested_preset=request.quality_preset,
            active_preset=request.quality_preset,
        )
        self._jobs[job_id] = job
        self._emit(
            job, event="job.queued", message="Image job queued behind chat and TTS."
        )
        await self._queue.put(job_id)
        return job.to_read()

    def get_job(self, job_id: str) -> ImageJobRead:
        return self._require_job(job_id).to_read()

    def get_output_reference(
        self, job_id: str, output_index: int
    ) -> ImageOutputReference:
        """Resolve a generated image output by index without allowing arbitrary file access.

        The public route intentionally accepts an output index, not a filesystem
        path. The index must point at an output path already attached to the job
        by ComfyUI completion metadata. Local files are served only when the
        resolved path stays inside the configured image output directory;
        otherwise the route can redirect to ComfyUI's /view endpoint for that
        same attached output.
        """

        job = self._require_job(job_id)
        if output_index < 0 or output_index >= len(job.output_paths):
            raise ImageGenerationError(
                "Image output was not found for that job.",
                code="image_output_not_found",
                retryable=False,
                details={"job_id": job_id, "output_index": output_index},
            )

        output_path = job.output_paths[output_index]
        return ImageOutputReference(
            output_path=output_path,
            local_path=self._resolve_local_output_path(output_path),
            comfyui_view_url=self._build_comfyui_view_url(output_path),
        )

    async def cancel(self, job_id: str) -> ImageJobRead:
        job = self._require_job(job_id)
        job.cancel_requested = True
        if job.status == ImageJobStatus.running:
            await self._adapter.interrupt()
        if job.status not in TERMINAL_STATUSES:
            self._update(
                job,
                status=ImageJobStatus.cancelled,
                phase="cancelled",
                progress=job.progress,
                message="Image job cancelled.",
            )
        return job.to_read()

    async def events(self, job_id: str):
        job = self._require_job(job_id)
        queue: asyncio.Queue[ImageJobEvent] = asyncio.Queue(maxsize=100)
        for event in job.events[-50:]:
            await queue.put(event)
        job.watchers.add(queue)
        try:
            while True:
                event = await queue.get()
                yield event
                if event.status in TERMINAL_STATUSES:
                    break
        finally:
            job.watchers.discard(queue)

    def _resolve_local_output_path(self, output_path: str) -> Path | None:
        output_root = Path(self._settings.image_generation_output_dir).resolve()
        relative_output = self._relative_output_path(output_path)
        if not relative_output:
            return None

        candidate = Path(relative_output)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (output_root / candidate).resolve()
        try:
            resolved.relative_to(output_root)
        except ValueError:
            return None
        return resolved if resolved.is_file() else None

    def _relative_output_path(self, output_path: str) -> str | None:
        parsed = urllib.parse.urlsplit(output_path.strip())
        if parsed.scheme and parsed.scheme != "file":
            return None
        query = urllib.parse.parse_qs(parsed.query)
        filename = (query.get("filename") or [""])[0].strip()
        subfolder = (query.get("subfolder") or [""])[0].strip().strip("/\\")
        if filename:
            return str(Path(subfolder) / filename) if subfolder else filename
        path = urllib.parse.unquote(parsed.path).strip()
        return path or None

    def _build_comfyui_view_url(self, output_path: str) -> str | None:
        parsed = urllib.parse.urlsplit(output_path.strip())
        if parsed.scheme in {"http", "https"}:
            return output_path
        if parsed.scheme == "file":
            return None

        query = urllib.parse.parse_qs(parsed.query)
        relative_output = self._relative_output_path(output_path)
        if not relative_output:
            return None
        relative_path = Path(relative_output)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            return None
        params = {
            "filename": (query.get("filename") or [relative_path.name])[0],
            "type": (query.get("type") or ["output"])[0],
        }
        subfolder = (query.get("subfolder") or [""])[0].strip().strip("/\\")
        if not subfolder and relative_path.parent != Path("."):
            subfolder = relative_path.parent.as_posix()
        if subfolder:
            params["subfolder"] = subfolder
        return f"{self._settings.image_generation_comfyui_url.rstrip('/')}/view?{urllib.parse.urlencode(params)}"

    def _ensure_worker(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(
                self._worker(), name="reverie-image-generation-worker"
            )

    async def _worker(self) -> None:
        while True:
            job_id = await self._queue.get()
            try:
                await self._run_job(self._jobs[job_id])
            except Exception as exc:  # pragma: no cover - defensive worker guard.
                logger.exception(
                    "Unhandled image worker failure",
                    extra={"job_id": job_id, "error": str(exc)},
                )
                job = self._jobs.get(job_id)
                if job and job.status not in TERMINAL_STATUSES:
                    self._fail(
                        job,
                        code="image_worker_error",
                        message="Unexpected local image worker error.",
                        retryable=True,
                    )
            finally:
                self._queue.task_done()

    async def _run_job(self, job: ImageJob) -> None:
        if job.cancel_requested:
            self._update(
                job,
                status=ImageJobStatus.cancelled,
                phase="cancelled",
                message="Image job cancelled before start.",
            )
            return
        async with self._coordinator.image_job_section(job_id=job.job_id):
            await self._wait_for_safe_resources(job)
            if job.cancel_requested:
                self._update(
                    job,
                    status=ImageJobStatus.cancelled,
                    phase="cancelled",
                    message="Image job cancelled before generation.",
                )
                return
            await self._attempt_generation_with_tts_preemption(job)

    async def _wait_for_safe_resources(self, job: ImageJob) -> None:
        while True:
            if job.cancel_requested:
                return
            if self._coordinator.tts_active:
                self._update(
                    job,
                    status=ImageJobStatus.paused,
                    phase="tts_priority",
                    resource_mode="paused_for_tts",
                    message="Paused while Reverie is speaking; TTS has priority over image generation.",
                )
                await self._coordinator.wait_for_tts_idle()
                self._update(
                    job,
                    status=ImageJobStatus.waiting_for_resources,
                    phase="resource_check",
                    resource_mode="checking",
                    message="TTS finished; checking VRAM before resuming image generation.",
                )
            snapshot = self._coordinator.snapshot_vram()
            preset = self._select_safe_preset(job, snapshot.free_mb)
            required = PRESET_CONFIGS[preset].min_free_vram_mb
            job.vram_free_mb = snapshot.free_mb
            job.vram_required_mb = required
            if (
                snapshot.free_mb is None
                and self._settings.image_generation_allow_unknown_vram
            ):
                if job.active_preset != ImageQualityPreset.preview_8gb:
                    job.active_preset = ImageQualityPreset.preview_8gb
                    job.fallback_used = True
                self._update(
                    job,
                    status=ImageJobStatus.waiting_for_resources,
                    phase="resource_check",
                    resource_mode="unknown_vram_preview",
                    progress=0.05,
                    message="VRAM telemetry is unavailable; using the preview 8GB preset for safety.",
                )
                return
            if snapshot.free_mb is not None and snapshot.free_mb >= required:
                if preset != job.active_preset:
                    job.active_preset = preset
                    job.fallback_used = True
                self._update(
                    job,
                    status=ImageJobStatus.waiting_for_resources,
                    phase="resource_ready",
                    resource_mode="vram_ready",
                    progress=0.08,
                    message="Image resources are available; starting queued generation.",
                )
                return
            self._update(
                job,
                status=ImageJobStatus.waiting_for_resources,
                phase="low_vram",
                resource_mode="waiting_for_vram",
                progress=0.03,
                message="Waiting for enough free VRAM before starting image generation.",
            )
            await asyncio.sleep(self._settings.image_generation_resume_poll_seconds)

    def _select_safe_preset(
        self, job: ImageJob, free_vram_mb: int | None
    ) -> ImageQualityPreset:
        requested_index = PRESET_ORDER.index(job.requested_preset)
        if free_vram_mb is None:
            return ImageQualityPreset.preview_8gb
        settings_floor = self._settings.image_generation_min_free_vram_mb
        for preset in reversed(PRESET_ORDER[: requested_index + 1]):
            required = max(
                PRESET_CONFIGS[preset].min_free_vram_mb,
                settings_floor if preset == ImageQualityPreset.preview_8gb else 0,
            )
            if free_vram_mb >= required:
                return preset
        return ImageQualityPreset.preview_8gb

    async def _attempt_generation_with_tts_preemption(self, job: ImageJob) -> None:
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            if job.cancel_requested:
                self._update(
                    job,
                    status=ImageJobStatus.cancelled,
                    phase="cancelled",
                    message="Image job cancelled.",
                )
                return
            preset = PRESET_CONFIGS[job.active_preset]
            self._update(
                job,
                status=ImageJobStatus.running,
                phase="comfyui_generation",
                resource_mode="exclusive_media",
                progress=0.15,
                message=f"Generating local image with {job.active_preset.value}.",
            )
            generation_task = asyncio.create_task(self._adapter.generate(job, preset))
            monitor_task = asyncio.create_task(self._monitor_tts_preemption(job))
            done, pending = await asyncio.wait(
                {generation_task, monitor_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            if monitor_task in done:
                monitor_result = monitor_task.result()
                if monitor_result == "cancelled":
                    generation_task.cancel()
                    await self._adapter.interrupt()
                    self._update(
                        job,
                        status=ImageJobStatus.cancelled,
                        phase="cancelled",
                        message="Image job cancelled.",
                    )
                    return
                if monitor_result == "preempted":
                    generation_task.cancel()
                    await self._adapter.interrupt()
                    self._update(
                        job,
                        status=ImageJobStatus.paused,
                        phase="tts_preempted",
                        resource_mode="paused_for_tts",
                        progress=job.progress,
                        message="Image generation paused so TTS can speak first.",
                    )
                    await self._wait_for_safe_resources(job)
                    continue
            try:
                outputs = generation_task.result()
            except asyncio.CancelledError:
                if attempt < max_attempts:
                    continue
                raise
            except ImageGenerationError as exc:
                self._fail(
                    job,
                    code=exc.code,
                    message=exc.message,
                    retryable=exc.retryable,
                    details=exc.details,
                )
                return
            except RuntimeError as exc:
                if "out of memory" in str(exc).lower() or "oom" in str(exc).lower():
                    job.active_preset = ImageQualityPreset.preview_8gb
                    job.fallback_used = True
                    self._update(
                        job,
                        status=ImageJobStatus.paused,
                        phase="oom_fallback",
                        resource_mode="degraded",
                        progress=0.10,
                        message="GPU memory was tight; retrying once with the preview 8GB preset.",
                    )
                    continue
                self._fail(
                    job,
                    code="image_runtime_failed",
                    message="Local image generation failed.",
                    retryable=True,
                )
                return
            self._update(
                job,
                status=ImageJobStatus.completed,
                phase="completed",
                resource_mode="complete",
                progress=1.0,
                message="Image generation completed.",
                output_paths=outputs,
            )
            return
        self._fail(
            job,
            code="image_preempted_or_oom",
            message="Image generation could not complete safely under current local resource pressure.",
            retryable=True,
        )

    async def _monitor_tts_preemption(self, job: ImageJob) -> str:
        while job.status == ImageJobStatus.running:
            if job.cancel_requested:
                return "cancelled"
            if self._coordinator.tts_active:
                return "preempted"
            await asyncio.sleep(0.25)
        return "done"

    def _require_job(self, job_id: str) -> ImageJob:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise ImageGenerationError(
                "Image job was not found.",
                code="image_job_not_found",
                retryable=False,
                details={"job_id": job_id},
            ) from exc

    def _fail(
        self,
        job: ImageJob,
        *,
        code: str,
        message: str,
        retryable: bool,
        details: dict[str, object] | None = None,
    ) -> None:
        self._update(
            job,
            status=ImageJobStatus.failed,
            phase="failed",
            resource_mode="failed",
            message=message,
            error={
                "code": code,
                "message": message,
                "details": details or {},
                "retryable": retryable,
            },
        )

    def _update(
        self,
        job: ImageJob,
        *,
        status: ImageJobStatus | None = None,
        phase: str | None = None,
        progress: float | None = None,
        message: str | None = None,
        resource_mode: str | None = None,
        output_paths: list[str] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        if status is not None:
            job.status = status
        if phase is not None:
            job.phase = phase
        if progress is not None:
            job.progress = max(0.0, min(1.0, progress))
        if message is not None:
            job.message = message
        if resource_mode is not None:
            job.resource_mode = resource_mode
        if output_paths is not None:
            job.output_paths = output_paths
        if error is not None:
            job.error = error
        self._emit(job, event=f"job.{job.status.value}", message=job.message)

    def _emit(self, job: ImageJob, *, event: str, message: str) -> None:
        job.updated_at = datetime.now(timezone.utc)
        job.sequence += 1
        payload = ImageJobEvent(
            event=event,
            job_id=job.job_id,
            sequence=job.sequence,
            status=job.status,
            phase=job.phase,
            progress=job.progress,
            message=message,
            resource_mode=job.resource_mode,
            output_paths=list(job.output_paths),
            error=job.error,
            fallback_used=job.fallback_used,
            vram_free_mb=job.vram_free_mb,
            vram_required_mb=job.vram_required_mb,
        )
        job.events.append(payload)
        for watcher in list(job.watchers):
            try:
                watcher.put_nowait(payload)
            except asyncio.QueueFull:
                job.watchers.discard(watcher)


_image_service: ImageGenerationService | None = None


def get_image_generation_service(settings: Settings) -> ImageGenerationService:
    """Return the process-local image queue service."""

    global _image_service
    if _image_service is None or _image_service._settings is not settings:
        _image_service = ImageGenerationService(settings)
    return _image_service
