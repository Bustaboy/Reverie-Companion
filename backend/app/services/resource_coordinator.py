"""Shared local resource coordination for 8GB-safe AI workloads.

The coordinator is intentionally small and dependency-light. It gives TTS a
process-wide priority signal and exposes best-effort VRAM snapshots for media
queues without forcing torch or NVIDIA tooling to be installed at startup.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import subprocess
from dataclasses import dataclass
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


class LocalResourceCoordinator:
    """Coordinate TTS priority and media jobs under strict 8GB constraints."""

    def __init__(self) -> None:
        self._condition = asyncio.Condition()
        self._active_tts = 0
        self._active_image_jobs = 0

    @property
    def tts_active(self) -> bool:
        return self._active_tts > 0

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
