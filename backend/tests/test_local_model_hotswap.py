"""Tests for local model hotswap helpers."""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.config import Settings
from app.services.local_model_hotswap import ComfyUICacheUnloader, OllamaModelUnloader


class FakeOllamaUnloader(OllamaModelUnloader):
    def __init__(self, settings: Settings, loaded_models: list[str] | None) -> None:
        super().__init__(settings)
        self.loaded_models = loaded_models
        self.payloads: list[dict[str, Any]] = []

    def _get_json(self, path: str) -> dict[str, Any]:
        assert path == "/api/ps"
        if self.loaded_models is None:
            raise RuntimeError("ps unavailable")
        return {"models": [{"name": name} for name in self.loaded_models]}

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        assert path == "/api/generate"
        self.payloads.append(payload)
        return {"done": True, "done_reason": "unload"}


class FakeComfyUnloader(ComfyUICacheUnloader):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.payloads: list[dict[str, Any]] = []

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        assert path == "/free"
        self.payloads.append(payload)
        return {}


def test_ollama_unloader_targets_loaded_configured_models_with_latest_alias() -> None:
    settings = Settings(
        _env_file=None,
        ollama_model="llama3.1:8b",
        memory_embedding_model="nomic-embed-text",
    )
    unloader = FakeOllamaUnloader(
        settings,
        loaded_models=["llama3.1:8b", "nomic-embed-text:latest", "other:latest"],
    )

    unloaded = asyncio.run(unloader.unload_for_image("image_generation_start"))

    assert unloaded == ["ollama:llama3.1:8b", "ollama:nomic-embed-text:latest"]
    assert unloader.payloads == [
        {"model": "llama3.1:8b", "keep_alive": 0},
        {"model": "nomic-embed-text:latest", "keep_alive": 0},
    ]


def test_ollama_unloader_falls_back_to_configured_models_when_ps_unavailable() -> None:
    settings = Settings(
        _env_file=None,
        ollama_model="llama3.1:8b",
        memory_embedding_model="nomic-embed-text",
    )
    unloader = FakeOllamaUnloader(settings, loaded_models=None)

    unloaded = asyncio.run(unloader.unload_for_image("image_generation_start"))

    assert unloaded == ["ollama:llama3.1:8b", "ollama:nomic-embed-text"]


def test_comfyui_unloader_posts_free_before_chat() -> None:
    settings = Settings(_env_file=None)
    unloader = FakeComfyUnloader(settings)

    unloaded = asyncio.run(unloader.unload_for_chat("chat_start"))

    assert unloaded == ["comfyui"]
    assert unloader.payloads == [{"unload_models": True, "free_memory": True}]


def test_hotswap_unloaders_respect_disabled_setting() -> None:
    settings = Settings(_env_file=None, local_ai_hotswap_enabled=False)
    ollama = FakeOllamaUnloader(settings, loaded_models=["llama3.1:8b"])
    comfy = FakeComfyUnloader(settings)

    assert asyncio.run(ollama.unload_for_image("image_generation_start")) == []
    assert asyncio.run(comfy.unload_for_chat("chat_start")) == []
    assert ollama.payloads == []
    assert comfy.payloads == []
