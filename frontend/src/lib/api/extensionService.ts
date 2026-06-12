import { dev } from '$app/environment';
import type {
  CharacterImportProfile,
  ExtensionCommandRequest,
  ExtensionCommandResult,
  ExtensionEvent,
  ExtensionRegistryResponse
} from '$lib/extensions/contracts';

const DEFAULT_API_BASE_URL = dev ? 'http://localhost:8000' : 'http://localhost:8000';
const API_BASE_URL = import.meta.env.VITE_REVERIE_API_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

export class ExtensionServiceError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly details?: unknown
  ) {
    super(message);
    this.name = 'ExtensionServiceError';
  }
}

const parseResponse = async <T>(response: Response): Promise<T> => {
  const contentType = response.headers.get('content-type') ?? '';
  const body = contentType.includes('application/json') ? await response.json() : await response.text();

  if (!response.ok) {
    const message =
      typeof body === 'object' && body && 'detail' in body
        ? JSON.stringify((body as { detail: unknown }).detail)
        : `Extension API request failed with status ${response.status}.`;
    throw new ExtensionServiceError(message, response.status, body);
  }

  return body as T;
};

export class ExtensionService {
  constructor(private readonly baseUrl = API_BASE_URL) {}

  async listExtensions(): Promise<ExtensionRegistryResponse> {
    const response = await fetch(`${this.baseUrl}/api/extensions`);
    return parseResponse<ExtensionRegistryResponse>(response);
  }

  async dispatchCommand(request: ExtensionCommandRequest): Promise<ExtensionCommandResult> {
    const response = await fetch(`${this.baseUrl}/api/extensions/commands/dispatch`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(request)
    });
    return parseResponse<ExtensionCommandResult>(response);
  }

  async listEvents(limit = 50): Promise<ExtensionEvent[]> {
    const response = await fetch(`${this.baseUrl}/api/extensions/events?limit=${encodeURIComponent(limit)}`);
    return parseResponse<ExtensionEvent[]>(response);
  }

  async previewCharacterImport(payload: Record<string, unknown>, source_format: 'sillytavern' | 'character_card' | 'auto' = 'auto'): Promise<CharacterImportProfile> {
    const response = await fetch(`${this.baseUrl}/api/extensions/character-import/preview`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ source_format, payload })
    });
    return parseResponse<CharacterImportProfile>(response);
  }
}

export const extensionService = new ExtensionService();
