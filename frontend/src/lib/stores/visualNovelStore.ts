import { derived, get, writable } from 'svelte/store';
import type { ChatMessage } from '$lib/types/chat';
import type {
  CharacterVisualManifest,
  GrowthVisualModifier,
  ResolvedVisualScene,
  SceneMediaCapabilities,
  VisualState
} from '$lib/types/visualNovel';
import { expressionManager } from '$lib/visualNovel/expressionManager';
import { defaultVisualManifest, preloadVisualSceneAssets, resolveVisualScene } from '$lib/visualNovel/manifest';
import { sceneMediaService } from '$lib/visualNovel/sceneMediaService';

export interface VisualNovelState {
  manifest: CharacterVisualManifest;
  baseVisualState: VisualState;
  activeVisualState: VisualState;
  growthModifier: GrowthVisualModifier | null;
  lastAssistantMessageId: string | null;
  mediaCapabilities: SceneMediaCapabilities;
  mediaStatusMessage: string | null;
}

export interface VisualNovelView {
  manifest: CharacterVisualManifest;
  visualState: VisualState;
  growthModifier: GrowthVisualModifier | null;
  scene: ResolvedVisualScene;
  mediaCapabilities: SceneMediaCapabilities;
  mediaStatusMessage: string | null;
}

const INITIAL_VISUAL_STATE = expressionManager.normalizeVisualState(undefined);

const INITIAL_STATE: VisualNovelState = {
  manifest: defaultVisualManifest,
  baseVisualState: INITIAL_VISUAL_STATE,
  activeVisualState: INITIAL_VISUAL_STATE,
  growthModifier: null,
  lastAssistantMessageId: null,
  mediaCapabilities: {
    available: false,
    modes: [],
    resourcePresets: ['preview_8gb', 'balanced_8gb']
  },
  mediaStatusMessage: null
};

function createVisualNovelStore() {
  const store = writable<VisualNovelState>(INITIAL_STATE);
  let growthDecayTimer: ReturnType<typeof setTimeout> | null = null;

  const clearGrowthDecayTimer = () => {
    if (growthDecayTimer) {
      clearTimeout(growthDecayTimer);
      growthDecayTimer = null;
    }
  };

  const preloadCurrentScene = (state: VisualNovelState) => {
    preloadVisualSceneAssets(resolveVisualScene(state.manifest, state.activeVisualState));
  };

  const scheduleGrowthDecay = (modifier: GrowthVisualModifier | null) => {
    clearGrowthDecayTimer();
    if (!modifier) {
      return;
    }

    const timeoutMs = Math.max(0, modifier.expiresAt - Date.now());
    growthDecayTimer = setTimeout(() => {
      store.update((state) => {
        const activeVisualState = expressionManager.withoutTemporaryGrowth(state.baseVisualState);
        const nextState = {
          ...state,
          activeVisualState,
          growthModifier: null
        };
        preloadCurrentScene(nextState);
        return nextState;
      });
      growthDecayTimer = null;
    }, timeoutMs);
  };

  return {
    subscribe: store.subscribe,
    applyVisualState(visualState: VisualState | undefined, assistantMessage?: Pick<ChatMessage, 'id'>) {
      const normalized = expressionManager.normalizeVisualState(visualState);
      const baseVisualState = expressionManager.withoutTemporaryGrowth(normalized);
      const growthModifier = expressionManager.createGrowthModifier(normalized);
      const activeVisualState = expressionManager.applyGrowthModifier(baseVisualState, growthModifier);

      store.update((state) => {
        const nextState = {
          ...state,
          baseVisualState,
          activeVisualState,
          growthModifier,
          lastAssistantMessageId: assistantMessage?.id ?? state.lastAssistantMessageId,
          mediaStatusMessage: null
        };
        preloadCurrentScene(nextState);
        return nextState;
      });
      scheduleGrowthDecay(growthModifier);
    },
    setManifest(manifest: CharacterVisualManifest) {
      store.update((state) => {
        const nextState = { ...state, manifest };
        preloadCurrentScene(nextState);
        return nextState;
      });
    },
    async refreshMediaCapabilities() {
      const mediaCapabilities = await sceneMediaService.checkCapabilities();
      store.update((state) => ({
        ...state,
        mediaCapabilities,
        mediaStatusMessage: mediaCapabilities.available ? null : (mediaCapabilities.message ?? null)
      }));
    },
    async requestCurrentSceneMedia() {
      const state = get(store);
      const job = await sceneMediaService.createSceneJob({
        characterId: state.activeVisualState.characterId,
        sceneId: `scene_${state.lastAssistantMessageId ?? 'current'}`,
        intent: 'illustrate_current_scene',
        visualState: state.activeVisualState,
        resourcePreset: 'preview_8gb'
      });
      store.update((current) => ({ ...current, mediaStatusMessage: job.message }));
    },
    clearMediaStatus() {
      store.update((state) => ({ ...state, mediaStatusMessage: null }));
    }
  };
}

export const visualNovelStore = createVisualNovelStore();

export const visualNovelView = derived<typeof visualNovelStore, VisualNovelView>(visualNovelStore, ($visualNovelStore) => ({
  manifest: $visualNovelStore.manifest,
  visualState: $visualNovelStore.activeVisualState,
  growthModifier: $visualNovelStore.growthModifier,
  scene: resolveVisualScene($visualNovelStore.manifest, $visualNovelStore.activeVisualState),
  mediaCapabilities: $visualNovelStore.mediaCapabilities,
  mediaStatusMessage: $visualNovelStore.mediaStatusMessage
}));
