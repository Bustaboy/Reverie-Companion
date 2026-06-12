export const EXTENSION_API_VERSION = '2026.06.v1' as const;
export type ExtensionCapability = 'custom_panel' | 'command' | 'tts_voice' | 'image_workflow' | 'growth_modifier' | 'settings_section' | 'character_importer' | 'event_subscriber';
export type ExtensionPermission = 'read_conversation_context' | 'read_character_profile' | 'suggest_memory' | 'suggest_growth_modifier' | 'request_tts_voice' | 'request_image_workflow' | 'register_ui';
export type ExtensionCommandTarget = 'vn' | 'tts' | 'image' | 'growth' | 'memory' | 'character' | 'system';
export type ExtensionSettingKind = 'text' | 'textarea' | 'boolean' | 'number' | 'select';
export interface ExtensionSettingOption { value: string; label: string; }
export interface ExtensionSettingDefinition { key: string; label: string; kind: ExtensionSettingKind; description?: string | null; default?: string | number | boolean | null; options?: ExtensionSettingOption[]; }
export interface ExtensionSettingsSection { id: string; title: string; description?: string | null; settings: ExtensionSettingDefinition[]; }
export interface ExtensionCommandDefinition { id: string; title: string; description?: string | null; target: ExtensionCommandTarget; payload_schema?: Record<string, unknown>; }
export interface ExtensionPanelDefinition { id: string; title: string; slot: 'sidebar' | 'settings' | 'character' | 'vn' | 'memory' | 'growth'; description?: string | null; }
export interface ExtensionManifest { id: string; name: string; version: string; api_version: string; description?: string | null; author?: string | null; capabilities: ExtensionCapability[]; permissions: ExtensionPermission[]; commands: ExtensionCommandDefinition[]; panels: ExtensionPanelDefinition[]; settings_sections: ExtensionSettingsSection[]; }
export interface RegisteredExtension { manifest: ExtensionManifest; status: 'active' | 'disabled' | 'failed'; loaded_at: string; error?: string | null; }
export interface ExtensionRegistryResponse { api_version: string; extensions: RegisteredExtension[]; }
export interface ExtensionCommandRequest { command_id: string; source?: string; target: ExtensionCommandTarget; payload?: Record<string, unknown>; }
export interface ExtensionEventEnvelope { event_id: string; event_type: string; source: string; target: ExtensionCommandTarget | 'extension'; occurred_at: string; payload: Record<string, unknown>; }
export interface ExtensionCommandResult { accepted: boolean; event?: ExtensionEventEnvelope | null; error?: { code: string; message: string; retryable?: boolean } | null; }
export interface LorebookEntry { id: string; keys: string[]; secondary_keys: string[]; content: string; comment?: string | null; enabled: boolean; constant: boolean; selective: boolean; insertion_order: number; metadata: Record<string, unknown>; }
export interface CharacterImportPreview { importer_version: string; source_format: string; name: string; description: string; personality: string; scenario: string; first_message: string; example_dialogues: string[]; tags: string[]; lorebook_entries: LorebookEntry[]; visual_assets: Array<Record<string, unknown>>; voice_hints: Array<Record<string, unknown>>; mood_growth_preferences: Record<string, unknown>; image_style_references: Array<Record<string, unknown>>; warnings: string[]; raw_metadata: Record<string, unknown>; }
