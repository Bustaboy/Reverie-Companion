import { dev } from '$app/environment';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';

export interface CharacterIdentity {
  display_name: string;
  pronouns: string;
  adult_age_range?: string;
  species_or_type?: string;
  creator_notes?: string | null;
  tags?: string[];
}

export interface CharacterRelationshipState {
  relationship_dynamic?: string;
  current_relationship_phase?: string;
  starting_relationship_phase?: string;
  phase?: string;
  default_intimacy_level?: string;
}

export interface CharacterVisualIdentity {
  schema_version?: string;
  identity_anchors?: string[];
  evolving_traits?: Array<{ name: string; value: string; provenance?: string; updated_at?: string }>;
  scene_mutable_traits?: string[];
  rejected_traits?: string[];
  current_appearance?: string | null;
  adult_only_policy?: Record<string, unknown>;
  updated_at?: string;
}

export interface CharacterPersonalityProfile {
  core_traits?: string[];
}

export interface CharacterBlueprint {
  schema_version: number;
  character_id: string;
  identity: CharacterIdentity;
  relationship?: CharacterRelationshipState;
  personality?: CharacterPersonalityProfile;
  visual_identity?: CharacterVisualIdentity;
  updated_at?: string;
}

export interface CharacterSummary {
  character_id: string;
  display_name: string;
  pronouns: string;
  adult_age_range?: string;
  species_or_type?: string;
  relationship_dynamic?: string;
  core_traits?: string[];
  updated_at?: string;
}

export interface CharacterCreateInput {
  display_name: string;
  character_id?: string;
  pronouns?: string;
  species_or_type?: string;
  relationship_dynamic?: string;
  core_traits?: string[];
}

interface CharacterListResponse {
  characters: CharacterSummary[];
}

interface CharacterResponse {
  character: CharacterBlueprint;
}

interface BackendErrorBody {
  detail?: { error?: string; code?: string };
  error?: string;
}

export class CharacterServiceError extends Error {
  readonly status?: number;
  readonly details?: unknown;

  constructor(message: string, options: { status?: number; details?: unknown; cause?: unknown } = {}) {
    super(message, { cause: options.cause });
    this.name = 'CharacterServiceError';
    this.status = options.status;
    this.details = options.details;
  }
}

export interface CharacterServiceOptions {
  baseUrl?: string;
  fetcher?: typeof fetch;
}

export class CharacterService {
  private readonly baseUrl: string;
  private readonly fetcher: typeof fetch;

  constructor(options: CharacterServiceOptions = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? getConfiguredBaseUrl());
    this.fetcher = options.fetcher ?? fetch;
  }

  async listCharacters(): Promise<CharacterSummary[]> {
    const body = await this.request<CharacterListResponse>('/api/characters');
    return Array.isArray(body.characters) ? body.characters : [];
  }

  async getCharacter(characterId: string): Promise<CharacterBlueprint> {
    const body = await this.request<CharacterResponse>(`/api/characters/${encodeURIComponent(characterId)}`);
    return body.character;
  }

  async createBasicCharacter(input: CharacterCreateInput): Promise<CharacterBlueprint> {
    const body = await this.request<CharacterResponse>('/api/characters', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(input)
    });
    return body.character;
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`;

    try {
      const response = await this.fetcher(url, {
        headers: { Accept: 'application/json', ...init.headers },
        ...init
      });
      const body = (await response.json().catch(() => ({}))) as T | BackendErrorBody;

      if (!response.ok) {
        throw new CharacterServiceError(toErrorMessage(body as BackendErrorBody), { status: response.status, details: body });
      }

      if (dev) console.debug('[Reverie API] Character response', url, body);
      return body as T;
    } catch (error) {
      if (error instanceof CharacterServiceError) throw error;
      throw new CharacterServiceError('Reverie could not reach the local character library.', { cause: error });
    }
  }
}

const toErrorMessage = (body: BackendErrorBody): string =>
  body.detail?.error ?? body.error ?? 'The local character library could not process that request.';

const getConfiguredBaseUrl = (): string =>
  import.meta.env.VITE_REVERIE_API_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

const normalizeBaseUrl = (baseUrl: string): string => baseUrl.replace(/\/+$/, '');

export const characterService = new CharacterService();
