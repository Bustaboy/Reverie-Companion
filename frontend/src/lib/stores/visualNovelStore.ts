import { derived, get, writable } from 'svelte/store';
import { DEFAULT_CHARACTER_VISUAL_MANIFEST } from '$lib/visual-novel/defaultManifest';
import { expressionManager } from '$lib/visual-novel/ExpressionManager';
import type {
  CharacterVisualManifest,
  NormalizedVisualState,
  ResolvedVisualNovelScene,
  VisualStateMetadata,
  GrowthVisualModifier
} from '$lib/types/visualNovel';

export interface VisualNovelState {
  manifest: CharacterVisualManifest;
  currentVisualState: NormalizedVisualState;
  fullImmersive: boolean;
  /** Small LRU of image URLs that failed to decode so the resolver stops retrying them. */
  failedAssetUrls: string[];
  growthModifier?: GrowthVisualModifier;
}

const FAILED_ASSET_CACHE_LIMIT = 16;
const GROWTH_MODIFIER_DECAY_MS = 45_000;

const initialManifest = DEFAULT_CHARACTER_VISUAL_MANIFEST;
const initialVisualState = expressionManager.normalizeState(initialManifest);

const INITIAL_STATE: VisualNovelState = {
  manifest: initialManifest,
  currentVisualState: initialVisualState,
  fullImmersive: false,
  failedAssetUrls: [],
  growthModifier: undefined
};

const addFailedAssetUrl = (urls: string[], url: string): string[] => {
  const trimmedUrl = url.trim();
  if (!trimmedUrl) return urls;

  const withoutDuplicate = urls.filter((item) => item !== trimmedUrl);
  return [...withoutDuplicate, trimmedUrl].slice(-FAILED_ASSET_CACHE_LIMIT);
};

function createVisualNovelStore() {
  const store = writable<VisualNovelState>(INITIAL_STATE);
  let growthModifierTimer: ReturnType<typeof globalThis.setTimeout> | undefined;

  const clearGrowthModifierTimer = () => {
    if (growthModifierTimer) {
      globalThis.clearTimeout(growthModifierTimer);
      growthModifierTimer = undefined;
    }
  };

  const scheduleGrowthModifierDecay = () => {
    clearGrowthModifierTimer();
    growthModifierTimer = globalThis.setTimeout(() => {
      store.update((state) => ({ ...state, growthModifier: undefined }));
      growthModifierTimer = undefined;
    }, GROWTH_MODIFIER_DECAY_MS);
  };

  const scene = derived(store, ($store): ResolvedVisualNovelScene => {
    const failedAssetUrls = new Set($store.failedAssetUrls);
    const resolved = expressionManager.resolveScene($store.manifest, $store.currentVisualState, failedAssetUrls);
    return { ...resolved, growthModifier: $store.growthModifier };
  });

  return {
    subscribe: store.subscribe,
    scene: { subscribe: scene.subscribe },
    applyVisualState(metadata?: VisualStateMetadata | null) {
      if (!metadata) return;

      store.update((state) => {
        const currentVisualState = expressionManager.normalizeState(state.manifest, metadata);
        const now = Date.now();
        const growthModifier = currentVisualState.growthCue
          ? {
              cue: currentVisualState.growthCue,
              startedAt: now,
              expiresAt: now + GROWTH_MODIFIER_DECAY_MS,
              intensity: Math.min(1, Math.max(0.35, currentVisualState.confidence || 0.55))
            }
          : state.growthModifier;

        if (currentVisualState.growthCue) {
          scheduleGrowthModifierDecay();
        }

        return {
          ...state,
          currentVisualState,
          growthModifier
        };
      });
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
