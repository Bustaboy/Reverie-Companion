import { browser } from '$app/environment';
import { writable } from 'svelte/store';

export type ExtensionSettingValue = string | number | boolean | null;
export type ExtensionSettingsState = Record<string, ExtensionSettingValue>;
const STORAGE_KEY = 'reverie.extensionSettings.v1';

const readSettings = (): ExtensionSettingsState => {
  if (!browser) return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ExtensionSettingsState) : {};
  } catch {
    return {};
  }
};

const persist = (state: ExtensionSettingsState) => {
  if (browser) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
};

function createExtensionSettingsStore() {
  const store = writable<ExtensionSettingsState>(readSettings());
  if (browser) store.subscribe(persist);
  return {
    subscribe: store.subscribe,
    setValue(key: string, value: ExtensionSettingValue) {
      store.update((state) => ({ ...state, [key]: value }));
    },
    resetSection(sectionId: string) {
      store.update((state) => Object.fromEntries(Object.entries(state).filter(([key]) => !key.startsWith(`${sectionId}.`))));
    }
  };
}

export const extensionSettingsStore = createExtensionSettingsStore();
