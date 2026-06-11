import { get, writable } from 'svelte/store';
import { GrowthServiceError, growthService } from '$lib/api/growthService';
import type { PersonalLoRAExample, PersonalLoRAJob, PersonalLoRASettings } from '$lib/types/growth';

interface GrowthState {
  settings: PersonalLoRASettings | null;
  currentJob: PersonalLoRAJob | null;
  examples: PersonalLoRAExample[];
  counts: {
    pending_review: number;
    approved: number;
    rejected: number;
  };
  loadState: 'idle' | 'loading' | 'refreshing' | 'loaded' | 'error';
  actionState: 'idle' | 'saving' | 'training' | 'error';
  error: string | null;
  lastLoadedAt: Date | null;
}

const INITIAL_STATE: GrowthState = {
  settings: null,
  currentJob: null,
  examples: [],
  counts: { pending_review: 0, approved: 0, rejected: 0 },
  loadState: 'idle',
  actionState: 'idle',
  error: null,
  lastLoadedAt: null
};

const friendlyError = (error: unknown): string => {
  if (error instanceof GrowthServiceError) return error.message;
  return 'Something went wrong while opening Training.';
};

const normalizeCounts = (examples: PersonalLoRAExample[], counts?: Partial<GrowthState['counts']>) => ({
  pending_review: counts?.pending_review ?? examples.filter((example) => example.status === 'pending_review').length,
  approved: counts?.approved ?? examples.filter((example) => example.status === 'approved').length,
  rejected: counts?.rejected ?? examples.filter((example) => example.status === 'rejected').length
});

function createGrowthStore() {
  const store = writable<GrowthState>(INITIAL_STATE);
  let activeLoad = false;

  const load = async (options: { force?: boolean } = {}) => {
    const current = get(store);
    if (activeLoad || (!options.force && current.loadState === 'loaded')) return;

    activeLoad = true;
    store.update((state) => ({
      ...state,
      loadState: state.examples.length > 0 ? 'refreshing' : 'loading',
      error: null
    }));

    try {
      const response = await growthService.getPersonalLoRAStatus();
      store.update((state) => ({
        ...state,
        settings: response.settings,
        currentJob: response.current_job ?? null,
        examples: response.examples ?? [],
        counts: normalizeCounts(response.examples ?? [], response.counts),
        loadState: 'loaded',
        actionState: 'idle',
        error: null,
        lastLoadedAt: new Date()
      }));
    } catch (error) {
      store.update((state) => ({
        ...state,
        loadState: 'error',
        actionState: 'error',
        error: friendlyError(error)
      }));
    } finally {
      activeLoad = false;
    }
  };

  const replaceExample = (updated: PersonalLoRAExample) => {
    store.update((state) => {
      const examples = state.examples.map((example) => (example.item_id === updated.item_id ? updated : example));
      return { ...state, examples, counts: normalizeCounts(examples), actionState: 'idle', error: null };
    });
  };

  const runAction = async <T>(action: () => Promise<T>, onSuccess: (value: T) => void, busy: GrowthState['actionState'] = 'saving') => {
    store.update((state) => ({ ...state, actionState: busy, error: null }));
    try {
      const value = await action();
      onSuccess(value);
    } catch (error) {
      store.update((state) => ({ ...state, actionState: 'error', error: friendlyError(error) }));
    }
  };

  return {
    subscribe: store.subscribe,
    load,
    refresh() {
      return load({ force: true });
    },
    updateSettings(updates: Partial<PersonalLoRASettings>) {
      return runAction(
        () => growthService.updatePersonalLoRASettings(updates),
        (settings) => store.update((state) => ({ ...state, settings, actionState: 'idle', error: null }))
      );
    },
    approveExample(itemId: string) {
      return runAction(() => growthService.approvePersonalLoRAExample(itemId), replaceExample);
    },
    rejectExample(itemId: string) {
      return runAction(() => growthService.rejectPersonalLoRAExample(itemId), replaceExample);
    },
    deleteExample(itemId: string) {
      return runAction(() => growthService.deletePersonalLoRAExample(itemId), replaceExample);
    },
    startTraining() {
      return runAction(
        () => growthService.startPersonalLoRATraining(),
        (currentJob) => store.update((state) => ({ ...state, currentJob, actionState: 'idle', error: null })),
        'training'
      );
    },
    stopTraining() {
      return runAction(
        () => growthService.stopPersonalLoRATraining(),
        (currentJob) => store.update((state) => ({ ...state, currentJob, actionState: 'idle', error: null })),
        'training'
      );
    },
    clearError() {
      store.update((state) => ({ ...state, error: null, actionState: 'idle' }));
    }
  };
}

export const growthStore = createGrowthStore();
