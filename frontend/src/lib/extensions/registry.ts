import { derived, writable } from 'svelte/store';
import type { ExtensionManifest, ExtensionRegistryResponse, ExtensionSettingsSection, RegisteredExtension } from './types';
const builtinCoreExtension: RegisteredExtension = {
  manifest: {
    id: 'reverie.frontend.extensibility', name: 'Frontend Extensibility Surface', version: '0.1.0', api_version: '2026.06.v1',
    description: 'Local UI registry for safe settings sections, lightweight panels, and command dispatch metadata.', author: 'Vision Entertainment',
    capabilities: ['settings_section', 'custom_panel', 'command', 'event_subscriber'], permissions: ['register_ui'], commands: [], panels: [],
    settings_sections: [{ id: 'frontend_sandbox', title: 'Frontend Extension Sandbox', description: 'Controls for local UI extension diagnostics. A bad extension section is rendered as data, not arbitrary code.', settings: [{ key: 'diagnosticBadges', label: 'Show diagnostic badges', kind: 'boolean', description: 'Show extension IDs and API versions while developing local panels.', default: false }] }]
  },
  status: 'active', loaded_at: new Date().toISOString(), error: null
};
const extensions = writable<RegisteredExtension[]>([builtinCoreExtension]);
const errors = writable<string | null>(null);
const validateManifest = (manifest: ExtensionManifest): ExtensionManifest => {
  if (!manifest.id || !manifest.name || !manifest.version) throw new Error('Extension manifest is missing id, name, or version.');
  return { ...manifest, capabilities: manifest.capabilities ?? [], permissions: manifest.permissions ?? [], commands: manifest.commands ?? [], panels: manifest.panels ?? [], settings_sections: manifest.settings_sections ?? [] };
};
export const extensionRegistry = {
  subscribe: extensions.subscribe,
  errors,
  register(manifest: ExtensionManifest) {
    try {
      const safeManifest = validateManifest(manifest);
      extensions.update((items) => [...items.filter((item) => item.manifest.id !== safeManifest.id), { manifest: safeManifest, status: 'active', loaded_at: new Date().toISOString(), error: null }]);
      errors.set(null);
    } catch (error) { errors.set(error instanceof Error ? error.message : 'Extension registration failed.'); }
  },
  async refreshFromBackend() {
    try {
      const response = await fetch('/extensions');
      if (!response.ok) throw new Error(`Extension registry failed with HTTP ${response.status}.`);
      const payload = (await response.json()) as ExtensionRegistryResponse;
      extensions.update((items) => {
        const localOnly = items.filter((item) => item.manifest.id.startsWith('reverie.frontend.'));
        const merged = new Map<string, RegisteredExtension>();
        [...localOnly, ...payload.extensions].forEach((item) => merged.set(item.manifest.id, item));
        return [...merged.values()];
      });
      errors.set(null);
    } catch (error) { errors.set(error instanceof Error ? error.message : 'Could not load backend extension registry.'); }
  }
};
export const extensionSettingsSections = derived(extensions, ($extensions): ExtensionSettingsSection[] =>
  $extensions.flatMap((extension) => extension.status === 'active' ? extension.manifest.settings_sections.map((section) => ({ ...section, id: `${extension.manifest.id}.${section.id}`, title: section.title, description: section.description ?? extension.manifest.description })) : [])
);
