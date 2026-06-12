"""Lightweight extension registry, command bus, and character-card importer."""

from __future__ import annotations

import logging
from collections import deque
from typing import Any
from uuid import uuid4

from app.models.extensions import (
    EXTENSION_API_VERSION,
    MAX_LOREBOOK_ENTRIES,
    MAX_VISUAL_ASSETS,
    CharacterImportPreview,
    CharacterImportRequest,
    ExtensionCapability,
    ExtensionCommandRequest,
    ExtensionCommandResult,
    ExtensionEventEnvelope,
    ExtensionManifest,
    ExtensionPermission,
    ExtensionRegistryResponse,
    ExtensionSettingDefinition,
    ExtensionSettingKind,
    ExtensionSettingsSection,
    ImageStyleReference,
    LorebookEntry,
    MoodGrowthPreferences,
    RegisteredExtension,
    VisualAssetHint,
    VoiceProfileHint,
)

logger = logging.getLogger(__name__)


class ExtensionRegistryError(Exception):
    """Raised when an extension cannot be safely registered or invoked."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ExtensionRegistry:
    """Process-local extension registry with defensive error isolation.

    This is deliberately metadata-first: Reverie loads manifests and schemas,
    not arbitrary Python code. Future extension executors can subscribe to the
    same bus while preserving this registry as the typed source of truth.
    """

    def __init__(self) -> None:
        self._extensions: dict[str, RegisteredExtension] = {}
        self._events: deque[ExtensionEventEnvelope] = deque(maxlen=256)
        self._register_builtin_extensions()

    def _register_builtin_extensions(self) -> None:
        manifest = ExtensionManifest(
            id="reverie.core.extensibility",
            name="Reverie Core Extensibility",
            version="0.1.0",
            api_version=EXTENSION_API_VERSION,
            description="Built-in contracts for safe panels, commands, settings, imports, TTS, image, memory, and growth integrations.",
            author="Vision Entertainment",
            capabilities=[
                ExtensionCapability.settings_section,
                ExtensionCapability.command,
                ExtensionCapability.character_importer,
                ExtensionCapability.event_subscriber,
            ],
            permissions=[ExtensionPermission.register_ui],
            settings_sections=[
                ExtensionSettingsSection(
                    id="extension_developer_mode",
                    title="Extension Developer Mode",
                    description="Local-only diagnostics for extension manifests and command events.",
                    settings=[
                        ExtensionSettingDefinition(
                            key="showDiagnostics",
                            label="Show extension diagnostics",
                            kind=ExtensionSettingKind.boolean,
                            description="Display manifest and command-bus metadata while developing local extensions.",
                            default=False,
                        )
                    ],
                )
            ],
        )
        self.register(manifest)

    def register(self, manifest: ExtensionManifest) -> RegisteredExtension:
        try:
            existing = self._extensions.get(manifest.id)
            if existing and existing.manifest.version == manifest.version:
                return existing
            record = RegisteredExtension(manifest=manifest)
            self._extensions[manifest.id] = record
            return record
        except Exception as exc:  # pragma: no cover - defensive isolation.
            logger.exception("Extension registration failed", extra={"extension_id": getattr(manifest, "id", "unknown")})
            raise ExtensionRegistryError("extension_registration_failed", str(exc)) from exc

    def list_extensions(self) -> ExtensionRegistryResponse:
        return ExtensionRegistryResponse(extensions=list(self._extensions.values()))

    def dispatch(self, request: ExtensionCommandRequest) -> ExtensionCommandResult:
        try:
            event = ExtensionEventEnvelope(
                event_id=f"evt_{uuid4().hex}",
                event_type=f"command.{request.target}.{request.command_id}",
                source=request.source,
                target=request.target,
                payload={"command_id": request.command_id, **request.payload},
            )
            self._events.append(event)
            return ExtensionCommandResult(accepted=True, event=event)
        except Exception as exc:  # pragma: no cover - defensive isolation.
            logger.exception("Extension command dispatch failed", extra={"command_id": request.command_id})
            return ExtensionCommandResult(
                accepted=False,
                error={"code": "extension_command_failed", "message": str(exc), "retryable": False},
            )

    def recent_events(self) -> list[ExtensionEventEnvelope]:
        return list(self._events)


class CharacterImportService:
    """Normalizes SillyTavern/character-card payloads into Reverie contracts."""

    def preview(self, request: CharacterImportRequest) -> CharacterImportPreview:
        card = request.card or {}
        data = card.get("data") if isinstance(card.get("data"), dict) else card
        warnings: list[str] = []
        source_format = self._detect_format(request.source_format, card)

        preview = CharacterImportPreview(
            source_format=source_format,
            name=self._first_text(data, card, keys=("name", "char_name")) or "Unnamed Character",
            description=self._first_text(data, card, keys=("description", "char_persona")) or "",
            personality=self._first_text(data, card, keys=("personality", "personality_summary")) or "",
            scenario=self._first_text(data, card, keys=("scenario", "world_scenario")) or "",
            first_message=self._first_text(data, card, keys=("first_mes", "first_message", "mes_example")) or "",
            example_dialogues=self._examples(data),
            tags=self._list_text(data.get("tags") or card.get("tags")),
            lorebook_entries=self._lorebook_entries(card, data, warnings),
            visual_assets=self._visual_assets(card, data, request.embedded_assets, warnings),
            voice_hints=self._voice_hints(card, data),
            mood_growth_preferences=self._mood_growth_preferences(card, data),
            image_style_references=self._image_style_references(card, data),
            warnings=warnings,
            raw_metadata={
                "creator": data.get("creator") or card.get("creator"),
                "character_version": data.get("character_version") or card.get("character_version"),
                "extensions": data.get("extensions") or card.get("extensions") or {},
            },
        )
        if not preview.lorebook_entries:
            preview.warnings.append("No lorebook/world-info entries were found in the card.")
        return preview

    def _detect_format(self, requested: str, card: dict[str, Any]) -> str:
        if requested != "auto":
            return requested
        spec = str(card.get("spec") or card.get("spec_version") or "").lower()
        if "chara_card" in spec or "character_card" in spec:
            return "character_card_v2"
        return "sillytavern_json"

    def _first_text(self, *sources: dict[str, Any], keys: tuple[str, ...]) -> str | None:
        for source in sources:
            for key in keys:
                value = source.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    def _list_text(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            candidates = value.replace(";", ",").split(",")
        elif isinstance(value, list):
            candidates = value
        else:
            return []
        normalized: list[str] = []
        for item in candidates:
            text = str(item).strip()
            if text and text.lower() not in {existing.lower() for existing in normalized}:
                normalized.append(text[:120])
        return normalized

    def _examples(self, data: dict[str, Any]) -> list[str]:
        examples = data.get("alternate_greetings") or []
        if isinstance(examples, str):
            examples = [examples]
        mes_example = data.get("mes_example")
        if isinstance(mes_example, str) and mes_example.strip():
            examples = [mes_example, *examples]
        return [str(item).strip()[:4000] for item in examples if str(item).strip()][:40]

    def _lorebook_entries(self, card: dict[str, Any], data: dict[str, Any], warnings: list[str]) -> list[LorebookEntry]:
        candidates = [data.get("character_book"), card.get("character_book"), data.get("world_info"), card.get("world_info")]
        entries: list[LorebookEntry] = []
        for candidate in candidates:
            raw_entries = candidate.get("entries") if isinstance(candidate, dict) else candidate
            if isinstance(raw_entries, dict):
                raw_entries = list(raw_entries.values())
            if not isinstance(raw_entries, list):
                continue
            for index, raw in enumerate(raw_entries[:MAX_LOREBOOK_ENTRIES]):
                if not isinstance(raw, dict):
                    continue
                content = str(raw.get("content") or raw.get("entry") or "").strip()
                if not content:
                    continue
                keys = self._list_text(raw.get("keys") or raw.get("key") or raw.get("keywords"))
                entries.append(
                    LorebookEntry(
                        id=str(raw.get("id") or raw.get("uid") or f"lore_{len(entries) + 1}"),
                        keys=keys,
                        secondary_keys=self._list_text(raw.get("secondary_keys") or raw.get("keysecondary")),
                        content=content,
                        comment=str(raw.get("comment") or raw.get("name") or "")[:500] or None,
                        enabled=bool(raw.get("enabled", not raw.get("disable", False))),
                        constant=bool(raw.get("constant", False)),
                        selective=bool(raw.get("selective", False)),
                        insertion_order=self._safe_int(raw.get("insertion_order") or raw.get("order"), index + 100),
                        metadata={"position": raw.get("position"), "probability": raw.get("probability")},
                    )
                )
        if len(entries) >= MAX_LOREBOOK_ENTRIES:
            warnings.append("Lorebook was capped at 200 entries to keep import lightweight.")
        return entries[:MAX_LOREBOOK_ENTRIES]

    def _visual_assets(self, card: dict[str, Any], data: dict[str, Any], embedded: list[dict[str, Any]], warnings: list[str]) -> list[VisualAssetHint]:
        extensions = self._extensions(card, data)
        raw_assets = extensions.get("assets") or extensions.get("sprites") or data.get("assets") or []
        assets: list[VisualAssetHint] = []
        avatar = data.get("avatar") or card.get("avatar") or card.get("file_name")
        if avatar:
            assets.append(VisualAssetHint(id="avatar", kind="avatar", label="Avatar", source=str(avatar)))
        if isinstance(raw_assets, dict):
            raw_assets = [{"id": key, **(value if isinstance(value, dict) else {"source": value})} for key, value in raw_assets.items()]
        if isinstance(raw_assets, list):
            for index, asset in enumerate(raw_assets[:MAX_VISUAL_ASSETS]):
                if not isinstance(asset, dict):
                    continue
                assets.append(
                    VisualAssetHint(
                        id=str(asset.get("id") or asset.get("name") or f"asset_{index + 1}"),
                        kind=self._visual_kind(asset.get("kind") or asset.get("type")),
                        label=asset.get("label") or asset.get("name"),
                        source=asset.get("path") or asset.get("url") or asset.get("source"),
                        expression=asset.get("expression") or asset.get("emotion"),
                        metadata={key: value for key, value in asset.items() if key not in {"id", "name", "kind", "type", "label", "path", "url", "source", "expression", "emotion"}},
                    )
                )
        for index, asset in enumerate(embedded[:MAX_VISUAL_ASSETS]):
            assets.append(
                VisualAssetHint(
                    id=str(asset.get("id") or f"embedded_{index + 1}"),
                    kind=self._visual_kind(asset.get("kind") or "reference"),
                    label=asset.get("label"),
                    source=asset.get("file_name") or asset.get("source"),
                    metadata={"embedded": True, **asset},
                )
            )
        if len(assets) >= MAX_VISUAL_ASSETS:
            warnings.append("Visual assets were capped at 80 hints for 8GB-safe import previews.")
        return assets[:MAX_VISUAL_ASSETS]

    def _voice_hints(self, card: dict[str, Any], data: dict[str, Any]) -> list[VoiceProfileHint]:
        extensions = self._extensions(card, data)
        raw = extensions.get("voice") or extensions.get("voice_hints") or data.get("voice")
        if not raw:
            return []
        items = raw if isinstance(raw, list) else [raw]
        hints: list[VoiceProfileHint] = []
        for item in items[:12]:
            if isinstance(item, str):
                hints.append(VoiceProfileHint(description=item, tags=self._list_text(item)))
            elif isinstance(item, dict):
                hints.append(
                    VoiceProfileHint(
                        voice_id=item.get("voice_id") or item.get("id"),
                        provider=item.get("provider"),
                        description=item.get("description") or item.get("prompt"),
                        sample_text=item.get("sample_text"),
                        tags=self._list_text(item.get("tags")),
                        metadata=item,
                    )
                )
        return hints

    def _mood_growth_preferences(self, card: dict[str, Any], data: dict[str, Any]) -> MoodGrowthPreferences:
        extensions = self._extensions(card, data)
        raw = extensions.get("reverie_growth") or extensions.get("growth") or extensions.get("mood") or {}
        if not isinstance(raw, dict):
            raw = {"growth_notes": self._list_text(raw)}
        return MoodGrowthPreferences(
            baseline_mood=raw.get("baseline_mood") or raw.get("mood"),
            affection_style=raw.get("affection_style"),
            trust_pace=raw.get("trust_pace") or raw.get("relationship_pace"),
            boundaries=self._list_text(raw.get("boundaries")),
            growth_notes=self._list_text(raw.get("growth_notes") or raw.get("preferences") or raw.get("notes")),
            metadata=raw,
        )

    def _image_style_references(self, card: dict[str, Any], data: dict[str, Any]) -> list[ImageStyleReference]:
        extensions = self._extensions(card, data)
        raw = extensions.get("image_style") or extensions.get("image_generation") or extensions.get("style_references") or []
        items = raw if isinstance(raw, list) else [raw]
        refs: list[ImageStyleReference] = []
        for index, item in enumerate(items[:24]):
            if isinstance(item, str):
                refs.append(ImageStyleReference(id=f"style_{index + 1}", prompt=item))
            elif isinstance(item, dict):
                refs.append(
                    ImageStyleReference(
                        id=str(item.get("id") or item.get("name") or f"style_{index + 1}"),
                        prompt=str(item.get("prompt") or item.get("positive") or ""),
                        negative_prompt=item.get("negative_prompt") or item.get("negative"),
                        style_tags=self._list_text(item.get("style_tags") or item.get("tags")),
                        reference_assets=self._list_text(item.get("reference_assets") or item.get("assets")),
                        metadata=item,
                    )
                )
        return refs

    def _safe_int(self, value: Any, fallback: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def _visual_kind(self, value: Any) -> str:
        candidate = str(value or "unknown").strip().lower()
        return candidate if candidate in {"avatar", "sprite", "expression", "background", "reference", "unknown"} else "unknown"

    def _extensions(self, card: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
        raw = data.get("extensions") or card.get("extensions") or {}
        return raw if isinstance(raw, dict) else {}


_extension_registry = ExtensionRegistry()
_character_import_service = CharacterImportService()


def get_extension_registry() -> ExtensionRegistry:
    return _extension_registry


def get_character_import_service() -> CharacterImportService:
    return _character_import_service
