"""Shared local resource coordination for 8GB-safe AI workloads.

The coordinator is intentionally dependency-light. It gives TTS a process-wide
priority signal, exposes best-effort VRAM snapshots, and provides a small
pressure model so every heavy subsystem degrades before the GPU reaches OOM.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import AsyncIterator

logger = logging.getLogger(__name__)


class ResourcePressure(StrEnum):
    """User-facing local resource pressure levels for 8GB hardware."""

    unknown = "unknown"
    normal = "normal"
    elevated = "elevated"
    critical = "critical"


@dataclass(frozen=True)
class VRAMSnapshot:
    """Best-effort GPU memory snapshot in MiB."""

    free_mb: int | None
    total_mb: int | None
    used_mb: int | None
    source: str

    @property
    def available(self) -> bool:
        return self.free_mb is not None and self.total_mb is not None


@dataclass(frozen=True)
class ResourceStatus:
    """Compact status shared with queues and UI diagnostics."""

    pressure: ResourcePressure
    snapshot: VRAMSnapshot
    tts_active: bool
    image_jobs_active: int
    warning: str | None
    recommended_action: str
    headroom_mb: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "pressure": self.pressure.value,
            "vram": {
                "free_mb": self.snapshot.free_mb,
                "used_mb": self.snapshot.used_mb,
                "total_mb": self.snapshot.total_mb,
                "source": self.snapshot.source,
                "available": self.snapshot.available,
            },
            "tts_active": self.tts_active,
            "image_jobs_active": self.image_jobs_active,
            "warning": self.warning,
            "recommended_action": self.recommended_action,
            "headroom_mb": self.headroom_mb,
        }


AuxiliaryUnloadCallback = Callable[[str], None]


class LocalResourceCoordinator:
    """Coordinate TTS priority and media jobs under strict 8GB constraints."""

    def __init__(
        self,
        *,
        warning_free_vram_mb: int = 2200,
        critical_free_vram_mb: int = 1200,
        target_headroom_mb: int = 768,
    ) -> None:
        self._condition = asyncio.Condition()
        self._active_tts = 0
        self._active_image_jobs = 0
        self._warning_free_vram_mb = warning_free_vram_mb
        self._critical_free_vram_mb = critical_free_vram_mb
        self._target_headroom_mb = target_headroom_mb
        self._auxiliary_unload_callbacks: dict[str, AuxiliaryUnloadCallback] = {}

    @property
    def tts_active(self) -> bool:
        return self._active_tts > 0

    @property
    def image_jobs_active(self) -> int:
        return self._active_image_jobs

    async def wait_for_tts_idle(self) -> None:
        """Block low-priority work until all active TTS requests finish."""

        async with self._condition:
            await self._condition.wait_for(lambda: self._active_tts == 0)

    @contextlib.asynccontextmanager
    async def tts_priority_section(
        self, *, request_id: str | None = None
    ) -> AsyncIterator[None]:
        """Mark Orpheus/Piper synthesis as active so media work pauses."""

        async with self._condition:
            self._active_tts += 1
            self._condition.notify_all()
        logger.debug("TTS priority section entered", extra={"request_id": request_id})
        try:
            yield
        finally:
            async with self._condition:
                self._active_tts = max(0, self._active_tts - 1)
                self._condition.notify_all()
            logger.debug(
                "TTS priority section exited", extra={"request_id": request_id}
            )

    @contextlib.asynccontextmanager
    async def image_job_section(self, *, job_id: str) -> AsyncIterator[None]:
        """Track one exclusive image job for diagnostics."""

        async with self._condition:
            self._active_image_jobs += 1
            self._condition.notify_all()
        try:
            yield
        finally:
            async with self._condition:
                self._active_image_jobs = max(0, self._active_image_jobs - 1)
                self._condition.notify_all()

    def register_auxiliary_unloader(
        self, name: str, callback: AuxiliaryUnloadCallback
    ) -> None:
        """Register an idempotent model/cache unload callback.

        TTS services use this to let exclusive media jobs release an idle Orpheus
        model before ComfyUI starts. Callbacks must not unload active work.
        """

        self._auxiliary_unload_callbacks[name] = callback

    def unregister_auxiliary_unloader(self, name: str) -> None:
        self._auxiliary_unload_callbacks.pop(name, None)

    def unload_auxiliary_models(self, reason: str) -> list[str]:
        """Best-effort idle-model unload used before exclusive media work."""

        unloaded: list[str] = []
        if self.tts_active:
            return unloaded
        for name, callback in list(self._auxiliary_unload_callbacks.items()):
            try:
                callback(reason)
                unloaded.append(name)
            except Exception:  # pragma: no cover - defensive cleanup path.
                logger.exception(
                    "Auxiliary model unload callback failed",
                    extra={"name": name, "reason": reason},
                )
        if unloaded:
            logger.info(
                "Unloaded auxiliary models for local resource headroom",
                extra={"reason": reason, "models": unloaded},
            )
        return unloaded

    def snapshot_vram(self) -> VRAMSnapshot:
        """Return a best-effort VRAM snapshot without mandatory GPU deps."""

        torch_snapshot = self._snapshot_with_torch()
        if torch_snapshot is not None:
            return torch_snapshot
        nvidia_smi_snapshot = self._snapshot_with_nvidia_smi()
        if nvidia_smi_snapshot is not None:
            return nvidia_smi_snapshot
        return VRAMSnapshot(
            free_mb=None, total_mb=None, used_mb=None, source="unavailable"
        )

    def resource_status(self, *, reserved_mb: int = 0) -> ResourceStatus:
        """Return proactive pressure/warning information for 8GB-safe queues."""

        snapshot = self.snapshot_vram()
        pressure = ResourcePressure.unknown
        warning: str | None = None
        recommended_action = "Use conservative 8GB defaults until telemetry is available."
        headroom_mb = None
        if snapshot.free_mb is not None:
            headroom_mb = snapshot.free_mb - reserved_mb
            if headroom_mb <= self._critical_free_vram_mb:
                pressure = ResourcePressure.critical
                warning = "GPU memory is critically low. Reverie will pause background media and use preview presets."
                recommended_action = "Pause image generation, unload idle models, or wait for the active voice/chat request to finish."
            elif headroom_mb <= self._warning_free_vram_mb:
                pressure = ResourcePressure.elevated
                warning = "GPU memory is getting tight. Reverie is protecting headroom to avoid a crash."
                recommended_action = "Use preview image quality and balanced context until pressure drops."
            else:
                pressure = ResourcePressure.normal
                recommended_action = "Normal 8GB operation; exclusive media should still run one job at a time."

        return ResourceStatus(
            pressure=pressure,
            snapshot=snapshot,
            tts_active=self.tts_active,
            image_jobs_active=self.image_jobs_active,
            warning=warning,
            recommended_action=recommended_action,
            headroom_mb=headroom_mb,
        )

    def _snapshot_with_torch(self) -> VRAMSnapshot | None:
        try:
            import torch  # type: ignore[import-not-found]
        except ImportError:
            return None
        if not torch.cuda.is_available():
            return None
        free_bytes, total_bytes = torch.cuda.mem_get_info()
        free_mb = int(free_bytes // (1024 * 1024))
        total_mb = int(total_bytes // (1024 * 1024))
        return VRAMSnapshot(
            free_mb=free_mb,
            total_mb=total_mb,
            used_mb=max(0, total_mb - free_mb),
            source="torch.cuda.mem_get_info",
        )

    def _snapshot_with_nvidia_smi(self) -> VRAMSnapshot | None:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.free,memory.total,memory.used",
                    "--format=csv,noheader,nounits",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=2.0,
            )
        except (FileNotFoundError, subprocess.SubprocessError, TimeoutError):
            return None
        first_line = (
            result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
        )
        try:
            free_mb, total_mb, used_mb = (
                int(part.strip()) for part in first_line.split(",")[:3]
            )
        except ValueError:
            return None
        return VRAMSnapshot(
            free_mb=free_mb, total_mb=total_mb, used_mb=used_mb, source="nvidia-smi"
        )


resource_coordinator = LocalResourceCoordinator()
