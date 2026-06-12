import { get, writable } from 'svelte/store';
import { journalService, JournalServiceError } from '$lib/api/journalService';
import type { JournalEntry } from '$lib/types/journal';

interface JournalState {
  entries: JournalEntry[];
  selectedEntryId: string | null;
  loadState: 'idle' | 'loading' | 'refreshing' | 'loaded' | 'error';
  actionState: 'idle' | 'reflecting';
  error: string | null;
  lastLoadedAt: Date | null;
}

const INITIAL_STATE: JournalState = {
  entries: [],
  selectedEntryId: null,
  loadState: 'idle',
  actionState: 'idle',
  error: null,
  lastLoadedAt: null
};

const friendlyError = (error: unknown): string => {
  if (error instanceof JournalServiceError) return error.message;
  return 'Something went wrong while opening the journal.';
};

function createJournalStore() {
  const store = writable<JournalState>(INITIAL_STATE);
  let activeRequest: AbortController | null = null;

  const loadEntries = async (options: { force?: boolean } = {}) => {
    const current = get(store);
    if (activeRequest || (!options.force && current.loadState === 'loaded')) return;

    const controller = new AbortController();
    activeRequest = controller;

    store.update((state) => ({
      ...state,
      loadState: state.entries.length > 0 ? 'refreshing' : 'loading',
      error: null
    }));

    try {
      const entries = await journalService.getRecentEntries(30);
      if (controller.signal.aborted) return;

      store.update((state) => {
        const selectedStillExists = entries.some((entry) => entry.entry_id === state.selectedEntryId);
        return {
          ...state,
          entries,
          selectedEntryId: selectedStillExists ? state.selectedEntryId : entries[0]?.entry_id ?? null,
          loadState: 'loaded',
          error: null,
          lastLoadedAt: new Date()
        };
      });
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

  return {
    subscribe: store.subscribe,
    loadEntries,
    refresh() {
      return loadEntries({ force: true });
    },
    selectEntry(entryId: string) {
      store.update((state) => ({ ...state, selectedEntryId: entryId }));
    },
    async triggerReflection(messages: { role: 'user' | 'assistant'; content: string }[]) {
      if (messages.length === 0) {
        store.update((state) => ({
          ...state,
          error: 'Start a conversation first, then Reverie can write a reflection from it.'
        }));
        return;
      }

      store.update((state) => ({ ...state, actionState: 'reflecting', error: null }));
      try {
        const entry = await journalService.triggerReflection(messages);
        store.update((state) => ({
          ...state,
          entries: [entry, ...state.entries.filter((existing) => existing.entry_id !== entry.entry_id)],
          selectedEntryId: entry.entry_id,
          loadState: 'loaded',
          error: null,
          lastLoadedAt: new Date()
        }));
      } catch (error) {
        store.update((state) => ({ ...state, error: friendlyError(error) }));
      } finally {
        store.update((state) => ({ ...state, actionState: 'idle' }));
      }
    },
    clearError() {
      store.update((state) => ({ ...state, error: null, loadState: state.entries.length ? 'loaded' : 'idle' }));
    }
  };
}

export const journalStore = createJournalStore();
