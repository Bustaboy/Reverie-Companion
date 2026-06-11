import { dev } from '$app/environment';
import type { JournalEntriesResponse, JournalEntry } from '$lib/types/journal';

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

export interface JournalServiceOptions {
  baseUrl?: string;
  timeoutMs?: number;
  fetcher?: typeof fetch;
}

export class JournalServiceError extends Error {
  readonly status?: number;
  readonly details?: unknown;

  constructor(message: string, options: { status?: number; details?: unknown; cause?: unknown } = {}) {
    super(message, { cause: options.cause });
    this.name = 'JournalServiceError';
    this.status = options.status;
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

  async getRecentEntries(limit = 20): Promise<JournalEntry[]> {
    const safeLimit = Math.min(Math.max(Math.round(limit), 1), 50);
    const url = `${this.baseUrl}/journal/entries?limit=${safeLimit}`;
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);

    if (dev) console.debug('[Reverie API] GET', url);

    try {
      const response = await this.fetcher(url, {
        headers: { Accept: 'application/json' },
        signal: controller.signal
      });
      const body = await this.parseJsonResponse<JournalEntriesResponse | BackendErrorBody>(response);

      if (!response.ok) {
        throw this.toServiceError(response, body as BackendErrorBody);
      }

      const entries = Array.isArray((body as JournalEntriesResponse).entries)
        ? (body as JournalEntriesResponse).entries
        : [];
      if (dev) console.debug('[Reverie API] Journal entries', { count: entries.length });
      return entries;
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
      throw new JournalServiceError('The journal returned an unreadable response.', {
        status: response.status,
        cause: error
      });
    }
  }

  private toServiceError(response: Response, body: BackendErrorBody): JournalServiceError {
    const message = body.detail?.error ?? body.error ?? this.defaultMessageForStatus(response.status);
    return new JournalServiceError(message, {
      status: response.status,
      details: body.detail?.details ?? body.details
    });
  }

  private toUserFriendlyError(error: unknown): JournalServiceError {
    if (error instanceof JournalServiceError) return error;

    if (error instanceof DOMException && error.name === 'AbortError') {
      return new JournalServiceError('The journal took too long to answer. Please try refreshing in a moment.', {
        cause: error
      });
    }

    if (error instanceof TypeError) {
      return new JournalServiceError(
        'Could not reach the local journal service. Make sure the backend is running, then refresh the journal.',
        { cause: error }
      );
    }

    return new JournalServiceError('Something went wrong while opening the journal.', { cause: error });
  }

  private defaultMessageForStatus(status: number): string {
    if (status === 404) return 'The journal endpoint is not available in this backend build.';
    if (status >= 500) return 'Reverie had trouble opening the journal. Please try again.';
    return 'The journal request could not be completed.';
  }
}

const getConfiguredBaseUrl = (): string =>
  import.meta.env.VITE_REVERIE_API_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

const normalizeBaseUrl = (baseUrl: string): string => baseUrl.replace(/\/+$/, '');

export const journalService = new JournalService();
