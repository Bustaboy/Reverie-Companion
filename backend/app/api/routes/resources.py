"""Local resource diagnostics for 8GB-safe feature degradation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.services.resource_coordinator import resource_coordinator

router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.get("/status")
async def get_resource_status() -> dict[str, Any]:
    """Return GPU pressure and workload priority without logging private data."""

    return resource_coordinator.resource_status().to_dict()
