"""Typed extension contracts for Reverie's local-first extension surface."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_EXTENSION_ID_LENGTH = 80
MAX_TEXT_FIELD_LENGTH = 2_000
ContractVersion = Literal["extension.v1"]


class ExtensionCapability(StrEnum):
    """Capabilities an extension may request from core systems."""

    CUSTOM_PANEL = "custom_panel"
    COMMANDS = "commands"
    SETTINGS = "settings"
    TTS_VOICE = "tts_voice"
    IMAGE_WORKFLOW = "image_workflow"
    GROWTH_MODIFIER = "growth_modifier"
    CHARACTER_IMPORT = "character_import"
    VN_STATE = "vn_state"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"


class ExtensionEventScope(StrEnum):
    """Core domains exposed through the event/command bus."""

    CORE = "core"
    VN = "vn"
    TTS = "tts"
    IMAGE = "image"
    GROWTH = "growth"
    MEMORY = "memory"
    SETTINGS = "settings"
    CHARACTER = "character"


class ExtensionStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERRORED = "errored"


class ExtensionError(BaseModel):
    """Non-fatal extension error captured without crashing core systems."""

    extension_id: str
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExtensionCommandContract(BaseModel):
    """Command an extension may expose to the typed bus."""

    command_id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=MAX_TEXT_FIELD_LENGTH)
    scope: ExtensionEventScope = ExtensionEventScope.CORE
    required_capabilities: list[ExtensionCapability] = Field(default_factory=list, max_length=12)
    payload_schema: dict[str, Any] = Field(default_factory=dict)


class ExtensionPanelContract(BaseModel):
    """UI panel contribution. Frontend renders only trusted built-in component keys."""

    panel_id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=120)
    placement: Literal["sidebar", "settings", "character", "vn"] = "sidebar"
    component_key: str = Field(..., min_length=1, max_length=120)
    required_capabilities: list[ExtensionCapability] = Field(
        default_factory=lambda: [ExtensionCapability.CUSTOM_PANEL], max_length=12
    )


class ExtensionSettingField(BaseModel):
    """Declarative setting field for lightweight extension settings UI."""

    key: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=MAX_TEXT_FIELD_LENGTH)
    kind: Literal["boolean", "number", "text", "select"]
    default: bool | float | str | None = None
    min_value: float | None = None
    max_value: float | None = None
    options: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_field_shape(self) -> "ExtensionSettingField":
        if self.kind == "select" and not self.options:
            raise ValueError("Select extension settings require at least one option.")
        if self.kind != "select" and self.options:
            raise ValueError("Only select extension settings may declare options.")
        if self.kind == "number" and (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise ValueError("Number setting min_value cannot exceed max_value.")
        return self


class ExtensionSettingsSection(BaseModel):
    """Settings contribution rendered by the frontend settings page."""

    section_id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=MAX_TEXT_FIELD_LENGTH)
    fields: list[ExtensionSettingField] = Field(default_factory=list, max_length=20)


class ExtensionTTSVoiceContract(BaseModel):
    voice_id: str = Field(..., min_length=1, max_length=120)
    name: str = Field(..., min_length=1, max_length=120)
    backend: str = Field(..., min_length=1, max_length=80)
    character_id: str | None = Field(default=None, max_length=120)
    mood_tags: list[str] = Field(default_factory=list, max_length=24)


class ExtensionImageWorkflowContract(BaseModel):
    workflow_id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=MAX_TEXT_FIELD_LENGTH)
    quality_presets: list[str] = Field(default_factory=list, max_length=12)
    supports_character_references: bool = True
    estimated_vram_gb: float | None = Field(default=None, ge=0, le=24)


class ExtensionGrowthModifierContract(BaseModel):
    modifier_id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=MAX_TEXT_FIELD_LENGTH)
    affected_domains: list[ExtensionEventScope] = Field(default_factory=list, max_length=12)
    requires_user_review: bool = True


class ExtensionManifest(BaseModel):
    """Versioned manifest loaded from local extension metadata only."""

    schema_version: ContractVersion = "extension.v1"
    extension_id: str = Field(..., min_length=1, max_length=MAX_EXTENSION_ID_LENGTH)
    name: str = Field(..., min_length=1, max_length=120)
    version: str = Field(..., min_length=1, max_length=40)
    description: str = Field(default="", max_length=MAX_TEXT_FIELD_LENGTH)
    author: str | None = Field(default=None, max_length=120)
    enabled_by_default: bool = False
    capabilities: list[ExtensionCapability] = Field(default_factory=list, max_length=20)
    commands: list[ExtensionCommandContract] = Field(default_factory=list, max_length=40)
    panels: list[ExtensionPanelContract] = Field(default_factory=list, max_length=20)
    settings_sections: list[ExtensionSettingsSection] = Field(default_factory=list, max_length=20)
    tts_voices: list[ExtensionTTSVoiceContract] = Field(default_factory=list, max_length=40)
    image_workflows: list[ExtensionImageWorkflowContract] = Field(default_factory=list, max_length=20)
    growth_modifiers: list[ExtensionGrowthModifierContract] = Field(default_factory=list, max_length=20)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("extension_id")
    @classmethod
    def extension_id_must_be_safe(cls, value: str) -> str:
        if not all(character.isalnum() or character in {"_", "-", "."} for character in value):
            raise ValueError("Extension IDs may contain only letters, numbers, '.', '_' and '-'.")
        return value


class ExtensionRead(BaseModel):
    manifest: ExtensionManifest
    status: ExtensionStatus
    errors: list[ExtensionError] = Field(default_factory=list)


class ExtensionRegistryResponse(BaseModel):
    schema_version: Literal["extension-registry.v1"] = "extension-registry.v1"
    extensions: list[ExtensionRead]
    errors: list[ExtensionError] = Field(default_factory=list)


class ExtensionEvent(BaseModel):
    """Typed event emitted by core or an extension with bounded payloads."""

    event_id: str = Field(..., min_length=1, max_length=120)
    event_type: str = Field(..., min_length=1, max_length=120)
    scope: ExtensionEventScope
    source: str = Field(..., min_length=1, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExtensionCommandRequest(BaseModel):
    command_id: str = Field(..., min_length=1, max_length=120)
    source_extension_id: str = Field(..., min_length=1, max_length=MAX_EXTENSION_ID_LENGTH)
    scope: ExtensionEventScope = ExtensionEventScope.CORE
    payload: dict[str, Any] = Field(default_factory=dict)


class ExtensionCommandResult(BaseModel):
    accepted: bool
    event: ExtensionEvent | None = None
    error: ExtensionError | None = None


class ImportedLoreEntry(BaseModel):
    id: str
    title: str
    triggers: list[str] = Field(default_factory=list)
    priority: int = Field(default=50, ge=0, le=100)
    budget_tokens: int = Field(default=180, ge=40, le=800)
    facts: list[str] = Field(default_factory=list)
    limits: list[str] = Field(default_factory=list)
    source: str = "sillytavern"


class ImportedAssetReference(BaseModel):
    id: str
    kind: Literal["avatar", "sprite", "background", "reference", "audio"]
    label: str
    path: str | None = None
    mime_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CharacterImportProfile(BaseModel):
    """Normalized preview produced from a SillyTavern/character-card payload."""

    schema_version: Literal["character-import.v1"] = "character-import.v1"
    name: str
    description: str | None = None
    personality: str | None = None
    scenario: str | None = None
    first_message: str | None = None
    example_dialogue: str | None = None
    lorebook_entries: list[ImportedLoreEntry] = Field(default_factory=list)
    visual_assets: list[ImportedAssetReference] = Field(default_factory=list)
    voice_hints: dict[str, Any] = Field(default_factory=dict)
    mood_preferences: dict[str, Any] = Field(default_factory=dict)
    growth_preferences: dict[str, Any] = Field(default_factory=dict)
    image_style_references: dict[str, Any] = Field(default_factory=dict)
    preserved_unknown_fields: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class CharacterImportRequest(BaseModel):
    source_format: Literal["sillytavern", "character_card", "auto"] = "auto"
    payload: dict[str, Any]
