import { derived, get, writable } from 'svelte/store';
import type { CharacterVisualManifest, ResolvedVisualScene, VisualStateMetadata } from '$lib/types/visualNovel';
import { CharacterVisualResolver, fallbackVisualManifest } from '$lib/visual-novel/visualManifest';

export interface VisualNovelState {
  enabled: boolean;
  immersive: boolean;
  manifest: CharacterVisualManifest;
  visualState: VisualStateMetadata;
}

const initialVisualState: VisualStateMetadata = {
  characterId: fallbackVisualManifest.characterId,
  expression: fallbackVisualManifest.defaults?.expression ?? 'neutral',
  pose: fallbackVisualManifest.defaults?.pose ?? 'idle',
  background: fallbackVisualManifest.defaults?.background ?? 'default',
  updatedAt: new Date(),
  source: 'fallback'
};

const createVisualNovelStore = () => {
  const store = writable<VisualNovelState>({
    enabled: false,
    immersive: false,
    manifest: fallbackVisualManifest,
    visualState: initialVisualState
  });
  const resolver = new CharacterVisualResolver(fallbackVisualManifest);

  const scene = derived(store, ($store): ResolvedVisualScene => resolver.resolveScene($store.visualState));
  const applyVisualState = (metadata: VisualStateMetadata | undefined): void => {
    if (!metadata) return;
    store.update((state) => ({
      ...state,
      visualState: {
        ...state.visualState,
        ...metadata,
        updatedAt: metadata.updatedAt ?? new Date()
      }
    }));
  };

  return {
    subscribe: store.subscribe,
    scene: { subscribe: scene.subscribe },
    setEnabled(enabled: boolean) {
      store.update((state) => ({ ...state, enabled }));
    },
    toggleEnabled() {
      store.update((state) => ({ ...state, enabled: !state.enabled }));
    },
    setImmersive(immersive: boolean) {
      store.update((state) => ({ ...state, immersive }));
    },
    setManifest(manifest: CharacterVisualManifest | null | undefined) {
      const safeManifest = manifest ?? fallbackVisualManifest;
      resolver.setManifest(safeManifest);
      store.update((state) => ({
        ...state,
        manifest: safeManifest,
        visualState: {
          ...state.visualState,
          characterId: safeManifest.characterId,
          expression: state.visualState.expression ?? safeManifest.defaults?.expression ?? 'neutral',
          pose: state.visualState.pose ?? safeManifest.defaults?.pose ?? 'idle',
          background: state.visualState.background ?? safeManifest.defaults?.background ?? 'default'
        }
      }));
    },
    applyVisualState,
    setExpression(expression: string) {
      applyVisualState({ expression, source: 'manual', updatedAt: new Date() });
    },
    setPose(pose: string) {
      applyVisualState({ pose, source: 'manual', updatedAt: new Date() });
    },
    resetVisuals() {
      store.update((state) => ({
        ...state,
        visualState: {
          characterId: state.manifest.characterId,
          expression: state.manifest.defaults?.expression ?? 'neutral',
          pose: state.manifest.defaults?.pose ?? 'idle',
          background: state.manifest.defaults?.background ?? 'default',
          updatedAt: new Date(),
          source: 'fallback'
        }
      }));
    },
    getSnapshot() {
      return get(store);
    },
    getResolvedScene() {
      return resolver.resolveScene(get(store).visualState);
    },
    resolveEmergencyFallback(slot: 'expression' | 'pose' | 'background', id?: string) {
      return resolver.resolveEmergencyFallback(slot, id);
    }
  };
};

export const visualNovelStore = createVisualNovelStore();
