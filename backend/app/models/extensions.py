"""Typed extension contracts and character import schemas for Reverie.

The models in this module are intentionally small and JSON-serializable. They
form the safe boundary between core systems and optional extensions: extensions
can declare capabilities, settings, commands, panels, and import enrichments,
but core services remain responsible for validation and execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

EXTENSION_API_VERSION = "2026.06.v1"
MAX_EXTENSION_ID_CHARS = 80
MAX_EXTENSION_SETTINGS = 24
MAX_LOREBOOK_ENTRIES = 200
MAX_VISUAL_ASSETS = 80


class ExtensionCapability(StrEnum):
    custom_panel = "custom_panel"
    command = "command"
    tts_voice = "tts_voice"
    image_workflow = "image_workflow"
    growth_modifier = "growth_modifier"
    settings_section = "settings_section"
    character_importer = "character_importer"
    event_subscriber = "event_subscriber"


class ExtensionStatus(StrEnum):
    active = "active"
    disabled = "disabled"
    failed = "failed"


class ExtensionPermission(StrEnum):
    read_conversation_context = "read_conversation_context"
    read_character_profile = "read_character_profile"
    suggest_memory = "suggest_memory"
    suggest_growth_modifier = "suggest_growth_modifier"
    request_tts_voice = "request_tts_voice"
    request_image_workflow = "request_image_workflow"
    register_ui = "register_ui"


class ExtensionSettingKind(StrEnum):
    text = "text"
    textarea = "textarea"
    boolean = "boolean"
    number = "number"
    select = "select"


class ExtensionSettingOption(BaseModel):
    value: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=120)


class ExtensionSettingDefinition(BaseModel):
    key: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    label: str = Field(min_length=1, max_length=120)
    kind: ExtensionSettingKind
    description: str | None = Field(default=None, max_length=400)
    default: str | float | bool | None = None
    options: list[ExtensionSettingOption] = Field(default_factory=list, max_length=20)


class ExtensionSettingsSection(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    settings: list[ExtensionSettingDefinition] = Field(default_factory=list, max_length=MAX_EXTENSION_SETTINGS)


class ExtensionCommandDefinition(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.:-]+$")
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    target: Literal["vn", "tts", "image", "growth", "memory", "character", "system"]
    payload_schema: dict[str, Any] = Field(default_factory=dict)


class ExtensionPanelDefinition(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.:-]+$")
    title: str = Field(min_length=1, max_length=120)
    slot: Literal["sidebar", "settings", "character", "vn", "memory", "growth"] = "settings"
    description: str | None = Field(default=None, max_length=500)


class ExtensionManifest(BaseModel):
    id: str = Field(min_length=1, max_length=MAX_EXTENSION_ID_CHARS, pattern=r"^[a-zA-Z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=40)
    api_version: str = Field(default=EXTENSION_API_VERSION, max_length=40)
    description: str | None = Field(default=None, max_length=800)
    author: str | None = Field(default=None, max_length=120)
    capabilities: list[ExtensionCapability] = Field(default_factory=list, max_length=16)
    permissions: list[ExtensionPermission] = Field(default_factory=list, max_length=16)
    commands: list[ExtensionCommandDefinition] = Field(default_factory=list, max_length=32)
    panels: list[ExtensionPanelDefinition] = Field(default_factory=list, max_length=16)
    settings_sections: list[ExtensionSettingsSection] = Field(default_factory=list, max_length=16)


class RegisteredExtension(BaseModel):
    manifest: ExtensionManifest
    status: ExtensionStatus = ExtensionStatus.active
    loaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None


class ExtensionRegistryResponse(BaseModel):
    api_version: str = EXTENSION_API_VERSION
    extensions: list[RegisteredExtension]


class ExtensionEventEnvelope(BaseModel):
    event_id: str = Field(min_length=1, max_length=120)
    event_type: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9_.:-]+$")
    source: str = Field(min_length=1, max_length=MAX_EXTENSION_ID_CHARS)
    target: Literal["vn", "tts", "image", "growth", "memory", "character", "system", "extension"]
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)


class ExtensionCommandRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=120)
    source: str = Field(default="core", min_length=1, max_length=MAX_EXTENSION_ID_CHARS)
    target: Literal["vn", "tts", "image", "growth", "memory", "character", "system"]
    payload: dict[str, Any] = Field(default_factory=dict)


class ExtensionCommandResult(BaseModel):
    accepted: bool
    event: ExtensionEventEnvelope | None = None
    error: dict[str, Any] | None = None


class LorebookEntry(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    keys: list[str] = Field(default_factory=list, max_length=24)
    secondary_keys: list[str] = Field(default_factory=list, max_length=24)
    content: str = Field(default="", max_length=8000)
    comment: str | None = Field(default=None, max_length=500)
    enabled: bool = True
    constant: bool = False
    selective: bool = False
    insertion_order: int = 100
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisualAssetHint(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    kind: Literal["avatar", "sprite", "expression", "background", "reference", "unknown"] = "unknown"
    label: str | None = Field(default=None, max_length=120)
    source: str | None = Field(default=None, max_length=500)
    expression: str | None = Field(default=None, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VoiceProfileHint(BaseModel):
    voice_id: str | None = Field(default=None, max_length=120)
    provider: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=800)
    sample_text: str | None = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list, max_length=24)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MoodGrowthPreferences(BaseModel):
    baseline_mood: str | None = Field(default=None, max_length=80)
    affection_style: str | None = Field(default=None, max_length=120)
    trust_pace: str | None = Field(default=None, max_length=120)
    boundaries: list[str] = Field(default_factory=list, max_length=30)
    growth_notes: list[str] = Field(default_factory=list, max_length=40)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImageStyleReference(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    prompt: str = Field(default="", max_length=1200)
    negative_prompt: str | None = Field(default=None, max_length=1200)
    style_tags: list[str] = Field(default_factory=list, max_length=40)
    reference_assets: list[str] = Field(default_factory=list, max_length=20)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CharacterImportRequest(BaseModel):
    source_format: Literal["sillytavern_json", "character_card_v2", "reverie_v1", "auto"] = "auto"
    file_name: str | None = Field(default=None, max_length=260)
    card: dict[str, Any] = Field(default_factory=dict)
    embedded_assets: list[dict[str, Any]] = Field(default_factory=list, max_length=MAX_VISUAL_ASSETS)


class CharacterImportPreview(BaseModel):
    importer_version: str = "2026.06.v1"
    source_format: str
    name: str = "Unnamed Character"
    description: str = ""
    personality: str = ""
    scenario: str = ""
    first_message: str = ""
    example_dialogues: list[str] = Field(default_factory=list, max_length=40)
    tags: list[str] = Field(default_factory=list, max_length=80)
    lorebook_entries: list[LorebookEntry] = Field(default_factory=list, max_length=MAX_LOREBOOK_ENTRIES)
    visual_assets: list[VisualAssetHint] = Field(default_factory=list, max_length=MAX_VISUAL_ASSETS)
    voice_hints: list[VoiceProfileHint] = Field(default_factory=list, max_length=12)
    mood_growth_preferences: MoodGrowthPreferences = Field(default_factory=MoodGrowthPreferences)
    image_style_references: list[ImageStyleReference] = Field(default_factory=list, max_length=24)
    warnings: list[str] = Field(default_factory=list, max_length=40)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [part.strip() for part in value.split(",")]
        if not isinstance(value, list):
            return []
        normalized: list[str] = []
        for item in value:
            text = str(item).strip().lower()
            if text and text not in normalized:
                normalized.append(text[:80])
        return normalized[:80]
