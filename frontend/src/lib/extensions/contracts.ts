export type ExtensionCapability =
  | 'custom_panel'
  | 'commands'
  | 'settings'
  | 'tts_voice'
  | 'image_workflow'
  | 'growth_modifier'
  | 'character_import'
  | 'vn_state'
  | 'memory_read'
  | 'memory_write';

export type ExtensionEventScope = 'core' | 'vn' | 'tts' | 'image' | 'growth' | 'memory' | 'settings' | 'character';
export type ExtensionStatus = 'enabled' | 'disabled' | 'errored';

export interface ExtensionError {
  extension_id: string;
  code: string;
  message: string;
  details: Record<string, unknown>;
  occurred_at: string;
}

export interface ExtensionCommandContract {
  command_id: string;
  title: string;
  description: string;
  scope: ExtensionEventScope;
  required_capabilities: ExtensionCapability[];
  payload_schema: Record<string, unknown>;
}

export interface ExtensionPanelContract {
  panel_id: string;
  title: string;
  placement: 'sidebar' | 'settings' | 'character' | 'vn';
  component_key: string;
  required_capabilities: ExtensionCapability[];
}

export interface ExtensionSettingField {
  key: string;
  label: string;
  description: string;
  kind: 'boolean' | 'number' | 'text' | 'select';
  default: boolean | number | string | null;
  min_value: number | null;
  max_value: number | null;
  options: string[];
}

export interface ExtensionSettingsSection {
  section_id: string;
  title: string;
  description: string;
  fields: ExtensionSettingField[];
}

export interface ExtensionManifest {
  schema_version: 'extension.v1';
  extension_id: string;
  name: string;
  version: string;
  description: string;
  author: string | null;
  enabled_by_default: boolean;
  capabilities: ExtensionCapability[];
  commands: ExtensionCommandContract[];
  panels: ExtensionPanelContract[];
  settings_sections: ExtensionSettingsSection[];
  tts_voices: Array<Record<string, unknown>>;
  image_workflows: Array<Record<string, unknown>>;
  growth_modifiers: Array<Record<string, unknown>>;
  metadata: Record<string, unknown>;
}

export interface ExtensionRead {
  manifest: ExtensionManifest;
  status: ExtensionStatus;
  errors: ExtensionError[];
}

export interface ExtensionRegistryResponse {
  schema_version: 'extension-registry.v1';
  extensions: ExtensionRead[];
  errors: ExtensionError[];
}

export interface ExtensionEvent<TPayload extends Record<string, unknown> = Record<string, unknown>> {
  event_id: string;
  event_type: string;
  scope: ExtensionEventScope;
  source: string;
  payload: TPayload;
  created_at: string;
}

export interface ExtensionCommandRequest<TPayload extends Record<string, unknown> = Record<string, unknown>> {
  command_id: string;
  source_extension_id: string;
  scope: ExtensionEventScope;
  payload: TPayload;
}

export interface ExtensionCommandResult {
  accepted: boolean;
  event: ExtensionEvent | null;
  error: ExtensionError | null;
}

export interface ImportedLoreEntry {
  id: string;
  title: string;
  triggers: string[];
  priority: number;
  budget_tokens: number;
  facts: string[];
  limits: string[];
  source: string;
}

export interface ImportedAssetReference {
  id: string;
  kind: 'avatar' | 'sprite' | 'background' | 'reference' | 'audio';
  label: string;
  path: string | null;
  mime_type: string | null;
  metadata: Record<string, unknown>;
}

export interface CharacterImportProfile {
  schema_version: 'character-import.v1';
  name: string;
  description: string | null;
  personality: string | null;
  scenario: string | null;
  first_message: string | null;
  example_dialogue: string | null;
  lorebook_entries: ImportedLoreEntry[];
  visual_assets: ImportedAssetReference[];
  voice_hints: Record<string, unknown>;
  mood_preferences: Record<string, unknown>;
  growth_preferences: Record<string, unknown>;
  image_style_references: Record<string, unknown>;
  preserved_unknown_fields: Record<string, unknown>;
  warnings: string[];
}
