import { derived, get, writable } from 'svelte/store';
import { growthService, GrowthServiceError } from '$lib/api/growthService';
import type {
  LoRATrainingExample,
  LoRATrainingJob,
  LoRATrainingStatusSummary,
  PersonalLoRACounts,
  PersonalLoRASettings,
  PersonalLoRASettingsUpdate,
  PersonalLoRAStatusResponse
} from '$lib/types/growth';

export type GrowthLoadState = 'idle' | 'loading' | 'refreshing' | 'loaded' | 'error';
export type GrowthActionState = 'idle' | 'saving' | 'reviewing' | 'training';

export interface GrowthState {
  settings: PersonalLoRASettings | null;
  currentJob: LoRATrainingJob | null;
  trainingStatus: LoRATrainingStatusSummary | null;
  examples: LoRATrainingExample[];
  counts: PersonalLoRACounts;
  loadState: GrowthLoadState;
  actionState: GrowthActionState;
  error: string | null;
  lastLoadedAt: Date | null;
}

export interface PersonalLoRAReviewView {
  pendingExamples: LoRATrainingExample[];
  approvedExamples: LoRATrainingExample[];
  recentlyReviewedExamples: LoRATrainingExample[];
  collectionOptedIn: boolean;
  trainingOptedIn: boolean;
  reviewRequired: boolean;
  applyApprovalRequired: boolean;
  autoTrainingEnabled: boolean;
  trainingActive: boolean;
  canStartTraining: boolean;
  canAutoTrainNow: boolean;
}

const INITIAL_COUNTS: PersonalLoRACounts = {
  pending_review: 0,
  approved: 0,
  rejected: 0
};

const INITIAL_STATE: GrowthState = {
  settings: null,
  currentJob: null,
  trainingStatus: null,
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

export const isPersonalLoRATrainingActive = (job: LoRATrainingJob | null): boolean =>
  job?.status === 'queued' || job?.status === 'running';

const mergeStatus = (state: GrowthState, response: PersonalLoRAStatusResponse): GrowthState => ({
  ...state,
  settings: response.settings,
  currentJob: response.current_job,
  trainingStatus: response.training_status,
  examples: response.examples,
  counts: response.counts,
  loadState: 'loaded',
  error: null,
  lastLoadedAt: new Date()
});

function createGrowthStore() {
  const store = writable<GrowthState>(INITIAL_STATE);
  let activeLoadId = 0;

  const refreshStatus = async () => {
    const requestId = ++activeLoadId;
    const response = await growthService.getPersonalLoRAStatus();
    if (requestId !== activeLoadId) return;
    store.update((state) => mergeStatus(state, response));
  };

  const loadPersonalLoRA = async (options: { force?: boolean } = {}) => {
    const current = get(store);
    if (!options.force && (current.loadState === 'loaded' || current.loadState === 'loading' || current.loadState === 'refreshing')) return;

    const requestId = ++activeLoadId;
    store.update((state) => ({
      ...state,
      loadState: state.examples.length > 0 ? 'refreshing' : 'loading',
      error: null
    }));

    try {
      const response = await growthService.getPersonalLoRAStatus();
      if (requestId !== activeLoadId) return;
      store.update((state) => mergeStatus(state, response));
    } catch (error) {
      if (requestId !== activeLoadId) return;
      store.update((state) => ({
        ...state,
        loadState: 'error',
        error: friendlyError(error)
      }));
    }
  };

  const runAction = async (actionState: GrowthActionState, action: () => Promise<unknown>) => {
    store.update((state) => ({ ...state, actionState, error: null }));
    try {
      await action();
      await refreshStatus();
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
    evaluateAutoTraining() {
      return runAction('training', () => growthService.evaluateAutoTraining());
    },
    approveAdapter(adapterId: string) {
      return runAction('reviewing', () => growthService.approveAdapter(adapterId));
    },
    rejectAdapter(adapterId: string) {
      return runAction('reviewing', () => growthService.rejectAdapter(adapterId));
    },
    clearError() {
      store.update((state) => ({ ...state, error: null, loadState: state.examples.length ? 'loaded' : 'idle' }));
    }
  };
}

export const growthStore = createGrowthStore();

export const personalLoRAReviewView = derived<typeof growthStore, PersonalLoRAReviewView>(growthStore, ($growthStore) => {
  const pendingExamples = $growthStore.examples.filter(
    (example) => (example.status ?? 'pending_review') === 'pending_review'
  );
  const approvedExamples = $growthStore.examples.filter((example) => example.status === 'approved');
  const trainingOptedIn = $growthStore.settings?.training_opt_in ?? false;
  const trainingActive = isPersonalLoRATrainingActive($growthStore.currentJob);
  const minTrainingExamples = $growthStore.settings?.min_training_examples ?? 1;

  return {
    pendingExamples,
    approvedExamples,
    recentlyReviewedExamples: $growthStore.examples.filter((example) => example.status === 'rejected').slice(0, 3),
    collectionOptedIn: $growthStore.settings?.collection_opt_in ?? false,
    trainingOptedIn,
    reviewRequired: $growthStore.settings?.require_review_before_training ?? true,
    applyApprovalRequired: $growthStore.settings?.require_approval_before_applying ?? true,
    autoTrainingEnabled: $growthStore.settings?.auto_training_enabled ?? false,
    trainingActive,
    canStartTraining: trainingOptedIn && approvedExamples.length >= minTrainingExamples && $growthStore.actionState === 'idle' && !trainingActive,
    canAutoTrainNow:
      trainingOptedIn &&
      ($growthStore.settings?.auto_training_enabled ?? false) &&
      approvedExamples.length >= minTrainingExamples &&
      $growthStore.actionState === 'idle' &&
      !trainingActive
  };
});
