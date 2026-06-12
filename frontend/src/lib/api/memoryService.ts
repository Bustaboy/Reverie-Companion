import { dev } from '$app/environment';
import type {
  MemoryBulkDeleteRequest,
  MemoryBulkDeleteResponse,
  MemoryFilters,
  MemoryListResponse,
  MemoryRecord,
  MemoryUpdateRequest,
  MemoryUpdateResponse
} from '$lib/types/memory';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 20_000;

interface BackendErrorBody {
  detail?: string | { error?: string; details?: unknown; request_id?: string };
  error?: string;
  details?: unknown;
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

export interface MemoryServiceOptions {
  baseUrl?: string;
  timeoutMs?: number;
  fetcher?: typeof fetch;
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

  async listMemories(filters: MemoryFilters = {}): Promise<MemoryListResponse> {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== null && String(value).trim() !== '') params.set(key, String(value));
    }
    const url = `${this.baseUrl}/memory${params.size ? `?${params.toString()}` : ''}`;
    return this.request<MemoryListResponse>(url, { method: 'GET' }, 'Memory browser could not load memories.');
  }

  async updateMemory(memoryId: string, update: MemoryUpdateRequest): Promise<MemoryRecord> {
    const body = await this.request<MemoryUpdateResponse>(
      `${this.baseUrl}/memory/${encodeURIComponent(memoryId)}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(update)
      },
      'Memory browser could not save that memory.'
    );
    return body.memory;
  }

  async deleteMemory(memoryId: string): Promise<void> {
    await this.request(`${this.baseUrl}/memory/${encodeURIComponent(memoryId)}`, { method: 'DELETE' }, 'Memory browser could not delete that memory.');
  }

  async bulkDeleteMemories(request: MemoryBulkDeleteRequest): Promise<MemoryBulkDeleteResponse> {
    return this.request<MemoryBulkDeleteResponse>(
      `${this.baseUrl}/memory/bulk-delete`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      },
      'Memory browser could not prune those memories.'
    );
  }

  private async request<T>(url: string, init: RequestInit, fallbackMessage: string): Promise<T> {
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);
    if (dev) console.debug('[Reverie API]', init.method ?? 'GET', url);

    try {
      const response = await this.fetcher(url, {
        ...init,
        headers: { Accept: 'application/json', ...(init.headers ?? {}) },
        signal: controller.signal
      });
      const body = await this.parseJsonResponse<T | BackendErrorBody>(response);
      if (!response.ok) throw this.toServiceError(response, body as BackendErrorBody, fallbackMessage);
      return body as T;
    } catch (error) {
      throw this.toUserFriendlyError(error, fallbackMessage);
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
      throw new MemoryServiceError('The memory service returned an unreadable response.', { status: response.status, cause: error });
    }
  }

  private toServiceError(response: Response, body: BackendErrorBody, fallbackMessage: string): MemoryServiceError {
    const detail = body.detail;
    const message = (typeof detail === 'string' ? detail : detail?.error) ?? body.error ?? fallbackMessage;
    return new MemoryServiceError(message, {
      status: response.status,
      details: typeof detail === 'string' ? body.details : (detail?.details ?? body.details)
    });
  }

  private toUserFriendlyError(error: unknown, fallbackMessage: string): MemoryServiceError {
    if (error instanceof MemoryServiceError) return error;
    if (error instanceof DOMException && error.name === 'AbortError') {
      return new MemoryServiceError('The memory browser took too long to answer. Try again in a moment.', { cause: error });
    }
    if (error instanceof TypeError) {
      return new MemoryServiceError('Could not reach the local memory service. Make sure the backend is running, then refresh Memory.', { cause: error });
    }
    return new MemoryServiceError(fallbackMessage, { cause: error });
  }
}

const getConfiguredBaseUrl = (): string =>
  import.meta.env.VITE_REVERIE_API_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

const normalizeBaseUrl = (baseUrl: string): string => baseUrl.replace(/\/+$/, '');

export const memoryService = new MemoryService();
