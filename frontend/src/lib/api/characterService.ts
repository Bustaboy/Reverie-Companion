import type { CharacterBlueprint, CharacterCreateInput, CharacterListResponse, CharacterResponse, CharacterSummary } from '$lib/types/character';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 20_000;

export interface CharacterServiceOptions {
  baseUrl?: string;
  timeoutMs?: number;
  fetcher?: typeof fetch;
}

interface BackendErrorBody {
  detail?: { error?: string; code?: string } | string;
}

export class CharacterServiceError extends Error {
  readonly status?: number;

  constructor(message: string, options: { status?: number; cause?: unknown } = {}) {
    super(message, { cause: options.cause });
    this.name = 'CharacterServiceError';
    this.status = options.status;
  }
}

export class CharacterService {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly fetcher: typeof fetch;

  constructor(options: CharacterServiceOptions = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? getConfiguredBaseUrl());
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.fetcher = options.fetcher ?? fetch;
  }

  async listCharacters(): Promise<CharacterSummary[]> {
    const response = await this.request<CharacterListResponse>('/api/characters');
    return response.characters;
  }

  async getCharacter(characterId: string): Promise<CharacterBlueprint> {
    const response = await this.request<CharacterResponse>(`/api/characters/${encodeURIComponent(characterId)}`);
    return response.character;
  }

  async createBasicCharacter(input: CharacterCreateInput): Promise<CharacterBlueprint> {
    const response = await this.request<CharacterResponse>('/api/characters', {
      method: 'POST',
      body: JSON.stringify(input)
    });
    return response.character;
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const response = await this.fetcher(`${this.baseUrl}${path}`, {
        ...init,
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          ...init.headers
        },
        signal: controller.signal
      });
      const body = await parseJsonResponse<T | BackendErrorBody>(response);
      if (!response.ok) throw toServiceError(response, body as BackendErrorBody);
      return body as T;
    } catch (error) {
      if (error instanceof CharacterServiceError) throw error;
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new CharacterServiceError('The local character library took too long to respond.', { cause: error });
      }
      throw new CharacterServiceError('The local character library is not available yet.', { cause: error });
    } finally {
      globalThis.clearTimeout(timeout);
    }
  }
}

const parseJsonResponse = async <T>(response: Response): Promise<T> => {
  const text = await response.text();
  if (!text) return {} as T;
  try {
    return JSON.parse(text) as T;
  } catch (error) {
    throw new CharacterServiceError('The character library returned an unreadable response.', {
      status: response.status,
      cause: error
    });
  }
};

const toServiceError = (response: Response, body: BackendErrorBody): CharacterServiceError => {
  const detail = body.detail;
  const message =
    typeof detail === 'object' && typeof detail.error === 'string'
      ? detail.error
      : typeof detail === 'string'
        ? detail
        : response.status >= 500
          ? 'The local character library had trouble loading characters.'
          : 'The character request could not be completed.';
  return new CharacterServiceError(message, { status: response.status });
};

const getConfiguredBaseUrl = (): string =>
  import.meta.env.VITE_REVERIE_API_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

const normalizeBaseUrl = (baseUrl: string): string => baseUrl.replace(/\/+$/, '');

export const characterService = new CharacterService();
