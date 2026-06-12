import { derived, get, writable } from 'svelte/store';
import { DEFAULT_CHARACTER_VISUAL_MANIFEST } from '$lib/visual-novel/defaultManifest';
import { expressionManager } from '$lib/visual-novel/ExpressionManager';
import type {
  CharacterVisualManifest,
  NormalizedVisualState,
  ResolvedVisualNovelScene,
  VisualStateMetadata
} from '$lib/types/visualNovel';

export interface VisualNovelState {
  manifest: CharacterVisualManifest;
  currentVisualState: NormalizedVisualState;
  fullImmersive: boolean;
  /** Small LRU of image URLs that failed to decode so the resolver stops retrying them. */
  failedAssetUrls: string[];
}

const FAILED_ASSET_CACHE_LIMIT = 16;

const initialManifest = DEFAULT_CHARACTER_VISUAL_MANIFEST;
const initialVisualState = expressionManager.normalizeState(initialManifest);

const INITIAL_STATE: VisualNovelState = {
  manifest: initialManifest,
  currentVisualState: initialVisualState,
  fullImmersive: false,
  failedAssetUrls: []
};

const addFailedAssetUrl = (urls: string[], url: string): string[] => {
  const trimmedUrl = url.trim();
  if (!trimmedUrl) return urls;

  const withoutDuplicate = urls.filter((item) => item !== trimmedUrl);
  return [...withoutDuplicate, trimmedUrl].slice(-FAILED_ASSET_CACHE_LIMIT);
};

function createVisualNovelStore() {
  const store = writable<VisualNovelState>(INITIAL_STATE);

  const scene = derived(store, ($store): ResolvedVisualNovelScene => {
    const failedAssetUrls = new Set($store.failedAssetUrls);
    return expressionManager.resolveScene($store.manifest, $store.currentVisualState, failedAssetUrls);
  });

  return {
    subscribe: store.subscribe,
    scene: { subscribe: scene.subscribe },
    applyVisualState(metadata?: VisualStateMetadata | null) {
      if (!metadata) return;

      store.update((state) => ({
        ...state,
        currentVisualState: expressionManager.normalizeState(state.manifest, metadata)
      }));
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
