import { get, writable } from 'svelte/store';
import { MemoryServiceError, memoryService } from '$lib/api/memoryService';
import type { MemoryBulkDeleteInput, MemoryQuery, MemoryRecord, MemoryUpdateInput } from '$lib/types/memory';

interface MemoryState {
  items: MemoryRecord[];
  selectedMemoryId: string | null;
  total: number;
  page: number;
  pageSize: number;
  query: Required<Pick<MemoryQuery, 'q' | 'character' | 'theme' | 'source'>> & Pick<MemoryQuery, 'dateFrom' | 'dateTo'>;
  loadState: 'idle' | 'loading' | 'refreshing' | 'loaded' | 'error';
  actionState: 'idle' | 'saving' | 'deleting' | 'pruning';
  error: string | null;
  lastLoadedAt: Date | null;
}

const INITIAL_STATE: MemoryState = {
  items: [],
  selectedMemoryId: null,
  total: 0,
  page: 1,
  pageSize: 20,
  query: { q: '', character: '', theme: '', source: '', dateFrom: undefined, dateTo: undefined },
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
  let activeRequest: AbortController | null = null;

  const loadMemories = async (options: { force?: boolean; page?: number } = {}) => {
    const current = get(store);
    if (activeRequest || (!options.force && current.loadState === 'loaded' && options.page === undefined)) return;

    const controller = new AbortController();
    activeRequest = controller;
    const requestedPage = options.page ?? current.page;

    store.update((state) => ({
      ...state,
      page: requestedPage,
      loadState: state.items.length > 0 ? 'refreshing' : 'loading',
      error: null
    }));

    try {
      const latest = get(store);
      const response = await memoryService.listMemories({
        ...latest.query,
        page: requestedPage,
        pageSize: latest.pageSize
      });
      if (controller.signal.aborted) return;
      store.update((state) => {
        const selectedStillExists = response.items.some((item) => item.id === state.selectedMemoryId);
        return {
          ...state,
          items: response.items,
          total: response.total,
          page: response.page,
          pageSize: response.page_size,
          selectedMemoryId: selectedStillExists ? state.selectedMemoryId : response.items[0]?.id ?? null,
          loadState: 'loaded',
          error: null,
          lastLoadedAt: new Date()
        };
      });
    } catch (error) {
      if (controller.signal.aborted) return;
      store.update((state) => ({ ...state, loadState: 'error', error: friendlyError(error) }));
    } finally {
      if (activeRequest === controller) activeRequest = null;
    }
  };

  return {
    subscribe: store.subscribe,
    loadMemories,
    refresh() {
      return loadMemories({ force: true });
    },
    selectMemory(memoryId: string) {
      store.update((state) => ({ ...state, selectedMemoryId: memoryId }));
    },
    setQuery(query: Partial<MemoryState['query']>) {
      store.update((state) => ({ ...state, query: { ...state.query, ...query }, page: 1 }));
      return loadMemories({ force: true, page: 1 });
    },
    setPage(page: number) {
      return loadMemories({ force: true, page });
    },
    async updateMemory(memoryId: string, input: MemoryUpdateInput) {
      store.update((state) => ({ ...state, actionState: 'saving', error: null }));
      try {
        const memory = await memoryService.updateMemory(memoryId, input);
        store.update((state) => ({
          ...state,
          items: state.items.map((item) => (item.id === memory.id ? memory : item)),
          selectedMemoryId: memory.id,
          actionState: 'idle',
          error: null
        }));
      } catch (error) {
        store.update((state) => ({ ...state, actionState: 'idle', error: friendlyError(error) }));
      }
    },
    async deleteMemory(memoryId: string) {
      store.update((state) => ({ ...state, actionState: 'deleting', error: null }));
      try {
        await memoryService.deleteMemory(memoryId);
        store.update((state) => {
          const items = state.items.filter((item) => item.id !== memoryId);
          return {
            ...state,
            items,
            total: Math.max(0, state.total - 1),
            selectedMemoryId: items[0]?.id ?? null,
            actionState: 'idle',
            error: null
          };
        });
      } catch (error) {
        store.update((state) => ({ ...state, actionState: 'idle', error: friendlyError(error) }));
      }
    },
    async bulkDelete(input: MemoryBulkDeleteInput) {
      store.update((state) => ({ ...state, actionState: 'pruning', error: null }));
      try {
        await memoryService.bulkDelete(input);
        store.update((state) => ({ ...state, actionState: 'idle', error: null }));
        await loadMemories({ force: true });
      } catch (error) {
        store.update((state) => ({ ...state, actionState: 'idle', error: friendlyError(error) }));
      }
    },
    clearError() {
      store.update((state) => ({ ...state, error: null, loadState: state.items.length ? 'loaded' : 'idle' }));
    }
  };
}

export const memoryStore = createMemoryStore();
