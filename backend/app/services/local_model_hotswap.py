"""Best-effort local model cache cleanup for 8GB GPU hotswapping."""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.request
from typing import Any

from app.core.config import Settings

logger = logging.getLogger(__name__)


class OllamaModelUnloader:
    """Unload idle Ollama models before exclusive image generation."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.ollama_host.rstrip("/")
        self._timeout = settings.local_ai_hotswap_timeout_seconds

    async def unload_for_image(self, reason: str) -> list[str]:
        if (
            not self._settings.local_ai_hotswap_enabled
            or not self._settings.local_ai_unload_ollama_before_images
        ):
            return []
        return await asyncio.to_thread(self._unload_for_image_sync, reason)

    def _unload_for_image_sync(self, reason: str) -> list[str]:
        targets = self._target_loaded_models()
        unloaded: list[str] = []
        for model in targets:
            try:
                self._post_json("/api/generate", {"model": model, "keep_alive": 0})
            except Exception as exc:  # pragma: no cover - local backend dependent.
                logger.info(
                    "Ollama model unload skipped",
                    extra={"model": model, "reason": reason, "error": str(exc)},
                )
                continue
            unloaded.append(f"ollama:{model}")
        if unloaded:
            logger.info(
                "Unloaded Ollama models before image generation",
                extra={"reason": reason, "models": unloaded},
            )
        return unloaded

    def _target_loaded_models(self) -> list[str]:
        configured = self._configured_models()
        if not configured:
            return []
        loaded = self._loaded_models()
        if loaded is None:
            return configured

        targets: list[str] = []
        for loaded_name in loaded:
            if any(self._same_model_name(loaded_name, name) for name in configured):
                targets.append(loaded_name)
        return self._unique(targets)

    def _configured_models(self) -> list[str]:
        return self._unique(
            [
                self._settings.ollama_model,
                self._settings.memory_embedding_model,
                self._settings.memory_llm_model or "",
            ]
        )

    def _loaded_models(self) -> list[str] | None:
        try:
            response = self._get_json("/api/ps")
        except Exception:  # pragma: no cover - local backend dependent.
            return None
        models = response.get("models")
        if not isinstance(models, list):
            return None
        names: list[str] = []
        for model in models:
            if not isinstance(model, dict):
                continue
            name = model.get("name") or model.get("model")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
        return self._unique(names)

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
                request, timeout=self._timeout
            ) as response:  # noqa: S310 - local Ollama URL from settings.
                body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise RuntimeError(str(exc)) from exc
        if not body.strip():
            return {}
        return json.loads(body)

    @classmethod
    def _same_model_name(cls, left: str, right: str) -> bool:
        left = left.strip()
        right = right.strip()
        return (
            left == right
            or left == f"{right}:latest"
            or f"{left}:latest" == right
            or left.removesuffix(":latest") == right.removesuffix(":latest")
        )

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            normalized = value.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result


class ComfyUICacheUnloader:
    """Free ComfyUI model cache before interactive chat uses Ollama."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.image_generation_comfyui_url.rstrip("/")
        self._timeout = settings.local_ai_hotswap_timeout_seconds

    async def unload_for_chat(self, reason: str) -> list[str]:
        if (
            not self._settings.local_ai_hotswap_enabled
            or not self._settings.local_ai_unload_comfyui_before_chat
            or not self._settings.image_generation_enabled
        ):
            return []
        return await asyncio.to_thread(self._unload_for_chat_sync, reason)

    def _unload_for_chat_sync(self, reason: str) -> list[str]:
        try:
            self._post_json("/free", {"unload_models": True, "free_memory": True})
        except Exception as exc:  # pragma: no cover - local backend dependent.
            logger.debug(
                "ComfyUI cache unload skipped",
                extra={"reason": reason, "url": self._base_url, "error": str(exc)},
            )
            return []
        logger.info("Freed ComfyUI model cache before chat", extra={"reason": reason})
        return ["comfyui"]

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self._timeout
            ) as response:  # noqa: S310 - local ComfyUI URL from settings.
                body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise RuntimeError(str(exc)) from exc
        if not body.strip():
            return {}
        return json.loads(body)
