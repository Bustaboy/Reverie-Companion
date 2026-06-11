import { get, writable } from 'svelte/store';
import { JournalServiceError, journalService } from '$lib/api/journalService';
import type { JournalEntry } from '$lib/types/journal';

export type JournalLoadState = 'idle' | 'loading' | 'refreshing' | 'ready' | 'error';

export interface JournalState {
  entries: JournalEntry[];
  selectedEntryId: string | null;
  loadState: JournalLoadState;
  error: string | null;
  lastLoadedAt: Date | null;
}

const INITIAL_STATE: JournalState = {
  entries: [],
  selectedEntryId: null,
  loadState: 'idle',
  error: null,
  lastLoadedAt: null
};

const toFriendlyError = (error: unknown): string => {
  if (error instanceof JournalServiceError) return error.message;
  return 'Something went wrong while opening the reflection journal.';
};

function createJournalStore() {
  const store = writable<JournalState>(INITIAL_STATE);
  let activeController: AbortController | null = null;

  const loadEntries = async ({ force = false }: { force?: boolean } = {}) => {
    const current = get(store);
    if (current.loadState === 'loading' || current.loadState === 'refreshing') return;
    if (!force && current.loadState === 'ready') return;

    const controller = new AbortController();
    activeController = controller;

    store.update((state) => ({
      ...state,
      loadState: state.entries.length > 0 ? 'refreshing' : 'loading',
      error: null
    }));

    try {
      const entries = await journalService.getRecentEntries({ limit: 25, signal: controller.signal });
      store.update((state) => {
        const selectedStillExists = entries.some((entry) => entry.entry_id === state.selectedEntryId);
        return {
          ...state,
          entries,
          selectedEntryId: selectedStillExists ? state.selectedEntryId : entries[0]?.entry_id ?? null,
          loadState: 'ready',
          error: null,
          lastLoadedAt: new Date()
        };
      });
    } catch (error) {
      store.update((state) => ({
        ...state,
        loadState: 'error',
        error: toFriendlyError(error)
      }));
    } finally {
      if (activeController === controller) activeController = null;
    }
  };

  return {
    subscribe: store.subscribe,
    open() {
      void loadEntries();
    },
    refresh() {
      activeController?.abort();
      activeController = null;
      void loadEntries({ force: true });
    },
    selectEntry(entryId: string) {
      store.update((state) => ({ ...state, selectedEntryId: entryId }));
    },
    clearError() {
      store.update((state) => ({ ...state, error: null, loadState: state.entries.length > 0 ? 'ready' : 'idle' }));
    }
  };
}

export const journalStore = createJournalStore();
