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
import re
import shutil
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
    ImageHistoryItem,
    ImageHistoryResponse,
    ImageJobEvent,
    ImageJobRead,
    ImageJobStatus,
    ImageQualityPreset,
    ImageSaveToAssetsResponse,
)
from app.services.image_prompt_engine import ImagePromptEngine
from app.services.resource_coordinator import (
    LocalResourceCoordinator,
    ResourcePressure,
    ResourceStatus,
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

IMAGE_HISTORY_SCHEMA_VERSION = 2
CHARACTER_ASSET_MANIFEST_VERSION = 2
CAPTURE_ASSET_EXPORT_SCHEMA_VERSION = "capture_asset_export.v1"


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
    conversation_id: str
    source: str | None
    source_message_id: str | None
    character_id: str | None
    session_id: str | None
    moment_capture_id: str | None
    scene_summary: str | None
    prompt_hash: str | None
    feedback_status: str
    review_status: str
    canon_status: str
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
    pressure: str = "unknown"
    warning: str | None = None
    sequence: int = 0
    cancel_requested: bool = False
    comfy_prompt_id: str | None = None
    saved_to_assets: bool = False
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
            pressure=self.pressure,
            warning=self.warning,
            conversation_id=self.conversation_id,
            source=self.source,
            source_message_id=self.source_message_id,
            character_id=self.character_id,
            session_id=self.session_id,
            moment_capture_id=self.moment_capture_id,
            scene_summary=self.scene_summary,
            prompt_hash=self.prompt_hash,
            feedback_status=self.feedback_status,
            review_status=self.review_status,
            canon_status=self.canon_status,
            saved_to_assets=self.saved_to_assets,
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
        self._history_path = Path(settings.image_generation_history_path)
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        self._history: dict[str, ImageHistoryItem] = self._load_history()
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
        metadata_v2 = self._image_metadata_from_context(enriched_context)
        job = ImageJob(
            job_id=job_id,
            prompt=engineered.prompt,
            negative_prompt=engineered.negative_prompt,
            context=enriched_context,
            conversation_id=request.conversation_id,
            source=request.source,
            source_message_id=request.source_message_id,
            character_id=metadata_v2.get("character_id"),
            session_id=metadata_v2.get("session_id"),
            moment_capture_id=metadata_v2.get("moment_capture_id"),
            scene_summary=metadata_v2.get("scene_summary"),
            prompt_hash=metadata_v2.get("prompt_hash"),
            feedback_status=metadata_v2.get("feedback_status", "pending"),
            review_status=metadata_v2.get("review_status", "unreviewed"),
            canon_status=metadata_v2.get("canon_status", "not_requested"),
            requested_preset=request.quality_preset,
            active_preset=request.quality_preset,
        )
        self._jobs[job_id] = job
        self._emit(
            job,
            event="job.queued",
            message=self._capture_message(
                job,
                "Moment Capture queued behind chat and voice.",
                "Image job queued behind chat and TTS.",
            ),
        )
        await self._queue.put(job_id)
        return job.to_read()

    def get_job(self, job_id: str) -> ImageJobRead:
        return self._require_job(job_id).to_read()

    def list_history(
        self,
        conversation_id: str | None = "default",
        *,
        character_id: str | None = None,
        include_deleted: bool = False,
    ) -> ImageHistoryResponse:
        items = [
            item
            for item in self._history.values()
            if (conversation_id is None or item.conversation_id == conversation_id)
            and (character_id is None or item.character_id == character_id)
            and (include_deleted or not item.is_deleted)
        ]
        items.sort(key=lambda item: item.completed_at, reverse=True)
        return ImageHistoryResponse(items=items)

    async def delete_history_item(self, job_id: str) -> ImageHistoryResponse:
        item = self._history.get(job_id)
        if item is None:
            raise ImageGenerationError(
                "Image was not found in this gallery.",
                code="image_history_not_found",
                retryable=False,
                details={"job_id": job_id},
            )
        tombstone = item.model_copy(
            update={
                "is_deleted": True,
                "deleted_at": datetime.now(timezone.utc),
                "feedback_status": "deleted",
                "review_status": "deleted",
                "output_paths": [],
                "thumbnail_paths": [],
                "metadata": {
                    **item.metadata,
                    "deleted": True,
                    "deleted_at": datetime.now(timezone.utc).isoformat(),
                },
            }
        )
        self._history[job_id] = tombstone
        try:
            self._write_history(raise_on_error=True)
        except ImageGenerationError:
            self._history[job_id] = item
            raise
        job = self._jobs.get(job_id)
        if job is not None:
            job.output_paths = []
        return self.list_history(item.conversation_id)

    async def save_to_character_assets(
        self,
        job_id: str,
        *,
        character_id: str,
        output_index: int = 0,
        asset_label: str | None = None,
    ) -> ImageSaveToAssetsResponse:
        item = self._require_history_item(job_id)
        reference = self.get_output_reference(job_id, output_index)
        if reference.local_path is None:
            raise ImageGenerationError(
                "This image is not available as a local file yet, so it cannot be saved to character assets.",
                code="image_asset_source_unavailable",
                retryable=True,
                details={"job_id": job_id, "output_index": output_index},
            )
        safe_character_id = self._safe_slug(character_id)
        asset_dir = (
            Path(self._settings.character_assets_dir)
            / safe_character_id
            / "assets"
            / "images"
        )
        asset_dir.mkdir(parents=True, exist_ok=True)
        extension = reference.local_path.suffix or ".png"
        asset_path = asset_dir / f"{job_id}_{output_index}{extension}"
        shutil.copy2(reference.local_path, asset_path)
        manifest_path = asset_dir.parent / "manifest.json"
        manifest = self._normalize_character_asset_manifest(
            self._read_json_file(manifest_path, default={}),
            character_id=safe_character_id,
        )
        asset_entry = self._build_character_asset_manifest_entry(
            item=item,
            asset_path=asset_path,
            manifest_path=manifest_path,
            output_index=output_index,
            asset_label=asset_label,
            character_id=safe_character_id,
        )
        images = [
            image
            for image in manifest.get("images", [])
            if not (
                image.get("job_id") == job_id
                and image.get("output_index") == output_index
            )
        ]
        images.append(asset_entry)
        manifest.update(
            {
                "schema_version": CHARACTER_ASSET_MANIFEST_VERSION,
                "character_id": safe_character_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "images": sorted(
                    images,
                    key=lambda image: str(image.get("saved_at", "")),
                    reverse=True,
                ),
            }
        )
        try:
            self._write_json_file(manifest_path, manifest)
        except OSError as exc:
            raise ImageGenerationError(
                "Reverie copied the image but could not update the character asset manifest. Check local file permissions and try again.",
                code="image_asset_manifest_write_failed",
                retryable=True,
                details={"manifest_path": str(manifest_path)},
            ) from exc
        updated = item.model_copy(
            update={
                "character_id": item.character_id or safe_character_id,
                "saved_to_assets": True,
                "asset_manifest_path": str(manifest_path),
                "metadata": {
                    **item.metadata,
                    "last_saved_asset_path": str(asset_path),
                    "last_saved_asset_id": asset_entry["asset_id"],
                },
            }
        )
        self._history[job_id] = updated
        if job_id in self._jobs:
            self._jobs[job_id].saved_to_assets = True
        self._write_history(raise_on_error=True)
        return ImageSaveToAssetsResponse(
            item=updated, asset_path=str(asset_path), manifest_path=str(manifest_path)
        )

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

        output_paths = self._output_paths_for_job_or_history(job_id)
        if output_index < 0 or output_index >= len(output_paths):
            raise ImageGenerationError(
                "Image output was not found for that job.",
                code="image_output_not_found",
                retryable=False,
                details={"job_id": job_id, "output_index": output_index},
            )

        output_path = output_paths[output_index]
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
                message=self._capture_message(
                    job,
                    "Moment Capture cancelled. Capture metadata was preserved for retry.",
                    "Image job cancelled.",
                ),
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
                message=self._capture_message(
                    job,
                    "Moment Capture cancelled before rendering. Capture metadata was preserved for retry.",
                    "Image job cancelled before start.",
                ),
            )
            return
        async with self._coordinator.image_job_section(job_id=job.job_id):
            unloaded = self._unload_idle_auxiliary_models("image_generation_start")
            if unloaded:
                self._update(
                    job,
                    status=ImageJobStatus.waiting_for_resources,
                    phase="unloaded_auxiliary_models",
                    resource_mode="freeing_headroom",
                    progress=0.04,
                    message="Released idle voice models before image generation to protect 8GB VRAM headroom.",
                )
            await self._wait_for_safe_resources(job)
            if job.cancel_requested:
                self._update(
                    job,
                    status=ImageJobStatus.cancelled,
                    phase="cancelled",
                    message=self._capture_message(
                        job,
                        "Moment Capture cancelled before rendering. Capture metadata was preserved for retry.",
                        "Image job cancelled before generation.",
                    ),
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
                    message=self._capture_message(
                        job,
                        "Moment Capture paused while Reverie is speaking; TTS has priority.",
                        "Paused while Reverie is speaking; TTS has priority over image generation.",
                    ),
                )
                await self._coordinator.wait_for_tts_idle()
                self._update(
                    job,
                    status=ImageJobStatus.waiting_for_resources,
                    phase="resource_check",
                    resource_mode="checking",
                    message=self._capture_message(
                        job,
                        "Voice finished; checking VRAM before resuming Moment Capture.",
                        "TTS finished; checking VRAM before resuming image generation.",
                    ),
                )
            status = self._resource_status()
            snapshot = status.snapshot
            preset = self._select_safe_preset(job, snapshot.free_mb)
            required = PRESET_CONFIGS[preset].min_free_vram_mb
            job.vram_free_mb = snapshot.free_mb
            job.vram_required_mb = required
            job.pressure = status.pressure.value
            job.warning = status.warning
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
                    message=self._capture_message(
                        job,
                        "VRAM telemetry is unavailable; Moment Capture is using the preview preset for safety.",
                        "VRAM telemetry is unavailable; using the preview 8GB preset for safety.",
                    ),
                )
                return
            if (
                snapshot.free_mb is not None
                and snapshot.free_mb >= required
                and status.pressure != ResourcePressure.critical
            ):
                if preset != job.active_preset:
                    job.active_preset = preset
                    job.fallback_used = True
                self._update(
                    job,
                    status=ImageJobStatus.waiting_for_resources,
                    phase="resource_ready",
                    resource_mode="vram_ready",
                    progress=0.08,
                    message=self._capture_message(
                        job,
                        "Resources are available; starting queued Moment Capture.",
                        "Image resources are available; starting queued generation.",
                    ),
                )
                return
            self._update(
                job,
                status=ImageJobStatus.waiting_for_resources,
                phase="low_vram",
                resource_mode="waiting_for_vram",
                progress=0.03,
                message=status.warning
                or self._capture_message(
                    job,
                    "Waiting for enough free VRAM before starting Moment Capture.",
                    "Waiting for enough free VRAM before starting image generation.",
                ),
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
            status = self._resource_status(
                reserved_mb=PRESET_CONFIGS[job.active_preset].min_free_vram_mb
            )
            if (
                status.pressure == ResourcePressure.critical
                and job.active_preset != ImageQualityPreset.preview_8gb
            ):
                job.active_preset = ImageQualityPreset.preview_8gb
                job.fallback_used = True
                self._update(
                    job,
                    status=ImageJobStatus.paused,
                    phase="critical_vram_downgrade",
                    resource_mode="degraded",
                    progress=0.10,
                    message=status.warning
                    or self._capture_message(
                        job,
                        "VRAM is tight; downgrading Moment Capture to preview quality.",
                        "VRAM is tight; downgrading image generation to preview quality.",
                    ),
                )
            preset = PRESET_CONFIGS[job.active_preset]
            self._update(
                job,
                status=ImageJobStatus.running,
                phase="comfyui_generation",
                resource_mode="exclusive_media",
                progress=0.15,
                message=self._capture_message(
                    job,
                    f"Rendering Moment Capture with {job.active_preset.value}.",
                    f"Generating local image with {job.active_preset.value}.",
                ),
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
                if monitor_result == "critical_vram":
                    generation_task.cancel()
                    await self._adapter.interrupt()
                    job.active_preset = ImageQualityPreset.preview_8gb
                    job.fallback_used = True
                    self._update(
                        job,
                        status=ImageJobStatus.paused,
                        phase="critical_vram_preempted",
                        resource_mode="degraded",
                        progress=job.progress,
                        message="GPU memory became critically low, so Reverie paused image generation and switched to preview quality.",
                    )
                    await self._wait_for_safe_resources(job)
                    continue
                if monitor_result == "preempted":
                    generation_task.cancel()
                    await self._adapter.interrupt()
                    self._update(
                        job,
                        status=ImageJobStatus.paused,
                        phase="tts_preempted",
                        resource_mode="paused_for_tts",
                        progress=job.progress,
                        message=self._capture_message(
                            job,
                            "Moment Capture paused so TTS can speak first.",
                            "Image generation paused so TTS can speak first.",
                        ),
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
                        message=self._capture_message(
                            job,
                            "GPU memory was tight; retrying Moment Capture once with the preview 8GB preset.",
                            "GPU memory was tight; retrying once with the preview 8GB preset.",
                        ),
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
                message=self._capture_message(
                    job,
                    "Moment Capture image completed.",
                    "Image generation completed.",
                ),
                output_paths=outputs,
            )
            self._record_history_item(job)
            return
        self._fail(
            job,
            code="image_preempted_or_oom",
            message=self._capture_message(
                job,
                "Moment Capture could not complete safely under current local resource pressure.",
                "Image generation could not complete safely under current local resource pressure.",
            ),
            retryable=True,
        )

    async def _monitor_tts_preemption(self, job: ImageJob) -> str:
        while job.status == ImageJobStatus.running:
            if job.cancel_requested:
                return "cancelled"
            if self._coordinator.tts_active:
                return "preempted"
            status = self._resource_status()
            job.vram_free_mb = status.snapshot.free_mb
            job.pressure = status.pressure.value
            job.warning = status.warning
            if status.pressure == ResourcePressure.critical:
                return "critical_vram"
            await asyncio.sleep(0.25)
        return "done"

    def _resource_status(self, *, reserved_mb: int = 0) -> ResourceStatus:
        if hasattr(self._coordinator, "resource_status"):
            return self._coordinator.resource_status(reserved_mb=reserved_mb)
        snapshot = self._coordinator.snapshot_vram()
        pressure = ResourcePressure.unknown
        warning = None
        headroom_mb = None
        if snapshot.free_mb is not None:
            headroom_mb = snapshot.free_mb - reserved_mb
            pressure = (
                ResourcePressure.normal
                if headroom_mb > 1200
                else ResourcePressure.critical
            )
            if pressure == ResourcePressure.critical:
                warning = "GPU memory is critically low; Reverie is waiting before starting image generation."
        return ResourceStatus(
            pressure=pressure,
            snapshot=snapshot,
            tts_active=self._coordinator.tts_active,
            image_jobs_active=0,
            warning=warning,
            recommended_action="Use preview image quality until local resource pressure drops.",
            headroom_mb=headroom_mb,
        )

    def _unload_idle_auxiliary_models(self, reason: str) -> list[str]:
        if hasattr(self._coordinator, "unload_auxiliary_models"):
            return self._coordinator.unload_auxiliary_models(reason)
        return []

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

    def _capture_message(
        self, job: ImageJob, capture_message: str, image_message: str
    ) -> str:
        return (
            capture_message
            if job.moment_capture_id or job.source == "moment_capture"
            else image_message
        )

    def _safe_failure_details(
        self, job: ImageJob, details: dict[str, object] | None
    ) -> dict[str, object]:
        safe_keys = {
            "url",
            "prompt_id",
            "history_path",
            "manifest_path",
            "job_id",
            "output_index",
            "backend",
        }
        safe_details = {
            key: value
            for key, value in (details or {}).items()
            if key in safe_keys
            and isinstance(value, str | int | float | bool | type(None))
        }
        safe_details["debug"] = {
            "job_id": job.job_id,
            "source": job.source,
            "conversation_id": job.conversation_id,
            "source_message_id": job.source_message_id,
            "capture_id": job.moment_capture_id,
            "character_id": job.character_id,
            "session_id": job.session_id,
            "prompt_hash": job.prompt_hash,
            "requested_preset": job.requested_preset.value,
            "active_preset": job.active_preset.value,
            "resource_mode": job.resource_mode,
            "pressure": job.pressure,
            "vram_free_mb": job.vram_free_mb,
            "vram_required_mb": job.vram_required_mb,
        }
        return safe_details

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
                "details": self._safe_failure_details(job, details),
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
        if job.warning and not error:
            logger.info(
                "Image job running under resource pressure",
                extra={
                    "job_id": job.job_id,
                    "pressure": job.pressure,
                    "warning": job.warning,
                },
            )
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
            pressure=job.pressure,
            warning=job.warning,
            conversation_id=job.conversation_id,
            source=job.source,
            source_message_id=job.source_message_id,
            character_id=job.character_id,
            session_id=job.session_id,
            moment_capture_id=job.moment_capture_id,
            scene_summary=job.scene_summary,
            prompt_hash=job.prompt_hash,
            feedback_status=job.feedback_status,
            review_status=job.review_status,
            canon_status=job.canon_status,
            saved_to_assets=job.saved_to_assets,
        )
        job.events.append(payload)
        for watcher in list(job.watchers):
            try:
                watcher.put_nowait(payload)
            except asyncio.QueueFull:
                job.watchers.discard(watcher)

    def _output_paths_for_job_or_history(self, job_id: str) -> list[str]:
        job = self._jobs.get(job_id)
        if job is not None:
            return job.output_paths
        item = self._history.get(job_id)
        if item is not None:
            return item.output_paths
        raise ImageGenerationError(
            "Image job was not found.",
            code="image_job_not_found",
            retryable=False,
            details={"job_id": job_id},
        )

    def _require_history_item(self, job_id: str) -> ImageHistoryItem:
        item = self._history.get(job_id)
        if item is not None:
            return item
        job = self._jobs.get(job_id)
        if job is not None and job.status == ImageJobStatus.completed:
            self._record_history_item(job)
            return self._history[job_id]
        raise ImageGenerationError(
            "Image was not found in this gallery.",
            code="image_history_not_found",
            retryable=False,
            details={"job_id": job_id},
        )

    def _record_history_item(self, job: ImageJob) -> None:
        if not job.output_paths:
            return
        metadata_v2 = self._history_metadata_from_job(job)
        item = ImageHistoryItem(
            job_id=job.job_id,
            conversation_id=job.conversation_id,
            source=job.source,
            source_message_id=job.source_message_id,
            character_id=metadata_v2.get("character_id"),
            session_id=metadata_v2.get("session_id"),
            moment_capture_id=metadata_v2.get("moment_capture_id"),
            scene_summary=metadata_v2.get("scene_summary"),
            prompt_hash=metadata_v2.get("prompt_hash"),
            feedback_status=metadata_v2.get("feedback_status", "pending"),
            review_status=metadata_v2.get("review_status", "unreviewed"),
            canon_status=metadata_v2.get("canon_status", "not_requested"),
            prompt=job.prompt,
            prompt_summary=metadata_v2.get("prompt_summary")
            or self._summarize_prompt(job.prompt),
            negative_prompt=job.negative_prompt,
            requested_preset=job.requested_preset,
            active_preset=job.active_preset,
            created_at=job.created_at,
            completed_at=job.updated_at,
            output_paths=list(job.output_paths),
            thumbnail_paths=list(job.output_paths[:1]),
            fallback_used=job.fallback_used,
            saved_to_assets=job.saved_to_assets,
            metadata={
                **metadata_v2,
                "resource_mode": job.resource_mode,
                "vram_free_mb": job.vram_free_mb,
                "vram_required_mb": job.vram_required_mb,
                "8gb_note": "Stored metadata only; images stay lazy-loaded by URL.",
            },
        )
        self._history[job.job_id] = item
        self._write_history()

    def _history_metadata_from_job(self, job: ImageJob) -> dict[str, Any]:
        metadata = self._image_metadata_from_context(job.context or {})
        metadata.update(
            {
                "character_id": job.character_id,
                "session_id": job.session_id,
                "moment_capture_id": job.moment_capture_id,
                "scene_summary": job.scene_summary,
                "prompt_hash": job.prompt_hash,
                "feedback_status": job.feedback_status,
                "review_status": job.review_status,
                "canon_status": job.canon_status,
            }
        )
        return metadata

    def _image_metadata_from_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Extract stable image metadata once for jobs, events, and history.

        Gallery metadata v2 should not exist only at persistence time: active job
        reads and SSE events need the same character/capture context so API
        consumers can connect an in-flight image to its companion moment before
        it lands in history. Keep this adapter small and deterministic so legacy
        generic jobs simply expose nullable metadata fields.
        """
        capture = (
            context.get("moment_capture")
            if isinstance(context.get("moment_capture"), dict)
            else {}
        )
        character = (
            context.get("character")
            if isinstance(context.get("character"), dict)
            else {}
        )
        scene_state = (
            capture.get("scene_state")
            if isinstance(capture.get("scene_state"), dict)
            else {}
        )
        scene_bits = [
            scene_state.get("location"),
            scene_state.get("time_of_day"),
            scene_state.get("mood") or scene_state.get("emotional_tone"),
            scene_state.get("pose"),
            scene_state.get("outfit"),
        ]
        scene_summary = " · ".join(str(bit) for bit in scene_bits if bit) or None
        return {
            "character_id": capture.get("character_id") or character.get("id"),
            "character_name": character.get("name"),
            "session_id": capture.get("session_id"),
            "moment_capture_id": capture.get("capture_id"),
            "source_turn_index": capture.get("source_turn_index"),
            "scene_summary": scene_summary,
            "scene_state": scene_state or None,
            "prompt_hash": capture.get("prompt_hash"),
            "prompt_summary": capture.get("capture_intent"),
            "feedback_status": "pending",
            "review_status": "unreviewed",
            "canon_status": "not_requested",
            "capture_status": "from_moment_capture" if capture else "generated",
        }

    def _load_history(self) -> dict[str, ImageHistoryItem]:
        raw = self._read_json_file(self._history_path, default={})
        raw_items: list[Any]
        if isinstance(raw, list):
            raw_items = raw
        elif isinstance(raw, dict) and isinstance(raw.get("items"), list):
            raw_items = raw["items"]
        elif isinstance(raw, dict) and isinstance(raw.get("conversations"), dict):
            raw_items = []
            for conversation_items in raw["conversations"].values():
                if isinstance(conversation_items, list):
                    raw_items.extend(conversation_items)
        else:
            raw_items = []

        items: dict[str, ImageHistoryItem] = {}
        skipped_count = 0
        for value in raw_items:
            try:
                item = ImageHistoryItem.model_validate(value)
            except Exception:
                skipped_count += 1
                continue
            items[item.job_id] = item
        if skipped_count:
            logger.warning(
                "Skipped unreadable image history items",
                extra={"count": skipped_count, "path": str(self._history_path)},
            )
        return items

    def _write_history(self, *, raise_on_error: bool = False) -> None:
        items = sorted(
            self._history.values(), key=lambda item: item.completed_at, reverse=True
        )
        conversations: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            conversations.setdefault(item.conversation_id, []).append(
                item.model_dump(mode="json")
            )
        payload = {
            "schema_version": IMAGE_HISTORY_SCHEMA_VERSION,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "conversations": conversations,
            # Keep a flat list for compatibility with PR #80-era builds and
            # lightweight external tooling that only knows about `items`.
            "items": [item.model_dump(mode="json") for item in items],
        }
        try:
            self._write_json_file(self._history_path, payload)
        except OSError as exc:
            logger.warning(
                "Could not persist image history metadata",
                extra={"path": str(self._history_path), "error": str(exc)},
            )
            if raise_on_error:
                raise ImageGenerationError(
                    "Reverie could not save the image gallery metadata. The image job is safe, but the gallery needs writable local storage.",
                    code="image_history_write_failed",
                    retryable=True,
                    details={"history_path": str(self._history_path)},
                ) from exc

    def _read_json_file(self, path: Path, *, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not read JSON metadata file",
                extra={"path": str(path), "error": str(exc)},
            )
            return default

    def _write_json_file(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            temp_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
            )
            temp_path.replace(path)
        finally:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                logger.debug("Could not remove temporary JSON metadata file")

    def _normalize_character_asset_manifest(
        self, manifest: Any, *, character_id: str
    ) -> dict[str, Any]:
        if not isinstance(manifest, dict):
            manifest = {}
        images = manifest.get("images")
        if not isinstance(images, list):
            images = []
        schema_version = manifest.get("schema_version")
        if not isinstance(schema_version, int):
            schema_version = CHARACTER_ASSET_MANIFEST_VERSION
        return {
            **manifest,
            "schema_version": schema_version,
            "character_id": str(manifest.get("character_id") or character_id),
            "images": [
                image
                for image in images
                if isinstance(image, dict)
                and self._is_safe_manifest_relative_path(image.get("path"))
            ],
        }

    def _build_character_asset_manifest_entry(
        self,
        *,
        item: ImageHistoryItem,
        asset_path: Path,
        manifest_path: Path,
        output_index: int,
        asset_label: str | None,
        character_id: str,
    ) -> dict[str, Any]:
        try:
            manifest_relative_path = asset_path.relative_to(manifest_path.parent)
            path_for_manifest = manifest_relative_path.as_posix()
        except ValueError:
            raise ImageGenerationError(
                "Character asset paths must stay inside the local character asset manifest directory.",
                code="image_asset_path_unsafe",
                retryable=False,
                details={
                    "asset_path": str(asset_path),
                    "manifest_path": str(manifest_path),
                },
            )
        if not self._is_safe_manifest_relative_path(path_for_manifest):
            raise ImageGenerationError(
                "Character asset paths must be relative, local-only paths.",
                code="image_asset_path_unsafe",
                retryable=False,
                details={"asset_path": path_for_manifest},
            )
        asset_id = f"image:{item.job_id}:{output_index}"
        capture_id = item.moment_capture_id or item.job_id
        character_id = self._safe_slug(item.character_id or character_id)
        created_at = item.completed_at.isoformat()
        feedback_state = {
            "status": item.feedback_status,
            "review_status": item.review_status,
        }
        canon_state = {
            "status": item.canon_status,
        }
        return {
            "asset_id": asset_id,
            "capture_id": capture_id,
            "character_id": character_id,
            "job_id": item.job_id,
            "conversation_id": item.conversation_id,
            "source": item.source,
            "source_message_id": item.source_message_id,
            "feedback_state": feedback_state,
            "canon_state": canon_state,
            "output_index": output_index,
            "label": asset_label or item.prompt_summary,
            "path": path_for_manifest,
            "created_at": created_at,
            "source_prompt": item.prompt,
            "negative_prompt": item.negative_prompt,
            "prompt_summary": item.prompt_summary,
            "requested_preset": item.requested_preset.value,
            "active_preset": item.active_preset.value,
            "fallback_used": item.fallback_used,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            # M5-P10 compatibility metadata only. Full character import/export
            # belongs to M6-P09; full app backup/export/import belongs to
            # M8-P04. Keep this shape serializable, relative-path-only, and
            # local-first so those future flows can reuse it without copying
            # large binaries unless the user explicitly saved the capture here.
            "export": {
                "schema_version": CAPTURE_ASSET_EXPORT_SCHEMA_VERSION,
                "kind": "character_capture_asset",
                "asset_id": asset_id,
                "capture_id": capture_id,
                "character_id": character_id,
                "source_message_id": item.source_message_id,
                "path": path_for_manifest,
                "created_at": created_at,
                "feedback_state": feedback_state,
                "canon_state": canon_state,
            },
        }

    def _is_safe_manifest_relative_path(self, value: Any) -> bool:
        if not isinstance(value, str) or not value.strip():
            return False
        candidate = Path(value)
        return (
            not candidate.is_absolute()
            and ".." not in candidate.parts
            and "\\" not in value
            and "://" not in value
        )

    def _safe_slug(self, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip()).strip(".-_").lower()
        return slug or "default"

    def _summarize_prompt(self, prompt: str) -> str:
        normalized = " ".join(prompt.split())
        return normalized if len(normalized) <= 96 else f"{normalized[:93].rstrip()}..."


_image_service: ImageGenerationService | None = None


def get_image_generation_service(settings: Settings) -> ImageGenerationService:
    """Return the process-local image queue service."""

    global _image_service
    if _image_service is None or _image_service._settings is not settings:
        _image_service = ImageGenerationService(settings)
    return _image_service
