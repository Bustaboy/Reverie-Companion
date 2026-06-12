import { dev } from '$app/environment';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 90_000;

export type TtsAudioFormat = 'wav' | 'pcm' | 'mp3';
export type TtsQualityPreference = 'quality' | 'speed';

export interface TtsContext {
  character_id?: string | null;
  mode?: 'one_to_one' | 'rpg' | string;
  is_narration?: boolean;
  scene_id?: string | null;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface TtsGenerateRequest {
  text: string;
  voice_id?: string;
  character_id?: string;
  context?: TtsContext;
  tts_text?: string;
  stream?: boolean;
  audio_format?: TtsAudioFormat;
}

export interface TtsGenerateResponse {
  request_id: string;
  backend: string;
  voice_id: string;
  audio_format: TtsAudioFormat;
  audio_base64: string;
  sample_rate?: number;
  duration_seconds?: number;
  fallback_used?: boolean;
}

export interface TtsServiceOptions {
  baseUrl?: string;
  timeoutMs?: number;
  fetcher?: typeof fetch;
}

interface BackendErrorBody {
  detail?: {
    error?: {
      code?: string;
      message?: string;
      details?: unknown;
      retryable?: boolean;
    };
  };
}

export class TtsServiceError extends Error {
  readonly code?: string;
  readonly status?: number;
  readonly retryable?: boolean;
  readonly details?: unknown;

  constructor(message: string, options: { code?: string; status?: number; retryable?: boolean; details?: unknown; cause?: unknown } = {}) {
    super(message, { cause: options.cause });
    this.name = 'TtsServiceError';
    this.code = options.code;
    this.status = options.status;
    this.retryable = options.retryable;
    this.details = options.details;
  }
}

export class TtsService {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly fetcher: typeof fetch;

  constructor(options: TtsServiceOptions = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? getConfiguredBaseUrl());
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.fetcher = options.fetcher ?? fetch;
  }

  async generateSpeech(request: TtsGenerateRequest, signal?: AbortSignal): Promise<TtsGenerateResponse> {
    const url = `${this.baseUrl}/api/tts/generate`;
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);
    const cancelForward = this.forwardAbort(signal, controller);

    this.logRequest(url, request);

    try {
      const response = await this.fetcher(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json'
        },
        body: JSON.stringify({ ...request, stream: false, audio_format: request.audio_format ?? 'wav' }),
        signal: controller.signal
      });
      const responseBody = await this.parseJsonResponse<TtsGenerateResponse | BackendErrorBody>(response);

      if (!response.ok) {
        throw this.toServiceError(response, responseBody as BackendErrorBody);
      }

      const result = responseBody as TtsGenerateResponse;
      this.logResponse(url, result);
      return result;
    } catch (error) {
      throw this.toUserFriendlyError(error);
    } finally {
      globalThis.clearTimeout(timeout);
      cancelForward();
    }
  }

  private async parseJsonResponse<T>(response: Response): Promise<T> {
    const text = await response.text();
    if (!text) return {} as T;

    try {
      return JSON.parse(text) as T;
    } catch (error) {
      throw new TtsServiceError('The local voice service returned an unreadable response.', {
        status: response.status,
        cause: error
      });
    }
  }

  private toServiceError(response: Response, body: BackendErrorBody): TtsServiceError {
    const backendError = body.detail?.error;
    return new TtsServiceError(backendError?.message ?? this.defaultMessageForStatus(response.status), {
      status: response.status,
      code: backendError?.code,
      retryable: backendError?.retryable,
      details: backendError?.details
    });
  }

  private toUserFriendlyError(error: unknown): TtsServiceError {
    if (error instanceof TtsServiceError) return error;

    if (error instanceof DOMException && error.name === 'AbortError') {
      return new TtsServiceError('Voice playback was cancelled before synthesis finished.', { cause: error });
    }

    if (error instanceof TypeError) {
      return new TtsServiceError('Could not reach the local voice service. TTS is paused until the backend is available.', {
        cause: error
      });
    }

    return new TtsServiceError('The local voice service could not synthesize this line.', { cause: error });
  }

  private defaultMessageForStatus(status: number): string {
    if (status === 503) return 'Text-to-speech is disabled or unavailable in the local backend.';
    if (status === 422) return 'This line could not be prepared for voice playback.';
    if (status >= 500) return 'The local voice service had trouble generating audio.';
    return 'The local voice service could not process this line.';
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

  private logRequest(url: string, request: TtsGenerateRequest): void {
    if (!dev) return;
    console.debug('[Reverie TTS] POST', url, {
      textChars: request.text.length,
      voiceId: request.voice_id,
      hasTtsText: Boolean(request.tts_text)
    });
  }

  private logResponse(url: string, response: TtsGenerateResponse): void {
    if (!dev) return;
    console.debug('[Reverie TTS] Response', url, {
      requestId: response.request_id,
      backend: response.backend,
      voiceId: response.voice_id,
      durationSeconds: response.duration_seconds,
      fallbackUsed: response.fallback_used
    });
  }
}

const getConfiguredBaseUrl = (): string =>
  import.meta.env.VITE_REVERIE_API_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

const normalizeBaseUrl = (baseUrl: string): string => baseUrl.replace(/\/+$/, '');

export const ttsService = new TtsService();
