import { get, writable } from 'svelte/store';
import { memoryService, MemoryServiceError } from '$lib/api/memoryService';
import type { MemoryBulkDeleteRequest, MemoryFilters, MemoryRecord } from '$lib/types/memory';

export type MemoryLoadState = 'idle' | 'loading' | 'refreshing' | 'loaded' | 'error';
export type MemoryActionState = 'idle' | 'saving' | 'deleting' | 'pruning';

export interface MemoryState {
  memories: MemoryRecord[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
  filters: MemoryFilters;
  loadState: MemoryLoadState;
  actionState: MemoryActionState;
  error: string | null;
  lastLoadedAt: Date | null;
}

const INITIAL_FILTERS: MemoryFilters = { page: 1, page_size: 20 };

const INITIAL_STATE: MemoryState = {
  memories: [],
  total: 0,
  page: 1,
  pageSize: 20,
  pages: 0,
  filters: INITIAL_FILTERS,
  loadState: 'idle',
  actionState: 'idle',
  error: null,
  lastLoadedAt: null
};

const friendlyError = (error: unknown): string => {
  if (error instanceof MemoryServiceError) return error.message;
  return 'Something went wrong while opening memory.';
};

function createMemoryStore() {
  const store = writable<MemoryState>(INITIAL_STATE);
  let activeLoadId = 0;

  const load = async (filters: MemoryFilters = {}, options: { force?: boolean } = {}) => {
    const current = get(store);
    const nextFilters = { ...current.filters, ...filters };
    if (!options.force && current.loadState === 'loaded' && JSON.stringify(nextFilters) === JSON.stringify(current.filters)) return;
    const requestId = ++activeLoadId;
    store.update((state) => ({
      ...state,
      filters: nextFilters,
      loadState: state.memories.length ? 'refreshing' : 'loading',
      error: null
    }));

    try {
      const response = await memoryService.listMemories(nextFilters);
      if (requestId !== activeLoadId) return;
      store.update((state) => ({
        ...state,
        memories: response.memories,
        total: response.total,
        page: response.page,
        pageSize: response.page_size,
        pages: response.pages,
        filters: { ...nextFilters, page: response.page, page_size: response.page_size },
        loadState: 'loaded',
        error: null,
        lastLoadedAt: new Date()
      }));
    } catch (error) {
      if (requestId !== activeLoadId) return;
      store.update((state) => ({ ...state, loadState: 'error', error: friendlyError(error) }));
    }
  };

  const runAction = async (actionState: MemoryActionState, action: () => Promise<unknown>) => {
    store.update((state) => ({ ...state, actionState, error: null }));
    try {
      await action();
      await load(get(store).filters, { force: true });
    } catch (error) {
      store.update((state) => ({ ...state, error: friendlyError(error) }));
    } finally {
      store.update((state) => ({ ...state, actionState: 'idle' }));
    }
  };

  return {
    subscribe: store.subscribe,
    load,
    refresh() {
      return load(get(store).filters, { force: true });
    },
    setFilters(filters: MemoryFilters) {
      return load({ ...filters, page: 1 }, { force: true });
    },
    setPage(page: number) {
      return load({ page }, { force: true });
    },
    updateMemory(memoryId: string, text: string, metadata?: Record<string, unknown>) {
      return runAction('saving', () => memoryService.updateMemory(memoryId, { text, metadata }));
    },
    deleteMemory(memoryId: string) {
      return runAction('deleting', () => memoryService.deleteMemory(memoryId));
    },
    bulkDelete(request: MemoryBulkDeleteRequest) {
      return runAction('pruning', () => memoryService.bulkDeleteMemories(request));
    },
    clearError() {
      store.update((state) => ({ ...state, error: null, loadState: state.memories.length ? 'loaded' : 'idle' }));
    }
  };
}

export const memoryStore = createMemoryStore();
