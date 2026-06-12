import { browser } from '$app/environment';
import { get, writable } from 'svelte/store';

export type ReflectionFrequency = 'low' | 'balanced' | 'high';
export type ReflectionSensitivity = 'conservative' | 'balanced' | 'responsive';
export type ContextBudgetPreset = 'gentle' | 'balanced' | 'roomy';
export type TTSLatencyPreset = 'quality' | 'balanced' | 'speed';
export type ImageDefaultPreset = 'preview_8gb' | 'balanced_8gb' | 'high_8gb';

export interface MemoryReflectionSettings {
  longTermMemoryEnabled: boolean;
  selfReflectionEnabled: boolean;
  reflectionFrequency: ReflectionFrequency;
  reflectionSensitivity: ReflectionSensitivity;
  growthNotificationsEnabled: boolean;
  contextBudgetPreset: ContextBudgetPreset;
  ttsEnabled: boolean;
  ttsAutoPlay: boolean;
  ttsVolume: number;
  ttsSpeed: number;
  ttsLatencyPreset: TTSLatencyPreset;
  imageAutoGenerateOnAssistant: boolean;
  imageDefaultPreset: ImageDefaultPreset;
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
  contextBudgetPreset: 'balanced',
  ttsEnabled: true,
  ttsAutoPlay: true,
  ttsVolume: 0.86,
  ttsSpeed: 1,
  ttsLatencyPreset: 'balanced',
  imageAutoGenerateOnAssistant: false,
  imageDefaultPreset: 'preview_8gb'
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

const isTTSLatencyPreset = (value: unknown): value is TTSLatencyPreset =>
  value === 'quality' || value === 'balanced' || value === 'speed';

const isImageDefaultPreset = (value: unknown): value is ImageDefaultPreset =>
  value === 'preview_8gb' || value === 'balanced_8gb' || value === 'high_8gb';

const toBoolean = (value: unknown, fallback: boolean): boolean => (typeof value === 'boolean' ? value : fallback);
const clampNumber = (value: unknown, fallback: number, min: number, max: number): number => {
  const numberValue = typeof value === 'number' && Number.isFinite(value) ? value : fallback;
  return Math.min(max, Math.max(min, numberValue));
};

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
  ttsEnabled: toBoolean(value.ttsEnabled, DEFAULT_MEMORY_REFLECTION_SETTINGS.ttsEnabled),
  ttsAutoPlay: toBoolean(value.ttsAutoPlay, DEFAULT_MEMORY_REFLECTION_SETTINGS.ttsAutoPlay),
  ttsVolume: clampNumber(value.ttsVolume, DEFAULT_MEMORY_REFLECTION_SETTINGS.ttsVolume, 0, 1),
  ttsSpeed: clampNumber(value.ttsSpeed, DEFAULT_MEMORY_REFLECTION_SETTINGS.ttsSpeed, 0.75, 1.35),
  ttsLatencyPreset: isTTSLatencyPreset(value.ttsLatencyPreset)
    ? value.ttsLatencyPreset
    : DEFAULT_MEMORY_REFLECTION_SETTINGS.ttsLatencyPreset,
  imageAutoGenerateOnAssistant: toBoolean(
    value.imageAutoGenerateOnAssistant,
    DEFAULT_MEMORY_REFLECTION_SETTINGS.imageAutoGenerateOnAssistant
  ),
  imageDefaultPreset: isImageDefaultPreset(value.imageDefaultPreset)
    ? value.imageDefaultPreset
    : DEFAULT_MEMORY_REFLECTION_SETTINGS.imageDefaultPreset,
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
    ttsEnabled: state.ttsEnabled,
    ttsAutoPlay: state.ttsAutoPlay,
    ttsVolume: state.ttsVolume,
    ttsSpeed: state.ttsSpeed,
    ttsLatencyPreset: state.ttsLatencyPreset,
    imageAutoGenerateOnAssistant: state.imageAutoGenerateOnAssistant,
    imageDefaultPreset: state.imageDefaultPreset,
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
    setTTSEnabled(ttsEnabled: boolean) {
      save({ ttsEnabled });
    },
    setTTSAutoPlay(ttsAutoPlay: boolean) {
      save({ ttsAutoPlay });
    },
    setTTSVolume(ttsVolume: number) {
      save({ ttsVolume: clampNumber(ttsVolume, DEFAULT_MEMORY_REFLECTION_SETTINGS.ttsVolume, 0, 1) });
    },
    setTTSSpeed(ttsSpeed: number) {
      save({ ttsSpeed: clampNumber(ttsSpeed, DEFAULT_MEMORY_REFLECTION_SETTINGS.ttsSpeed, 0.75, 1.35) });
    },
    setTTSLatencyPreset(ttsLatencyPreset: TTSLatencyPreset) {
      save({ ttsLatencyPreset });
    },
    setImageAutoGenerateOnAssistant(imageAutoGenerateOnAssistant: boolean) {
      save({ imageAutoGenerateOnAssistant });
    },
    setImageDefaultPreset(imageDefaultPreset: ImageDefaultPreset) {
      save({ imageDefaultPreset });
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
