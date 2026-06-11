import { browser } from '$app/environment';
import { writable } from 'svelte/store';

export type ReflectionFrequency = 'low' | 'balanced' | 'high';
export type ReflectionSensitivity = 'conservative' | 'balanced' | 'responsive';
export type ContextBudgetPreset = 'lean' | 'balanced' | 'deep';

export interface MemoryReflectionSettings {
  longTermMemoryEnabled: boolean;
  selfReflectionEnabled: boolean;
  reflectionFrequency: ReflectionFrequency;
  reflectionSensitivity: ReflectionSensitivity;
  growthNotificationsEnabled: boolean;
  contextBudgetPreset: ContextBudgetPreset;
  updatedAt: string | null;
}

const STORAGE_KEY = 'reverie.memoryReflectionSettings.v1';

export const DEFAULT_MEMORY_REFLECTION_SETTINGS: MemoryReflectionSettings = {
  longTermMemoryEnabled: true,
  selfReflectionEnabled: true,
  reflectionFrequency: 'balanced',
  reflectionSensitivity: 'balanced',
  growthNotificationsEnabled: true,
  contextBudgetPreset: 'balanced',
  updatedAt: null
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const isReflectionFrequency = (value: unknown): value is ReflectionFrequency =>
  value === 'low' || value === 'balanced' || value === 'high';

const isReflectionSensitivity = (value: unknown): value is ReflectionSensitivity =>
  value === 'conservative' || value === 'balanced' || value === 'responsive';

const isContextBudgetPreset = (value: unknown): value is ContextBudgetPreset =>
  value === 'lean' || value === 'balanced' || value === 'deep';

const normalizeSettings = (value: unknown): MemoryReflectionSettings => {
  if (!isRecord(value)) return DEFAULT_MEMORY_REFLECTION_SETTINGS;

  return {
    longTermMemoryEnabled:
      typeof value.longTermMemoryEnabled === 'boolean'
        ? value.longTermMemoryEnabled
        : DEFAULT_MEMORY_REFLECTION_SETTINGS.longTermMemoryEnabled,
    selfReflectionEnabled:
      typeof value.selfReflectionEnabled === 'boolean'
        ? value.selfReflectionEnabled
        : DEFAULT_MEMORY_REFLECTION_SETTINGS.selfReflectionEnabled,
    reflectionFrequency: isReflectionFrequency(value.reflectionFrequency)
      ? value.reflectionFrequency
      : DEFAULT_MEMORY_REFLECTION_SETTINGS.reflectionFrequency,
    reflectionSensitivity: isReflectionSensitivity(value.reflectionSensitivity)
      ? value.reflectionSensitivity
      : DEFAULT_MEMORY_REFLECTION_SETTINGS.reflectionSensitivity,
    growthNotificationsEnabled:
      typeof value.growthNotificationsEnabled === 'boolean'
        ? value.growthNotificationsEnabled
        : DEFAULT_MEMORY_REFLECTION_SETTINGS.growthNotificationsEnabled,
    contextBudgetPreset: isContextBudgetPreset(value.contextBudgetPreset)
      ? value.contextBudgetPreset
      : DEFAULT_MEMORY_REFLECTION_SETTINGS.contextBudgetPreset,
    updatedAt: typeof value.updatedAt === 'string' ? value.updatedAt : null
  };
};

const loadSettings = (): MemoryReflectionSettings => {
  if (!browser) return DEFAULT_MEMORY_REFLECTION_SETTINGS;

  try {
    const rawSettings = window.localStorage.getItem(STORAGE_KEY);
    if (!rawSettings) return DEFAULT_MEMORY_REFLECTION_SETTINGS;

    return normalizeSettings(JSON.parse(rawSettings));
  } catch {
    return DEFAULT_MEMORY_REFLECTION_SETTINGS;
  }
};

const persistSettings = (settings: MemoryReflectionSettings) => {
  if (!browser) return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
};

function createSettingsStore() {
  const store = writable<MemoryReflectionSettings>(loadSettings());

  const commit = (updater: (settings: MemoryReflectionSettings) => MemoryReflectionSettings) => {
    store.update((settings) => {
      const nextSettings = {
        ...updater(settings),
        updatedAt: new Date().toISOString()
      } satisfies MemoryReflectionSettings;
      persistSettings(nextSettings);
      return nextSettings;
    });
  };

  return {
    subscribe: store.subscribe,
    setLongTermMemoryEnabled(enabled: boolean) {
      commit((settings) => ({ ...settings, longTermMemoryEnabled: enabled }));
    },
    setSelfReflectionEnabled(enabled: boolean) {
      commit((settings) => ({ ...settings, selfReflectionEnabled: enabled }));
    },
    setReflectionFrequency(frequency: ReflectionFrequency) {
      commit((settings) => ({ ...settings, reflectionFrequency: frequency }));
    },
    setReflectionSensitivity(sensitivity: ReflectionSensitivity) {
      commit((settings) => ({ ...settings, reflectionSensitivity: sensitivity }));
    },
    setGrowthNotificationsEnabled(enabled: boolean) {
      commit((settings) => ({ ...settings, growthNotificationsEnabled: enabled }));
    },
    setContextBudgetPreset(preset: ContextBudgetPreset) {
      commit((settings) => ({ ...settings, contextBudgetPreset: preset }));
    },
    resetMemoryReflectionSettings() {
      const resetSettings = {
        ...DEFAULT_MEMORY_REFLECTION_SETTINGS,
        updatedAt: new Date().toISOString()
      } satisfies MemoryReflectionSettings;
      persistSettings(resetSettings);
      store.set(resetSettings);
    }
  };
}

export const settingsStore = createSettingsStore();
