"""Lightweight extension registry, event bus, and character import helpers."""

from __future__ import annotations

import json
import logging
from collections import deque
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.core.config import Settings
from app.models.extensions import (
    CharacterImportProfile,
    CharacterImportRequest,
    ExtensionCapability,
    ExtensionCommandRequest,
    ExtensionCommandResult,
    ExtensionError,
    ExtensionEvent,
    ExtensionEventScope,
    ExtensionManifest,
    ExtensionRead,
    ExtensionRegistryResponse,
    ExtensionStatus,
    ImportedAssetReference,
    ImportedLoreEntry,
)

logger = logging.getLogger(__name__)


class ExtensionRegistry:
    """Loads local extension manifests without importing arbitrary extension code.

    The foundation deliberately treats extensions as declarative metadata plus a
    typed event/command contract. Future plugin runtimes can be added behind this
    boundary, while today's app avoids unsafe imports and keeps startup overhead
    to small JSON files.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._extensions: dict[str, ExtensionRead] = {}
        self._errors: list[ExtensionError] = []
        self._loaded = False

    def load(self) -> ExtensionRegistryResponse:
        if self._loaded:
            return self.snapshot()

        self._extensions = {}
        self._errors = []
        self._register_manifest(_core_manifest(), status=ExtensionStatus.ENABLED)

        if self._settings.extensions_enabled:
            for directory in self._settings.extension_manifest_dirs:
                self._load_directory(Path(directory))

        self._loaded = True
        return self.snapshot()

    def snapshot(self) -> ExtensionRegistryResponse:
        return ExtensionRegistryResponse(
            extensions=sorted(self._extensions.values(), key=lambda item: item.manifest.name.lower()),
            errors=list(self._errors),
        )

    def get(self, extension_id: str) -> ExtensionRead | None:
        self.load()
        return self._extensions.get(extension_id)

    def can_dispatch(self, request: ExtensionCommandRequest) -> ExtensionError | None:
        extension = self.get(request.source_extension_id)
        if extension is None:
            return _error(
                request.source_extension_id,
                "extension_not_registered",
                "That extension is not registered.",
                {"command_id": request.command_id},
            )
        if extension.status != ExtensionStatus.ENABLED:
            return _error(
                request.source_extension_id,
                "extension_not_enabled",
                "That extension is not enabled.",
                {"command_id": request.command_id, "status": extension.status.value},
            )
        if ExtensionCapability.COMMANDS not in extension.manifest.capabilities:
            return _error(
                request.source_extension_id,
                "extension_missing_commands_capability",
                "That extension has not requested command bus access.",
                {"command_id": request.command_id},
            )
        command = next(
            (candidate for candidate in extension.manifest.commands if candidate.command_id == request.command_id),
            None,
        )
        if command is None:
            return _error(
                request.source_extension_id,
                "extension_command_not_declared",
                "That command is not declared by the extension manifest.",
                {"command_id": request.command_id},
            )
        missing = [capability for capability in command.required_capabilities if capability not in extension.manifest.capabilities]
        if missing:
            return _error(
                request.source_extension_id,
                "extension_missing_required_capability",
                "That command requires capabilities not granted to the extension.",
                {"command_id": request.command_id, "missing": [item.value for item in missing]},
            )
        return None

    def _load_directory(self, directory: Path) -> None:
        try:
            resolved = directory.expanduser().resolve()
        except OSError as exc:
            self._errors.append(_error("extension-loader", "extension_directory_invalid", str(exc), {"path": str(directory)}))
            return
        if not resolved.exists():
            return
        if not resolved.is_dir():
            self._errors.append(_error("extension-loader", "extension_directory_not_directory", "Extension manifest path is not a directory.", {"path": str(resolved)}))
            return
        for manifest_path in sorted(resolved.glob("*.json")):
            self._load_manifest_file(manifest_path)

    def _load_manifest_file(self, manifest_path: Path) -> None:
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = ExtensionManifest.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            error = _error(
                "extension-loader",
                "extension_manifest_invalid",
                "An extension manifest could not be loaded.",
                {"path": str(manifest_path), "reason": str(exc)[:500]},
            )
            self._errors.append(error)
            logger.warning("Extension manifest failed validation", extra={"path": str(manifest_path), "error": str(exc)})
            return

        self._register_manifest(
            manifest,
            status=ExtensionStatus.ENABLED if manifest.enabled_by_default else ExtensionStatus.DISABLED,
        )

    def _register_manifest(self, manifest: ExtensionManifest, status: ExtensionStatus) -> None:
        if manifest.extension_id in self._extensions:
            self._errors.append(_error(manifest.extension_id, "extension_duplicate_id", "Duplicate extension ID ignored."))
            return
        self._extensions[manifest.extension_id] = ExtensionRead(manifest=manifest, status=status)


class ExtensionEventBus:
    """Small in-process typed event/command bus with bounded history."""

    def __init__(self, registry: ExtensionRegistry, *, history_limit: int = 100) -> None:
        self._registry = registry
        self._history: deque[ExtensionEvent] = deque(maxlen=history_limit)

    def publish_core_event(
        self,
        event_type: str,
        scope: ExtensionEventScope,
        payload: dict[str, Any] | None = None,
    ) -> ExtensionEvent:
        event = ExtensionEvent(
            event_id=f"evt_{uuid4().hex}",
            event_type=event_type,
            scope=scope,
            source="reverie.core",
            payload=_bounded_payload(payload or {}),
        )
        self._history.append(event)
        return event

    def dispatch(self, request: ExtensionCommandRequest) -> ExtensionCommandResult:
        error = self._registry.can_dispatch(request)
        if error is not None:
            return ExtensionCommandResult(accepted=False, error=error)
        event = ExtensionEvent(
            event_id=f"evt_{uuid4().hex}",
            event_type=f"command.{request.command_id}",
            scope=request.scope,
            source=request.source_extension_id,
            payload=_bounded_payload(request.payload),
        )
        self._history.append(event)
        return ExtensionCommandResult(accepted=True, event=event)

    def recent(self, *, limit: int = 50) -> list[ExtensionEvent]:
        bounded_limit = min(max(limit, 1), 100)
        return list(self._history)[-bounded_limit:]


class CharacterImportService:
    """Normalizes SillyTavern/character-card payloads into Reverie import previews."""

    KNOWN_TOP_LEVEL = {
        "spec",
        "spec_version",
        "name",
        "description",
        "personality",
        "scenario",
        "first_mes",
        "mes_example",
        "avatar",
        "creator_notes",
        "tags",
        "data",
        "extensions",
        "character_book",
    }

    def preview(self, request: CharacterImportRequest) -> CharacterImportProfile:
        payload = dict(request.payload)
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        extensions = _as_dict(data.get("extensions")) | _as_dict(payload.get("extensions"))
        warnings: list[str] = []

        name = _clean_text(data.get("name") or payload.get("name") or "Imported Character", 160)
        lore_entries = self._extract_lore_entries(payload, data, warnings)
        assets = self._extract_assets(payload, data, extensions)
        voice_hints = self._extract_voice_hints(data, extensions)
        mood_preferences = self._extract_mood_preferences(data, extensions)
        growth_preferences = self._extract_growth_preferences(data, extensions)
        image_style_references = self._extract_image_style_references(data, extensions)
        preserved = {
            key: value
            for key, value in payload.items()
            if key not in self.KNOWN_TOP_LEVEL and _is_jsonish(value)
        }

        if not lore_entries:
            warnings.append("No lorebook/world-info entries were found in the imported card.")
        if not assets:
            warnings.append("No sprite or visual asset references were found beyond embedded card data.")
        if not voice_hints:
            warnings.append("No explicit voice profile hints were found; Reverie can assign a voice later.")

        return CharacterImportProfile(
            name=name,
            description=_clean_optional(data.get("description")),
            personality=_clean_optional(data.get("personality")),
            scenario=_clean_optional(data.get("scenario")),
            first_message=_clean_optional(data.get("first_mes") or data.get("first_message")),
            example_dialogue=_clean_optional(data.get("mes_example") or data.get("example_dialogue")),
            lorebook_entries=lore_entries,
            visual_assets=assets,
            voice_hints=voice_hints,
            mood_preferences=mood_preferences,
            growth_preferences=growth_preferences,
            image_style_references=image_style_references,
            preserved_unknown_fields=preserved,
            warnings=warnings,
        )

    def _extract_lore_entries(self, payload: dict[str, Any], data: dict[str, Any], warnings: list[str]) -> list[ImportedLoreEntry]:
        books = [payload.get("character_book"), data.get("character_book"), _as_dict(data.get("extensions")).get("world_info"), _as_dict(data.get("extensions")).get("lorebook")]
        entries: list[ImportedLoreEntry] = []
        seen: set[str] = set()
        for book in books:
            raw_entries = _as_entries(book)
            for index, raw_entry in enumerate(raw_entries):
                title = _clean_text(raw_entry.get("comment") or raw_entry.get("name") or raw_entry.get("title") or f"Lore {index + 1}", 120)
                keys = raw_entry.get("keys") or raw_entry.get("key") or raw_entry.get("keywords") or []
                triggers = [_clean_text(item, 80) for item in _as_list(keys) if _clean_text(item, 80)]
                content = _clean_text(raw_entry.get("content") or raw_entry.get("text") or raw_entry.get("entry") or "", 4000)
                if not content and not triggers:
                    continue
                stable_id = f"lore_{_slug(title)}_{len(entries) + 1}"
                if stable_id in seen:
                    stable_id = f"{stable_id}_{index}"
                seen.add(stable_id)
                priority = _coerce_priority(raw_entry.get("priority") or raw_entry.get("order"))
                entries.append(
                    ImportedLoreEntry(
                        id=stable_id,
                        title=title,
                        triggers=triggers[:24],
                        priority=priority,
                        budget_tokens=_coerce_budget(raw_entry.get("budget") or raw_entry.get("budget_tokens")),
                        facts=_split_facts(content),
                        limits=_extract_limits(raw_entry),
                    )
                )
        if len(entries) > 200:
            warnings.append("Imported lorebook was trimmed to the first 200 entries for review.")
        return entries[:200]

    def _extract_assets(self, payload: dict[str, Any], data: dict[str, Any], extensions: dict[str, Any]) -> list[ImportedAssetReference]:
        assets: list[ImportedAssetReference] = []
        avatar = data.get("avatar") or payload.get("avatar")
        if isinstance(avatar, str) and avatar.strip():
            assets.append(ImportedAssetReference(id="asset_avatar", kind="avatar", label="Imported avatar", path=avatar.strip()))
        for key in ("sprites", "sprite", "assets", "visual_assets", "expressions"):
            for index, item in enumerate(_as_list(extensions.get(key))):
                asset = _asset_from_unknown(item, index=index, fallback_kind="sprite")
                if asset is not None:
                    assets.append(asset)
        for key in ("backgrounds", "background_assets"):
            for index, item in enumerate(_as_list(extensions.get(key))):
                asset = _asset_from_unknown(item, index=index, fallback_kind="background")
                if asset is not None:
                    assets.append(asset)
        return assets[:80]

    def _extract_voice_hints(self, data: dict[str, Any], extensions: dict[str, Any]) -> dict[str, Any]:
        hints = _as_dict(extensions.get("voice")) | _as_dict(extensions.get("voice_profile"))
        for key in ("voice", "voice_profile", "tts", "speaking_style"):
            if key in data and _is_jsonish(data[key]):
                hints[key] = data[key]
            if key in extensions and _is_jsonish(extensions[key]):
                hints[key] = extensions[key]
        return _bounded_mapping(hints)

    def _extract_mood_preferences(self, data: dict[str, Any], extensions: dict[str, Any]) -> dict[str, Any]:
        mood = _as_dict(extensions.get("mood")) | _as_dict(extensions.get("mood_preferences"))
        tags = [str(item) for item in _as_list(data.get("tags"))]
        mood_tags = [tag for tag in tags if tag.lower() in {"shy", "bold", "playful", "soft", "dominant", "submissive", "romantic", "dark"}]
        if mood_tags:
            mood["tag_hints"] = mood_tags[:20]
        return _bounded_mapping(mood)

    def _extract_growth_preferences(self, data: dict[str, Any], extensions: dict[str, Any]) -> dict[str, Any]:
        growth = _as_dict(extensions.get("growth")) | _as_dict(extensions.get("relationship"))
        if isinstance(data.get("personality"), str):
            growth.setdefault("stable_personality_source", "personality")
        return _bounded_mapping(growth)

    def _extract_image_style_references(self, data: dict[str, Any], extensions: dict[str, Any]) -> dict[str, Any]:
        image = _as_dict(extensions.get("image_generation")) | _as_dict(extensions.get("stable_diffusion"))
        for key in ("sd_character_prompt", "sd_negative_prompt", "style", "appearance", "appearance_tags"):
            if key in data and _is_jsonish(data[key]):
                image[key] = data[key]
            if key in extensions and _is_jsonish(extensions[key]):
                image[key] = extensions[key]
        return _bounded_mapping(image)


def _core_manifest() -> ExtensionManifest:
    return ExtensionManifest(
        extension_id="reverie.core",
        name="Reverie Core Extension Surface",
        version="1.0.0",
        description="Built-in extension contracts for panels, commands, voices, image workflows, growth modifiers, and character import previews.",
        enabled_by_default=True,
        capabilities=[
            ExtensionCapability.CUSTOM_PANEL,
            ExtensionCapability.COMMANDS,
            ExtensionCapability.SETTINGS,
            ExtensionCapability.TTS_VOICE,
            ExtensionCapability.IMAGE_WORKFLOW,
            ExtensionCapability.GROWTH_MODIFIER,
            ExtensionCapability.CHARACTER_IMPORT,
            ExtensionCapability.VN_STATE,
            ExtensionCapability.MEMORY_READ,
            ExtensionCapability.MEMORY_WRITE,
        ],
    )


def _error(extension_id: str, code: str, message: str, details: dict[str, Any] | None = None) -> ExtensionError:
    return ExtensionError(extension_id=extension_id, code=code, message=message, details=details or {})


def _bounded_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return _bounded_mapping(payload, max_items=40, max_text=2000)


def _bounded_mapping(mapping: dict[str, Any], *, max_items: int = 40, max_text: int = 1000) -> dict[str, Any]:
    bounded: dict[str, Any] = {}
    for index, (key, value) in enumerate(mapping.items()):
        if index >= max_items:
            break
        if not isinstance(key, str):
            continue
        bounded[key[:120]] = _bounded_value(value, max_text=max_text)
    return bounded


def _bounded_value(value: Any, *, max_text: int) -> Any:
    if isinstance(value, str):
        return value[:max_text]
    if isinstance(value, bool | int | float) or value is None:
        return value
    if isinstance(value, list):
        return [_bounded_value(item, max_text=max_text) for item in value[:40]]
    if isinstance(value, dict):
        return _bounded_mapping(value, max_items=40, max_text=max_text)
    return str(value)[:max_text]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return list(value.values())
    if value is None:
        return []
    return [value]


def _as_entries(book: Any) -> list[dict[str, Any]]:
    if isinstance(book, dict):
        entries = book.get("entries") or book.get("items") or book.get("world_info")
        return [entry for entry in _as_list(entries) if isinstance(entry, dict)]
    return [entry for entry in _as_list(book) if isinstance(entry, dict)]


def _clean_text(value: Any, max_length: int) -> str:
    return str(value or "").strip()[:max_length]


def _clean_optional(value: Any) -> str | None:
    text = _clean_text(value, 8000)
    return text or None


def _slug(value: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "_" for character in value).strip("_")
    return slug[:48] or "entry"


def _coerce_priority(value: Any) -> int:
    if isinstance(value, int | float):
        return max(0, min(100, int(value)))
    return 50


def _coerce_budget(value: Any) -> int:
    if isinstance(value, int | float):
        return max(40, min(800, int(value)))
    return 180


def _split_facts(content: str) -> list[str]:
    if not content:
        return []
    lines = [line.strip(" -•\t") for line in content.splitlines() if line.strip()]
    if len(lines) <= 1:
        lines = [part.strip() for part in content.replace("\n", " ").split(". ") if part.strip()]
    return [line[:500] for line in lines[:20]]


def _extract_limits(raw_entry: dict[str, Any]) -> list[str]:
    limits = raw_entry.get("limits") or raw_entry.get("contradictions") or raw_entry.get("forbidden")
    return [_clean_text(item, 300) for item in _as_list(limits) if _clean_text(item, 300)][:12]


def _asset_from_unknown(item: Any, *, index: int, fallback_kind: str) -> ImportedAssetReference | None:
    if isinstance(item, str) and item.strip():
        return ImportedAssetReference(id=f"asset_{fallback_kind}_{index + 1}", kind=fallback_kind, label=f"Imported {fallback_kind} {index + 1}", path=item.strip())
    if not isinstance(item, dict):
        return None
    path = item.get("path") or item.get("src") or item.get("url") or item.get("file")
    label = _clean_text(item.get("label") or item.get("name") or item.get("expression") or f"Imported {fallback_kind} {index + 1}", 120)
    kind = item.get("kind") if item.get("kind") in {"avatar", "sprite", "background", "reference", "audio"} else fallback_kind
    return ImportedAssetReference(
        id=_clean_text(item.get("id") or f"asset_{fallback_kind}_{index + 1}", 120),
        kind=kind,
        label=label,
        path=_clean_text(path, 1000) or None,
        mime_type=_clean_text(item.get("mime_type") or item.get("type"), 120) or None,
        metadata=_bounded_mapping({key: value for key, value in item.items() if key not in {"id", "kind", "path", "src", "url", "file", "label", "name"}}),
    )


def _is_jsonish(value: Any) -> bool:
    return isinstance(value, str | int | float | bool | list | dict) or value is None
