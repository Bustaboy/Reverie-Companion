from app.services.resource_coordinator import (
    LocalResourceCoordinator,
    ResourcePressureLevel,
    VRAMSnapshot,
)


def test_resource_coordinator_recommends_preview_and_piper_under_high_pressure():
    coordinator = LocalResourceCoordinator()
    decision = coordinator.evaluate_vram_for_workload(
        workload="image_generation",
        required_free_mb=2800,
        snapshot=VRAMSnapshot(free_mb=1200, total_mb=8192, used_mb=6992, source="test"),
    )

    assert decision.level == ResourcePressureLevel.high
    assert decision.can_start is False
    assert decision.should_downgrade is True
    assert decision.should_unload_optional_models is True
    assert decision.recommended_image_preset == "preview_8gb"
    assert decision.recommended_tts_backend == "piper"


def test_resource_coordinator_allows_balanced_quality_with_headroom():
    coordinator = LocalResourceCoordinator()
    decision = coordinator.evaluate_vram_for_workload(
        workload="image_generation",
        required_free_mb=4200,
        snapshot=VRAMSnapshot(free_mb=5200, total_mb=8192, used_mb=2992, source="test"),
    )

    assert decision.level == ResourcePressureLevel.normal
    assert decision.can_start is True
    assert decision.should_downgrade is False
    assert decision.recommended_image_preset == "balanced_8gb"
    assert decision.recommended_tts_backend == "orpheus"


def test_resource_coordinator_unknown_telemetry_uses_conservative_defaults():
    coordinator = LocalResourceCoordinator()
    decision = coordinator.evaluate_vram_for_workload(
        workload="status",
        snapshot=VRAMSnapshot(
            free_mb=None, total_mb=None, used_mb=None, source="unavailable"
        ),
    )

    assert decision.level == ResourcePressureLevel.unknown
    assert decision.can_start is True
    assert decision.should_downgrade is True
    assert decision.recommended_image_preset == "preview_8gb"
