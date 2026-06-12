"""API coverage for local image generation job routes."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.api.routes.images import get_images_service
from app.main import app
from app.models.image import ImageJobRead


class FakeImageService:
    def __init__(self) -> None:
        self.job = ImageJobRead(
            job_id="img_test",
            status="queued",
            requested_preset="preview_8gb",
            effective_preset="preview_8gb",
            progress=0.0,
            phase="queued",
            message="Image generation is queued.",
            created_at="2026-06-12T10:00:00+00:00",
            updated_at="2026-06-12T10:00:00+00:00",
            resource_mode="queued",
        )
        self.request = None

    async def submit(self, request):
        self.request = request
        return self.job

    def get_job(self, job_id: str):
        assert job_id == self.job.job_id
        return self.job

    async def cancel(self, job_id: str):
        assert job_id == self.job.job_id
        self.job = self.job.model_copy(
            update={
                "status": "cancelled",
                "phase": "cancelled",
                "message": "Image generation was cancelled.",
                "resource_mode": "cancelled",
            }
        )
        return self.job


class ImageApiTests(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_generate_image_queues_job(self) -> None:
        fake_service = FakeImageService()
        app.dependency_overrides[get_images_service] = lambda: fake_service
        client = TestClient(app)

        response = client.post(
            "/api/images/generate",
            json={
                "prompt": "warm local preview portrait",
                "context": {"character_id": "tara", "scene_tags": ["cozy"]},
                "quality_preset": "preview_8gb",
            },
        )

        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["job"]["job_id"], "img_test")
        self.assertIsNotNone(fake_service.request)
        self.assertEqual(fake_service.request.prompt, "warm local preview portrait")
        self.assertEqual(fake_service.request.quality_preset, "preview_8gb")

    def test_cancel_image_job_returns_cancelled_state(self) -> None:
        fake_service = FakeImageService()
        app.dependency_overrides[get_images_service] = lambda: fake_service
        client = TestClient(app)

        response = client.post("/api/images/img_test/cancel")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
