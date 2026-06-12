import { dev } from '$app/environment';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 60_000;

export interface VoiceProfile {
  voice_id: string;
  name: string;
  type: 'character' | 'narrator';
  reference_audio_path?: string | null;
  metadata: Record<string, unknown>;
}

export interface VoiceCloneRequest {
  name: string;
  audio_base64: string;
  mime_type: string;
  character_id?: string;
  duration_seconds?: number;
}

export interface VoiceCloneResponse {
  profile: VoiceProfile;
  assigned_character_id?: string | null;
  cloning_backend: string;
  message: string;
}

export class VoiceServiceError extends Error {
  readonly status?: number;

  constructor(message: string, options: { status?: number; cause?: unknown } = {}) {
    super(message, { cause: options.cause });
    this.name = 'VoiceServiceError';
    this.status = options.status;
  }
}

export class VoiceService {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly fetcher: typeof fetch;

  constructor(options: { baseUrl?: string; timeoutMs?: number; fetcher?: typeof fetch } = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? getConfiguredBaseUrl());
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.fetcher = options.fetcher ?? fetch;
  }

  async createClone(request: VoiceCloneRequest, options: { signal?: AbortSignal } = {}): Promise<VoiceCloneResponse> {
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);
    const cancelExternalAbort = this.forwardAbort(options.signal, controller);

    try {
      const response = await this.fetcher(`${this.baseUrl}/api/voices/clone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify(request),
        signal: controller.signal
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = body?.detail?.error ?? body?.detail ?? body?.error;
        const message = typeof detail === 'string' ? detail : detail?.message ?? 'Reverie could not save that voice profile.';
        throw new VoiceServiceError(message, { status: response.status });
      }
      return body as VoiceCloneResponse;
    } catch (error) {
      if (error instanceof VoiceServiceError) throw error;
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new VoiceServiceError('Voice cloning was cancelled.', { cause: error });
      }
      throw new VoiceServiceError('Reverie could not reach the local voice manager.', { cause: error });
    } finally {
      globalThis.clearTimeout(timeout);
      cancelExternalAbort();
    }
  }

  private forwardAbort(signal: AbortSignal | undefined, controller: AbortController): () => void {
    if (!signal) return () => undefined;
    if (signal.aborted) {
      controller.abort();
      return () => undefined;
    }
    const abort = () => controller.abort();
    signal.addEventListener('abort', abort, { once: true });
    return () => signal.removeEventListener('abort', abort);
  }
}

function getConfiguredBaseUrl(): string {
  const envBaseUrl = import.meta.env.VITE_REVERIE_API_BASE_URL;
  return typeof envBaseUrl === 'string' && envBaseUrl.trim().length > 0 ? envBaseUrl : DEFAULT_API_BASE_URL;
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, '');
}

export const voiceService = new VoiceService();
