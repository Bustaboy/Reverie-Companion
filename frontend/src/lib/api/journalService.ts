import { dev } from '$app/environment';
import type { JournalEntry } from '$lib/types/journal';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 20_000;
const DEFAULT_JOURNAL_LIMIT = 25;

export interface JournalServiceOptions {
  baseUrl?: string;
  timeoutMs?: number;
  fetcher?: typeof fetch;
}

export interface GetJournalEntriesOptions {
  limit?: number;
  signal?: AbortSignal;
}

interface BackendErrorBody {
  detail?: {
    error?: string;
    request_id?: string;
    details?: unknown;
  };
}

interface BackendJournalResponse {
  entries?: unknown;
}

export class JournalServiceError extends Error {
  readonly status?: number;
  readonly requestId?: string;
  readonly details?: unknown;

  constructor(message: string, options: { status?: number; requestId?: string; details?: unknown; cause?: unknown } = {}) {
    super(message, { cause: options.cause });
    this.name = 'JournalServiceError';
    this.status = options.status;
    this.requestId = options.requestId;
    this.details = options.details;
  }
}

export class JournalService {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly fetcher: typeof fetch;

  constructor(options: JournalServiceOptions = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? getConfiguredBaseUrl());
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.fetcher = options.fetcher ?? fetch;
  }

  async getRecentEntries(options: GetJournalEntriesOptions = {}): Promise<JournalEntry[]> {
    const limit = clampLimit(options.limit ?? DEFAULT_JOURNAL_LIMIT);
    const url = `${this.baseUrl}/journal?limit=${limit}`;
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);
    const cancelExternalAbort = this.forwardAbort(options.signal, controller);

    if (dev) {
      console.debug('[Reverie API] GET', url);
    }

    try {
      const response = await this.fetcher(url, {
        method: 'GET',
        headers: { Accept: 'application/json' },
        signal: controller.signal
      });
      const body = await this.parseJsonResponse<BackendJournalResponse | BackendErrorBody>(response);

      if (!response.ok) {
        throw this.toServiceError(response, body as BackendErrorBody);
      }

      const entries = this.normalizeEntries((body as BackendJournalResponse).entries);
      if (dev) {
        console.debug('[Reverie API] Journal entries', { count: entries.length });
      }
      return entries;
    } catch (error) {
      throw this.toUserFriendlyError(error);
    } finally {
      globalThis.clearTimeout(timeout);
      cancelExternalAbort();
    }
  }

  private normalizeEntries(value: unknown): JournalEntry[] {
    if (!Array.isArray(value)) {
      return [];
    }

    return value.filter((entry): entry is JournalEntry => this.isRecord(entry) && typeof entry.entry_id === 'string');
  }

  private async parseJsonResponse<T>(response: Response): Promise<T> {
    const text = await response.text();
    if (!text) return {} as T;

    try {
      return JSON.parse(text) as T;
    } catch (error) {
      throw new JournalServiceError('The journal returned an unreadable response.', {
        status: response.status,
        cause: error
      });
    }
  }

  private forwardAbort(source: AbortSignal | undefined, target: AbortController): () => void {
    if (!source) return () => undefined;

    if (source.aborted) {
      target.abort(source.reason);
      return () => undefined;
    }

    const abortTarget = () => target.abort(source.reason);
    source.addEventListener('abort', abortTarget, { once: true });
    return () => source.removeEventListener('abort', abortTarget);
  }

  private toServiceError(response: Response, body: BackendErrorBody): JournalServiceError {
    const detail = body.detail;
    return new JournalServiceError(detail?.error ?? this.defaultMessageForStatus(response.status), {
      status: response.status,
      requestId: detail?.request_id,
      details: detail?.details
    });
  }

  private toUserFriendlyError(error: unknown): JournalServiceError {
    if (error instanceof JournalServiceError) return error;

    if (error instanceof DOMException && error.name === 'AbortError') {
      return new JournalServiceError('The journal took too long to open. Make sure the local backend is running.');
    }

    if (error instanceof TypeError) {
      return new JournalServiceError('Could not reach the local journal service. Start the backend, then refresh the journal.');
    }

    return new JournalServiceError('Something went wrong while opening the reflection journal.', { cause: error });
  }

  private defaultMessageForStatus(status: number): string {
    if (status === 422) return 'The journal request was not valid.';
    if (status >= 500) return 'The local journal service had trouble reading entries.';
    return 'The journal service could not process the request.';
  }

  private isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
  }
}

const getConfiguredBaseUrl = (): string =>
  import.meta.env.VITE_REVERIE_API_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

const normalizeBaseUrl = (baseUrl: string): string => baseUrl.replace(/\/+$/, '');
const clampLimit = (limit: number): number => Math.min(Math.max(Math.trunc(limit), 1), 50);

export const journalService = new JournalService();
