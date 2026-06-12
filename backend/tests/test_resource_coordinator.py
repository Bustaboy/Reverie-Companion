"""Tests for local 8GB resource pressure coordination."""

from app.services.resource_coordinator import LocalResourceCoordinator, ResourcePressure, VRAMSnapshot


class StaticCoordinator(LocalResourceCoordinator):
    def __init__(self, snapshot: VRAMSnapshot) -> None:
        super().__init__(warning_free_vram_mb=2200, critical_free_vram_mb=1200)
        self._snapshot = snapshot

    def snapshot_vram(self) -> VRAMSnapshot:
        return self._snapshot


def test_resource_status_marks_elevated_pressure() -> None:
    coordinator = StaticCoordinator(VRAMSnapshot(free_mb=1800, total_mb=8192, used_mb=6392, source="test"))

    status = coordinator.resource_status()

    assert status.pressure == ResourcePressure.elevated
    assert status.warning is not None
    assert status.headroom_mb == 1800


def test_resource_status_accounts_for_reserved_headroom() -> None:
    coordinator = StaticCoordinator(VRAMSnapshot(free_mb=4800, total_mb=8192, used_mb=3392, source="test"))

    status = coordinator.resource_status(reserved_mb=4000)

    assert status.pressure == ResourcePressure.critical
    assert status.headroom_mb == 800


def test_auxiliary_unload_skips_active_tts() -> None:
    coordinator = StaticCoordinator(VRAMSnapshot(free_mb=4800, total_mb=8192, used_mb=3392, source="test"))
    called: list[str] = []
    coordinator.register_auxiliary_unloader("orpheus", lambda reason: called.append(reason))
    coordinator._active_tts = 1

    unloaded = coordinator.unload_auxiliary_models("image_generation_start")

    assert unloaded == []
    assert called == []
