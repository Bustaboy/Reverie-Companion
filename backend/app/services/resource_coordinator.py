"""Shared local resource coordination for 8GB-safe AI workloads.

The coordinator is intentionally dependency-light. It gives TTS a process-wide
priority signal, exposes best-effort VRAM snapshots, and centralizes the
pressure policy used by chat-adjacent media queues. The thresholds reserve
headroom for RTX 4070-class 8GB laptop GPUs where desktop compositors, driver
fragmentation, and transient kernels can consume hundreds of MiB outside
Reverie's direct control.
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import importlib.util
import logging
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from typing import AsyncIterator

logger = logging.getLogger(__name__)


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

    @property
    def used_ratio(self) -> float | None:
        if not self.total_mb or self.used_mb is None:
            return None
        return self.used_mb / self.total_mb


class ResourcePressureLevel(StrEnum):
    """User-facing resource pressure buckets for 8GB hardware."""

    unknown = "unknown"
    normal = "normal"
    elevated = "elevated"
    high = "high"
    critical = "critical"


@dataclass(frozen=True)
class ResourceDecision:
    """Policy result for a local GPU-adjacent workload."""

    level: ResourcePressureLevel
    can_start: bool
    should_downgrade: bool
    should_unload_optional_models: bool
    recommended_image_preset: str
    recommended_tts_backend: str
    message: str
    snapshot: VRAMSnapshot
    required_free_mb: int | None = None


class LocalResourceCoordinator:
    """Coordinate TTS priority and media jobs under strict 8GB constraints."""

    # Product-level guardrails for 8GB cards: keep normal work below ~7.5GB and
    # treat the last 500-750MiB as emergency headroom for compositor/driver
    # spikes. These are deliberately conservative because optional media should
    # degrade before chat or speech becomes unstable.
    WARNING_FREE_MB = 3000
    HIGH_PRESSURE_FREE_MB = 1800
    CRITICAL_FREE_MB = 750
    HEADROOM_MB = 500

    def __init__(self) -> None:
        self._condition = asyncio.Condition()
        self._active_tts = 0
        self._active_image_jobs = 0

    @property
    def tts_active(self) -> bool:
        return self._active_tts > 0

    @property
    def active_image_jobs(self) -> int:
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

    def evaluate_vram_for_workload(
        self,
        *,
        workload: str,
        required_free_mb: int | None = None,
        snapshot: VRAMSnapshot | None = None,
    ) -> ResourceDecision:
        """Return a conservative start/degrade decision for a local workload."""

        current = snapshot or self.snapshot_vram()
        level = self._pressure_level(current)
        recommended_image_preset = self._recommended_image_preset(current)
        recommended_tts_backend = (
            "piper"
            if level in {ResourcePressureLevel.high, ResourcePressureLevel.critical}
            else "orpheus"
        )
        should_unload = level in {
            ResourcePressureLevel.high,
            ResourcePressureLevel.critical,
        }
        can_start = level != ResourcePressureLevel.critical
        should_downgrade = level in {
            ResourcePressureLevel.elevated,
            ResourcePressureLevel.high,
            ResourcePressureLevel.critical,
        }

        if current.free_mb is None:
            can_start = required_free_mb is None
            should_downgrade = True
            recommended_image_preset = "preview_8gb"
            recommended_tts_backend = "orpheus"
            message = "VRAM telemetry is unavailable; Reverie will use conservative 8GB-safe fallbacks."
            return ResourceDecision(
                level=level,
                can_start=can_start,
                should_downgrade=should_downgrade,
                should_unload_optional_models=False,
                recommended_image_preset=recommended_image_preset,
                recommended_tts_backend=recommended_tts_backend,
                message=message,
                snapshot=current,
                required_free_mb=required_free_mb,
            )

        if required_free_mb is not None:
            required_with_headroom = required_free_mb + self.HEADROOM_MB
            can_start = can_start and current.free_mb >= required_with_headroom
            should_downgrade = (
                should_downgrade or current.free_mb < required_with_headroom
            )

        message = self._pressure_message(level, current, workload)
        return ResourceDecision(
            level=level,
            can_start=can_start,
            should_downgrade=should_downgrade,
            should_unload_optional_models=should_unload,
            recommended_image_preset=recommended_image_preset,
            recommended_tts_backend=recommended_tts_backend,
            message=message,
            snapshot=current,
            required_free_mb=required_free_mb,
        )

    def _pressure_level(self, snapshot: VRAMSnapshot) -> ResourcePressureLevel:
        if snapshot.free_mb is None or snapshot.total_mb is None:
            return ResourcePressureLevel.unknown
        used_ratio = snapshot.used_ratio or 0.0
        if snapshot.free_mb < self.CRITICAL_FREE_MB or used_ratio >= 0.92:
            return ResourcePressureLevel.critical
        if snapshot.free_mb < self.HIGH_PRESSURE_FREE_MB or used_ratio >= 0.82:
            return ResourcePressureLevel.high
        if snapshot.free_mb < self.WARNING_FREE_MB or used_ratio >= 0.72:
            return ResourcePressureLevel.elevated
        return ResourcePressureLevel.normal

    def _recommended_image_preset(self, snapshot: VRAMSnapshot) -> str:
        if snapshot.free_mb is None:
            return "preview_8gb"
        if snapshot.free_mb >= 6100:
            return "high_8gb"
        if snapshot.free_mb >= 4700:
            return "balanced_8gb"
        return "preview_8gb"

    def _pressure_message(
        self, level: ResourcePressureLevel, snapshot: VRAMSnapshot, workload: str
    ) -> str:
        free = snapshot.free_mb
        if level == ResourcePressureLevel.normal:
            return "Local GPU resources look healthy for Reverie's 8GB profile."
        if level == ResourcePressureLevel.elevated:
            return f"VRAM is getting busy ({free} MiB free); optional media may use preview quality."
        if level == ResourcePressureLevel.high:
            return f"VRAM pressure is high ({free} MiB free); Reverie will prefer speech/chat and downgrade background media."
        if level == ResourcePressureLevel.critical:
            return f"VRAM is critically low ({free} MiB free); optional {workload} work should wait or fall back."
        return "VRAM telemetry is unavailable; Reverie will use conservative 8GB-safe fallbacks."

    def _snapshot_with_torch(self) -> VRAMSnapshot | None:
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
