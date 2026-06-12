import { derived, get, writable } from 'svelte/store';
import { DEFAULT_CHARACTER_VISUAL_MANIFEST } from '$lib/visual-novel/defaultManifest';
import { expressionManager } from '$lib/visual-novel/ExpressionManager';
import type {
  CharacterVisualManifest,
  NormalizedVisualState,
  ResolvedVisualNovelScene,
  VisualGrowthModifier,
  VisualStateMetadata
} from '$lib/types/visualNovel';

export interface VisualNovelState {
  manifest: CharacterVisualManifest;
  currentVisualState: NormalizedVisualState;
  fullImmersive: boolean;
  /** Temporary emphasis from a final SSE visual_state growth_cue. */
  growthModifier: VisualGrowthModifier | null;
  /** Small LRU of image URLs that failed to decode so the resolver stops retrying them. */
  failedAssetUrls: string[];
}

const FAILED_ASSET_CACHE_LIMIT = 16;
const MIN_GROWTH_MODIFIER_MS = 30_000;
const MAX_GROWTH_MODIFIER_MS = 60_000;
const DEFAULT_GROWTH_MODIFIER_MS = 45_000;
const DEFAULT_GROWTH_INTENSITY = 0.5;
const MIN_GROWTH_INTENSITY = 0.2;

const initialManifest = DEFAULT_CHARACTER_VISUAL_MANIFEST;
const initialVisualState = expressionManager.normalizeState(initialManifest);

const INITIAL_STATE: VisualNovelState = {
  manifest: initialManifest,
  currentVisualState: initialVisualState,
  fullImmersive: false,
  growthModifier: null,
  failedAssetUrls: []
};

const addFailedAssetUrl = (urls: string[], url: string): string[] => {
  const trimmedUrl = url.trim();
  if (!trimmedUrl) return urls;

  const withoutDuplicate = urls.filter((item) => item !== trimmedUrl);
  return [...withoutDuplicate, trimmedUrl].slice(-FAILED_ASSET_CACHE_LIMIT);
};

const clampNumber = (value: number | undefined, fallback: number, min: number, max: number): number => {
  if (value === undefined || !Number.isFinite(value)) return fallback;
  return Math.min(max, Math.max(min, value));
};

const clampDecayMs = (value: number | undefined): number =>
  Math.round(clampNumber(value, DEFAULT_GROWTH_MODIFIER_MS, MIN_GROWTH_MODIFIER_MS, MAX_GROWTH_MODIFIER_MS));

const normalizeIntensity = (value: number | undefined): number =>
  clampNumber(value, DEFAULT_GROWTH_INTENSITY, MIN_GROWTH_INTENSITY, 1);

const createGrowthModifier = (metadata: VisualStateMetadata, now = Date.now()): VisualGrowthModifier | null => {
  if (!metadata.growthCue) return null;

  const decayMs = clampDecayMs(metadata.decayMs);
  return {
    cue: metadata.growthCue,
    intensity: normalizeIntensity(metadata.intensity),
    startedAt: now,
    expiresAt: now + decayMs,
    decayMs
  };
};

function createVisualNovelStore() {
  const store = writable<VisualNovelState>(INITIAL_STATE);
  let growthDecayTimer: ReturnType<typeof globalThis.setTimeout> | null = null;

  const clearGrowthDecayTimer = () => {
    if (!growthDecayTimer) return;
    globalThis.clearTimeout(growthDecayTimer);
    growthDecayTimer = null;
  };

  const scheduleGrowthModifierDecay = (modifier: VisualGrowthModifier) => {
    clearGrowthDecayTimer();
    growthDecayTimer = globalThis.setTimeout(() => {
      store.update((state) => (state.growthModifier?.startedAt === modifier.startedAt ? { ...state, growthModifier: null } : state));
      growthDecayTimer = null;
    }, modifier.decayMs);
  };

  const scene = derived(store, ($store): ResolvedVisualNovelScene => {
    const failedAssetUrls = new Set($store.failedAssetUrls);
    return expressionManager.resolveScene($store.manifest, $store.currentVisualState, failedAssetUrls);
  });

  return {
    subscribe: store.subscribe,
    scene: { subscribe: scene.subscribe },
    applyVisualState(metadata?: VisualStateMetadata | null) {
      if (!metadata) return;

      const growthModifier = createGrowthModifier(metadata);
      store.update((state) => ({
        ...state,
        currentVisualState: expressionManager.normalizeState(state.manifest, metadata),
        growthModifier: growthModifier ?? state.growthModifier
      }));

      if (growthModifier) {
        scheduleGrowthModifierDecay(growthModifier);
      }
    },
    setFullImmersive(enabled: boolean) {
      store.update((state) => ({ ...state, fullImmersive: enabled }));
    },
    toggleFullImmersive() {
      store.update((state) => ({ ...state, fullImmersive: !state.fullImmersive }));
    },
    markAssetFailed(src?: string) {
      if (!src) return;
      store.update((state) => ({
        ...state,
        failedAssetUrls: addFailedAssetUrl(state.failedAssetUrls, src)
      }));
    },
    getSnapshot(): VisualNovelState {
      return get(store);
    }
  };
}

export const visualNovelStore = createVisualNovelStore();
export const visualNovelScene = visualNovelStore.scene;
