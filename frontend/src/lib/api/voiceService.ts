import { dev } from '$app/environment';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';

export interface VoiceProfile {
  voice_id: string;
  name: string;
  type: 'character' | 'narrator';
  reference_audio_path?: string | null;
  metadata: Record<string, unknown>;
}

export interface CreateVoiceProfileInput {
  name: string;
  referenceAudio: Blob;
  filename?: string;
  characterId?: string;
  durationSeconds?: number;
}

export class VoiceServiceError extends Error {
  readonly status?: number;
  readonly code?: string;

  constructor(message: string, options: { status?: number; code?: string; cause?: unknown } = {}) {
    super(message, { cause: options.cause });
    this.name = 'VoiceServiceError';
    this.status = options.status;
    this.code = options.code;
  }
}

export class VoiceService {
  private readonly baseUrl: string;
  private readonly fetcher: typeof fetch;

  constructor(options: { baseUrl?: string; fetcher?: typeof fetch } = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? getConfiguredBaseUrl());
    this.fetcher = options.fetcher ?? fetch;
  }

  async listVoices(): Promise<VoiceProfile[]> {
    const response = await this.fetcher(`${this.baseUrl}/api/voices`, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw await this.toError(response, 'Could not load local voice profiles.');
    return (await response.json()) as VoiceProfile[];
  }

  async createVoiceProfile(input: CreateVoiceProfileInput): Promise<VoiceProfile> {
    const body = new FormData();
    body.set('name', input.name);
    body.set('reference_audio', input.referenceAudio, input.filename ?? 'voice-reference.webm');
    if (input.characterId?.trim()) body.set('character_id', input.characterId.trim());
    if (typeof input.durationSeconds === 'number' && Number.isFinite(input.durationSeconds)) {
      body.set('duration_seconds', input.durationSeconds.toFixed(2));
    }

    const response = await this.fetcher(`${this.baseUrl}/api/voices/clone`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
      body
    });
    if (!response.ok) throw await this.toError(response, 'Could not create that voice profile.');
    return (await response.json()) as VoiceProfile;
  }

  private async toError(response: Response, fallback: string): Promise<VoiceServiceError> {
    try {
      const body = (await response.json()) as { detail?: { error?: { code?: string; message?: string } } };
      return new VoiceServiceError(body.detail?.error?.message ?? fallback, {
        status: response.status,
        code: body.detail?.error?.code
      });
    } catch (error) {
      return new VoiceServiceError(fallback, { status: response.status, cause: error });
    }
  }
}

function getConfiguredBaseUrl(): string {
  const envBaseUrl = import.meta.env.VITE_REVERIE_API_BASE_URL;
  if (typeof envBaseUrl === 'string' && envBaseUrl.trim().length > 0) return envBaseUrl;
  if (dev) return DEFAULT_API_BASE_URL;
  return DEFAULT_API_BASE_URL;
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, '');
}

export const voiceService = new VoiceService();
