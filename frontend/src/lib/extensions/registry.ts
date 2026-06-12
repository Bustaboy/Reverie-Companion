import { browser } from '$app/environment';
import { derived, writable } from 'svelte/store';
import type { ExtensionManifest, ExtensionRead, ExtensionSettingsSection } from './contracts';

const CORE_EXTENSION: ExtensionRead = {
  manifest: {
    schema_version: 'extension.v1',
    extension_id: 'reverie.core',
    name: 'Reverie Core Extension Surface',
    version: '1.0.0',
    description: 'Built-in typed contracts for settings, commands, VN, TTS, images, growth, memory, and character import.',
    author: 'Vision Entertainment',
    enabled_by_default: true,
    capabilities: [
      'custom_panel',
      'commands',
      'settings',
      'tts_voice',
      'image_workflow',
      'growth_modifier',
      'character_import',
      'vn_state',
      'memory_read',
      'memory_write'
    ],
    commands: [],
    panels: [],
    settings_sections: [
      {
        section_id: 'developer-foundations',
        title: 'Extension foundations',
        description: 'Local manifest loading, event history, and typed command dispatch are available for future extensions without enabling remote code.',
        fields: [
          {
            key: 'show_diagnostics',
            label: 'Show extension diagnostics',
            description: 'Keep lightweight local diagnostics visible while developing extension manifests.',
            kind: 'boolean',
            default: false,
            min_value: null,
            max_value: null,
            options: []
          }
        ]
      }
    ],
    tts_voices: [],
    image_workflows: [],
    growth_modifiers: [],
    metadata: {}
  },
  status: 'enabled',
  errors: []
};

const extensionsStore = writable<ExtensionRead[]>([CORE_EXTENSION]);
const errorsStore = writable<string | null>(null);

const sanitizeManifest = (manifest: ExtensionManifest): ExtensionManifest => ({
  ...manifest,
  settings_sections: manifest.settings_sections.slice(0, 20).map((section) => ({
    ...section,
    fields: section.fields.slice(0, 20)
  }))
});

export const extensionRegistry = {
  extensions: { subscribe: extensionsStore.subscribe },
  errors: { subscribe: errorsStore.subscribe },

  registerLocal(manifest: ExtensionManifest, status: ExtensionRead['status'] = 'enabled') {
    const extension: ExtensionRead = { manifest: sanitizeManifest(manifest), status, errors: [] };
    extensionsStore.update((current) => {
      const withoutDuplicate = current.filter((item) => item.manifest.extension_id !== manifest.extension_id);
      return [...withoutDuplicate, extension].sort((a, b) => a.manifest.name.localeCompare(b.manifest.name));
    });
  },

  setBackendExtensions(extensions: ExtensionRead[]) {
    const sanitized = extensions.map((extension) => ({
      ...extension,
      manifest: sanitizeManifest(extension.manifest)
    }));
    extensionsStore.set(sanitized.length > 0 ? sanitized : [CORE_EXTENSION]);
  },

  reportError(message: string) {
    errorsStore.set(message);
  }
};

export const enabledExtensions = derived(extensionsStore, ($extensions) =>
  $extensions.filter((extension) => extension.status === 'enabled')
);

export const extensionSettingsSections = derived(enabledExtensions, ($extensions) =>
  $extensions.flatMap((extension): Array<ExtensionSettingsSection & { extensionId: string; extensionName: string }> =>
    extension.manifest.settings_sections.map((section) => ({
      ...section,
      extensionId: extension.manifest.extension_id,
      extensionName: extension.manifest.name
    }))
  )
);

if (browser) {
  queueMicrotask(() => extensionsStore.update((extensions) => extensions));
}
