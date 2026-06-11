import { dev } from '$app/environment';
import type {
  LoRATrainingExample,
  LoRATrainingJob,
  PersonalLoRASettingsUpdate,
  PersonalLoRAStatusResponse
} from '$lib/types/growth';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 20_000;

interface BackendErrorBody {
  detail?: string | {
    error?: string;
    details?: unknown;
    request_id?: string;
  };
  error?: string;
  details?: unknown;
}

export interface GrowthServiceOptions {
  baseUrl?: string;
  timeoutMs?: number;
  fetcher?: typeof fetch;
}

export class GrowthServiceError extends Error {
  readonly status?: number;
  readonly details?: unknown;

  constructor(message: string, options: { status?: number; details?: unknown; cause?: unknown } = {}) {
    super(message, { cause: options.cause });
    this.name = 'GrowthServiceError';
    this.status = options.status;
    this.details = options.details;
  }
}

export class GrowthService {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly fetcher: typeof fetch;

  constructor(options: GrowthServiceOptions = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? getConfiguredBaseUrl());
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.fetcher = options.fetcher ?? fetch;
  }

  getPersonalLoRAStatus(): Promise<PersonalLoRAStatusResponse> {
    return this.request<PersonalLoRAStatusResponse>('/growth/personal-lora');
  }

  updatePersonalLoRASettings(update: PersonalLoRASettingsUpdate): Promise<PersonalLoRAStatusResponse> {
    return this.request<{ settings: PersonalLoRAStatusResponse['settings'] }>('/growth/personal-lora/settings', {
      method: 'PATCH',
      body: JSON.stringify(update)
    }).then(async () => this.getPersonalLoRAStatus());
  }

  approveExample(itemId: string): Promise<LoRATrainingExample> {
    return this.request<{ example: LoRATrainingExample }>(`/growth/personal-lora/examples/${encodeURIComponent(itemId)}/approve`, {
      method: 'POST'
    }).then((response) => response.example);
  }

  rejectExample(itemId: string): Promise<LoRATrainingExample> {
    return this.request<{ example: LoRATrainingExample }>(`/growth/personal-lora/examples/${encodeURIComponent(itemId)}/reject`, {
      method: 'POST'
    }).then((response) => response.example);
  }

  deleteExample(itemId: string): Promise<LoRATrainingExample> {
    return this.request<{ example: LoRATrainingExample }>(`/growth/personal-lora/examples/${encodeURIComponent(itemId)}`, {
      method: 'DELETE'
    }).then((response) => response.example);
  }

  startTraining(): Promise<LoRATrainingJob> {
    return this.request<{ job: LoRATrainingJob }>('/growth/personal-lora/start', { method: 'POST' }).then(
      (response) => response.job
    );
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);

    if (dev) console.debug('[Reverie API]', init.method ?? 'GET', url);

    try {
      const response = await this.fetcher(url, {
        ...init,
        headers: {
          Accept: 'application/json',
          ...(init.body ? { 'Content-Type': 'application/json' } : {}),
          ...init.headers
        },
        signal: controller.signal
      });
      const body = await this.parseJsonResponse<T | BackendErrorBody>(response);

      if (!response.ok) {
        throw this.toServiceError(response, body as BackendErrorBody);
      }

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
      throw new GrowthServiceError('The growth service returned an unreadable response.', {
        status: response.status,
        cause: error
      });
    }
  }

  private toServiceError(response: Response, body: BackendErrorBody): GrowthServiceError {
    const detail = body.detail;
    const message =
      (typeof detail === 'string' ? detail : detail?.error) ?? body.error ?? this.defaultMessageForStatus(response.status);
    return new GrowthServiceError(message, {
      status: response.status,
      details: typeof detail === 'object' ? detail.details : body.details
    });
  }

  private toUserFriendlyError(error: unknown): GrowthServiceError {
    if (error instanceof GrowthServiceError) return error;

    if (error instanceof DOMException && error.name === 'AbortError') {
      return new GrowthServiceError('The growth controls took too long to answer. Please try again in a moment.', {
        cause: error
      });
    }

    if (error instanceof TypeError) {
      return new GrowthServiceError(
        'Could not reach the local growth service. Make sure the backend is running, then refresh Training.',
        { cause: error }
      );
    }

    return new GrowthServiceError('Something went wrong while opening the growth controls.', { cause: error });
  }

  private defaultMessageForStatus(status: number): string {
    if (status === 404) return 'The personal LoRA controls are not available in this backend build.';
    if (status === 409) return 'Training could not start yet. Please review the approved examples and opt-in status.';
    if (status >= 500) return 'Reverie had trouble opening the growth controls. Please try again.';
    return 'The growth request could not be completed.';
  }
}

const getConfiguredBaseUrl = (): string =>
  import.meta.env.VITE_REVERIE_API_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

const normalizeBaseUrl = (baseUrl: string): string => baseUrl.replace(/\/+$/, '');

export const growthService = new GrowthService();
