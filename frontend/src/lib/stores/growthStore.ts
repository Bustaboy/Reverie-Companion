import { get, writable } from 'svelte/store';
import { growthService, GrowthServiceError } from '$lib/api/growthService';
import type {
  LoRATrainingExample,
  LoRATrainingJob,
  PersonalLoRACounts,
  PersonalLoRASettings,
  PersonalLoRASettingsUpdate
} from '$lib/types/growth';

interface GrowthState {
  settings: PersonalLoRASettings | null;
  currentJob: LoRATrainingJob | null;
  examples: LoRATrainingExample[];
  counts: PersonalLoRACounts;
  loadState: 'idle' | 'loading' | 'refreshing' | 'loaded' | 'error';
  actionState: 'idle' | 'saving' | 'reviewing' | 'training';
  error: string | null;
  lastLoadedAt: Date | null;
}

const INITIAL_COUNTS: PersonalLoRACounts = {
  pending_review: 0,
  approved: 0,
  rejected: 0
};

const INITIAL_STATE: GrowthState = {
  settings: null,
  currentJob: null,
  examples: [],
  counts: INITIAL_COUNTS,
  loadState: 'idle',
  actionState: 'idle',
  error: null,
  lastLoadedAt: null
};

const friendlyError = (error: unknown): string => {
  if (error instanceof GrowthServiceError) return error.message;
  return 'Something went wrong while opening the growth controls.';
};

function createGrowthStore() {
  const store = writable<GrowthState>(INITIAL_STATE);
  let activeRequest: AbortController | null = null;

  const loadPersonalLoRA = async (options: { force?: boolean } = {}) => {
    const current = get(store);
    if (activeRequest || (!options.force && current.loadState === 'loaded')) return;

    const controller = new AbortController();
    activeRequest = controller;

    store.update((state) => ({
      ...state,
      loadState: state.examples.length > 0 ? 'refreshing' : 'loading',
      error: null
    }));

    try {
      const response = await growthService.getPersonalLoRAStatus();
      if (controller.signal.aborted) return;

      store.update((state) => ({
        ...state,
        settings: response.settings,
        currentJob: response.current_job,
        examples: response.examples,
        counts: response.counts,
        loadState: 'loaded',
        error: null,
        lastLoadedAt: new Date()
      }));
    } catch (error) {
      if (controller.signal.aborted) return;
      store.update((state) => ({
        ...state,
        loadState: 'error',
        error: friendlyError(error)
      }));
    } finally {
      if (activeRequest === controller) activeRequest = null;
    }
  };

  const refreshAfterAction = async () => {
    try {
      const response = await growthService.getPersonalLoRAStatus();
      store.update((state) => ({
        ...state,
        settings: response.settings,
        currentJob: response.current_job,
        examples: response.examples,
        counts: response.counts,
        loadState: 'loaded',
        error: null,
        lastLoadedAt: new Date()
      }));
    } catch (error) {
      store.update((state) => ({ ...state, error: friendlyError(error) }));
    }
  };

  const runAction = async (actionState: GrowthState['actionState'], action: () => Promise<unknown>) => {
    store.update((state) => ({ ...state, actionState, error: null }));
    try {
      await action();
      await refreshAfterAction();
    } catch (error) {
      store.update((state) => ({ ...state, error: friendlyError(error) }));
    } finally {
      store.update((state) => ({ ...state, actionState: 'idle' }));
    }
  };

  return {
    subscribe: store.subscribe,
    loadPersonalLoRA,
    refresh() {
      return loadPersonalLoRA({ force: true });
    },
    updateSettings(update: PersonalLoRASettingsUpdate) {
      return runAction('saving', () => growthService.updatePersonalLoRASettings(update));
    },
    approveExample(itemId: string) {
      return runAction('reviewing', () => growthService.approveExample(itemId));
    },
    rejectExample(itemId: string) {
      return runAction('reviewing', () => growthService.rejectExample(itemId));
    },
    deleteExample(itemId: string) {
      return runAction('reviewing', () => growthService.deleteExample(itemId));
    },
    startTraining() {
      return runAction('training', () => growthService.startTraining());
    },
    clearError() {
      store.update((state) => ({ ...state, error: null, loadState: state.examples.length ? 'loaded' : 'idle' }));
    }
  };
}

export const growthStore = createGrowthStore();
