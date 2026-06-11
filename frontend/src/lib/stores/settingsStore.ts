import { browser } from '$app/environment';
import { get, writable } from 'svelte/store';

export type ReflectionFrequency = 'low' | 'balanced' | 'high';
export type ReflectionSensitivity = 'conservative' | 'balanced' | 'responsive';
export type ContextBudgetPreset = 'gentle' | 'balanced' | 'roomy';

export interface MemoryReflectionSettings {
  longTermMemoryEnabled: boolean;
  selfReflectionEnabled: boolean;
  reflectionFrequency: ReflectionFrequency;
  reflectionSensitivity: ReflectionSensitivity;
  growthNotificationsEnabled: boolean;
  contextBudgetPreset: ContextBudgetPreset;
}

export interface SettingsState extends MemoryReflectionSettings {
  savedAt: Date | null;
}

type PersistedSettings = Partial<MemoryReflectionSettings> & {
  savedAt?: string | null;
};

const STORAGE_KEY = 'reverie.memoryReflectionSettings.v1';

export const DEFAULT_MEMORY_REFLECTION_SETTINGS: MemoryReflectionSettings = {
  longTermMemoryEnabled: true,
  selfReflectionEnabled: true,
  reflectionFrequency: 'balanced',
  reflectionSensitivity: 'balanced',
  growthNotificationsEnabled: true,
  contextBudgetPreset: 'balanced'
};

const INITIAL_STATE: SettingsState = {
  ...DEFAULT_MEMORY_REFLECTION_SETTINGS,
  savedAt: null
};

const isReflectionFrequency = (value: unknown): value is ReflectionFrequency =>
  value === 'low' || value === 'balanced' || value === 'high';

const isReflectionSensitivity = (value: unknown): value is ReflectionSensitivity =>
  value === 'conservative' || value === 'balanced' || value === 'responsive';

const isContextBudgetPreset = (value: unknown): value is ContextBudgetPreset =>
  value === 'gentle' || value === 'balanced' || value === 'roomy';

const toBoolean = (value: unknown, fallback: boolean): boolean => (typeof value === 'boolean' ? value : fallback);

const normalizePersistedSettings = (value: PersistedSettings): SettingsState => ({
  longTermMemoryEnabled: toBoolean(
    value.longTermMemoryEnabled,
    DEFAULT_MEMORY_REFLECTION_SETTINGS.longTermMemoryEnabled
  ),
  selfReflectionEnabled: toBoolean(value.selfReflectionEnabled, DEFAULT_MEMORY_REFLECTION_SETTINGS.selfReflectionEnabled),
  reflectionFrequency: isReflectionFrequency(value.reflectionFrequency)
    ? value.reflectionFrequency
    : DEFAULT_MEMORY_REFLECTION_SETTINGS.reflectionFrequency,
  reflectionSensitivity: isReflectionSensitivity(value.reflectionSensitivity)
    ? value.reflectionSensitivity
    : DEFAULT_MEMORY_REFLECTION_SETTINGS.reflectionSensitivity,
  growthNotificationsEnabled: toBoolean(
    value.growthNotificationsEnabled,
    DEFAULT_MEMORY_REFLECTION_SETTINGS.growthNotificationsEnabled
  ),
  contextBudgetPreset: isContextBudgetPreset(value.contextBudgetPreset)
    ? value.contextBudgetPreset
    : DEFAULT_MEMORY_REFLECTION_SETTINGS.contextBudgetPreset,
  savedAt: typeof value.savedAt === 'string' ? new Date(value.savedAt) : null
});

const readPersistedSettings = (): SettingsState => {
  if (!browser) return INITIAL_STATE;

  const rawSettings = window.localStorage.getItem(STORAGE_KEY);
  if (!rawSettings) return INITIAL_STATE;

  try {
    return normalizePersistedSettings(JSON.parse(rawSettings) as PersistedSettings);
  } catch {
    return INITIAL_STATE;
  }
};

const persistSettings = (state: SettingsState) => {
  if (!browser) return;

  const payload: PersistedSettings = {
    longTermMemoryEnabled: state.longTermMemoryEnabled,
    selfReflectionEnabled: state.selfReflectionEnabled,
    reflectionFrequency: state.reflectionFrequency,
    reflectionSensitivity: state.reflectionSensitivity,
    growthNotificationsEnabled: state.growthNotificationsEnabled,
    contextBudgetPreset: state.contextBudgetPreset,
    savedAt: state.savedAt?.toISOString() ?? null
  };

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
};

function createSettingsStore() {
  const store = writable<SettingsState>(readPersistedSettings());

  if (browser) {
    store.subscribe((state) => persistSettings(state));
  }

  const save = (patch: Partial<MemoryReflectionSettings>) => {
    store.update((state) => ({
      ...state,
      ...patch,
      savedAt: new Date()
    }));
  };

  return {
    subscribe: store.subscribe,
    setLongTermMemoryEnabled(enabled: boolean) {
      save({ longTermMemoryEnabled: enabled });
    },
    setSelfReflectionEnabled(enabled: boolean) {
      save({ selfReflectionEnabled: enabled });
    },
    setReflectionFrequency(reflectionFrequency: ReflectionFrequency) {
      save({ reflectionFrequency });
    },
    setReflectionSensitivity(reflectionSensitivity: ReflectionSensitivity) {
      save({ reflectionSensitivity });
    },
    setGrowthNotificationsEnabled(enabled: boolean) {
      save({ growthNotificationsEnabled: enabled });
    },
    setContextBudgetPreset(contextBudgetPreset: ContextBudgetPreset) {
      save({ contextBudgetPreset });
    },
    resetMemoryReflectionSettings() {
      save(DEFAULT_MEMORY_REFLECTION_SETTINGS);
    },
    getSnapshot() {
      return get(store);
    }
  };
}

export const settingsStore = createSettingsStore();
