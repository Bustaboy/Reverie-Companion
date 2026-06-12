import { dev } from '$app/environment';
import type {
  MemoryBulkDeleteInput,
  MemoryBulkDeleteResponse,
  MemoryDetailResponse,
  MemoryListResponse,
  MemoryQuery,
  MemoryRecord,
  MemoryUpdateInput
} from '$lib/types/memory';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 20_000;

interface BackendErrorBody {
  detail?: {
    error?: string;
    details?: unknown;
    request_id?: string;
  };
  error?: string;
  details?: unknown;
}

export interface MemoryServiceOptions {
  baseUrl?: string;
  timeoutMs?: number;
  fetcher?: typeof fetch;
}

export class MemoryServiceError extends Error {
  readonly status?: number;
  readonly details?: unknown;

  constructor(message: string, options: { status?: number; details?: unknown; cause?: unknown } = {}) {
    super(message, { cause: options.cause });
    this.name = 'MemoryServiceError';
    this.status = options.status;
    this.details = options.details;
  }
}

export class MemoryService {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly fetcher: typeof fetch;

  constructor(options: MemoryServiceOptions = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? getConfiguredBaseUrl());
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.fetcher = options.fetcher ?? fetch;
  }

  async listMemories(query: MemoryQuery = {}): Promise<MemoryListResponse> {
    const params = new URLSearchParams();
    if (query.q) params.set('q', query.q);
    if (query.character) params.set('character', query.character);
    if (query.theme) params.set('theme', query.theme);
    if (query.source) params.set('source', query.source);
    if (query.dateFrom) params.set('date_from', query.dateFrom);
    if (query.dateTo) params.set('date_to', query.dateTo);
    params.set('page', String(Math.max(1, query.page ?? 1)));
    params.set('page_size', String(Math.min(Math.max(query.pageSize ?? 20, 5), 50)));
    return this.request<MemoryListResponse>(`/memory/memories?${params.toString()}`, { method: 'GET' });
  }

  async getMemory(memoryId: string): Promise<MemoryRecord> {
    const body = await this.request<MemoryDetailResponse>(`/memory/memories/${encodeURIComponent(memoryId)}`, { method: 'GET' });
    return body.memory;
  }

  async updateMemory(memoryId: string, input: MemoryUpdateInput): Promise<MemoryRecord> {
    const body = await this.request<MemoryDetailResponse>(`/memory/memories/${encodeURIComponent(memoryId)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input)
    });
    return body.memory;
  }

  async deleteMemory(memoryId: string): Promise<void> {
    await this.request<void>(`/memory/memories/${encodeURIComponent(memoryId)}`, { method: 'DELETE' });
  }

  async bulkDelete(input: MemoryBulkDeleteInput): Promise<MemoryBulkDeleteResponse> {
    return this.request<MemoryBulkDeleteResponse>('/memory/memories/bulk-delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input)
    });
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);
    if (dev) console.debug('[Reverie API]', init.method ?? 'GET', url);

    try {
      const response = await this.fetcher(url, {
        ...init,
        headers: { Accept: 'application/json', ...(init.headers ?? {}) },
        signal: controller.signal
      });
      if (response.status === 204) return undefined as T;
      const body = await this.parseJsonResponse<T | BackendErrorBody>(response);
      if (!response.ok) throw this.toServiceError(response, body as BackendErrorBody);
      return body as T;
    } catch (error) {
      throw this.toUserFriendlyError(error);
    } finally {
      globalThis.clearTimeout(timeout);
    }
  }

  private async parseJsonResponse<T>(response: Response): Promise<T> {
    const text = await response.text();
    if (!text) return {} as T;
    try {
      return JSON.parse(text) as T;
    } catch (error) {
      throw new MemoryServiceError('Reverie returned an unreadable memory response.', {
        status: response.status,
        cause: error
      });
    }
  }

  private toServiceError(response: Response, body: BackendErrorBody): MemoryServiceError {
    const detail = body.detail;
    const message = detail?.error ?? body.error ?? 'Reverie could not update memory right now.';
    return new MemoryServiceError(message, { status: response.status, details: detail?.details ?? body.details });
  }

  private toUserFriendlyError(error: unknown): MemoryServiceError {
    if (error instanceof MemoryServiceError) return error;
    if (error instanceof DOMException && error.name === 'AbortError') {
      return new MemoryServiceError('Memory took too long to answer. The local backend may be busy.', { cause: error });
    }
    if (error instanceof TypeError) {
      return new MemoryServiceError('Cannot reach the local Reverie backend for memory controls.', { cause: error });
    }
    return new MemoryServiceError('Something went wrong while opening memory.', { cause: error });
  }
}

const normalizeBaseUrl = (url: string) => url.replace(/\/$/, '');

const getConfiguredBaseUrl = () => {
  if (typeof window === 'undefined') return DEFAULT_API_BASE_URL;
  return window.localStorage.getItem('reverie.apiBaseUrl') ?? DEFAULT_API_BASE_URL;
};

export const memoryService = new MemoryService();
