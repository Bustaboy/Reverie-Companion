import { dev } from '$app/environment';
import type { TTSEmotionMetadata, TTSMode } from '$lib/types/chat';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 90_000;

export type TTSAudioFormat = 'wav' | 'pcm' | 'mp3';

export interface TTSContextPayload {
  character_id?: string;
  is_narration?: boolean;
  mode?: TTSMode;
  emotion_hint?: string;
  intensity?: number;
}

export interface TTSGenerateRequest {
  text: string;
  voice_id?: string;
  character_id?: string;
  context?: TTSContextPayload;
  tts_text?: string;
  emotion?: TTSEmotionMetadata;
  stream?: boolean;
  audio_format?: TTSAudioFormat;
}

export interface TTSStreamResult {
  objectUrl: string;
  audio_format: TTSAudioFormat;
  request_id?: string;
  streamed: boolean;
}

export interface TTSGenerateResponse {
  request_id: string;
  backend: 'orpheus' | 'piper';
  voice_id: string;
  audio_format: TTSAudioFormat;
  audio_base64: string;
  sample_rate: number;
  duration_seconds?: number | null;
  fallback_used?: boolean;
}

export interface TTSServiceOptions {
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

export class TTSServiceError extends Error {
  readonly status?: number;
  readonly code?: string;
  readonly retryable?: boolean;
  readonly details?: unknown;

  constructor(message: string, options: { status?: number; code?: string; retryable?: boolean; details?: unknown; cause?: unknown } = {}) {
    super(message, { cause: options.cause });
    this.name = 'TTSServiceError';
    this.status = options.status;
    this.code = options.code;
    this.retryable = options.retryable;
    this.details = options.details;
  }
}

export class TTSService {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly fetcher: typeof fetch;

  constructor(options: TTSServiceOptions = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? getConfiguredBaseUrl());
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.fetcher = options.fetcher ?? fetch;
  }

  async generateSpeech(request: TTSGenerateRequest, options: { signal?: AbortSignal } = {}): Promise<TTSGenerateResponse> {
    const url = `${this.baseUrl}/api/tts/generate`;
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);
    const cancelExternalAbort = this.forwardAbort(options.signal, controller);

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

      const body = await this.parseJsonResponse<TTSGenerateResponse | BackendErrorBody>(response);

      if (!response.ok) {
        throw this.toServiceError(response, body as BackendErrorBody);
      }

      return body as TTSGenerateResponse;
    } catch (error) {
      throw this.toUserFriendlyError(error);
    } finally {
      globalThis.clearTimeout(timeout);
      cancelExternalAbort();
    }
  }


  async streamSpeech(request: TTSGenerateRequest, options: { signal?: AbortSignal } = {}): Promise<TTSStreamResult> {
    const url = `${this.baseUrl}/api/tts/generate`;
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);
    const cancelExternalAbort = this.forwardAbort(options.signal, controller);

    try {
      const response = await this.fetcher(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'audio/wav, application/json'
        },
        body: JSON.stringify({ ...request, stream: true, audio_format: request.audio_format ?? 'wav' }),
        signal: controller.signal
      });

      if (!response.ok) {
        const body = await this.parseJsonResponse<BackendErrorBody>(response);
        throw this.toServiceError(response, body);
      }

      const audioFormat = request.audio_format ?? 'wav';
      const requestId = response.headers.get('X-Request-ID') ?? undefined;

      if (!response.body) {
        const blob = await response.blob();
        return {
          objectUrl: URL.createObjectURL(blob),
          audio_format: audioFormat,
          request_id: requestId,
          streamed: false
        };
      }

      const mediaSourceUrl = this.tryCreateProgressiveMediaSourceUrl(response.body, audioFormat, controller.signal);
      if (mediaSourceUrl) {
        return {
          objectUrl: mediaSourceUrl,
          audio_format: audioFormat,
          request_id: requestId,
          streamed: true
        };
      }

      const chunks: ArrayBuffer[] = [];
      const reader = response.body.getReader();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (value) chunks.push(value.slice().buffer as ArrayBuffer);
      }

      return {
        objectUrl: URL.createObjectURL(new Blob(chunks, { type: `audio/${audioFormat}` })),
        audio_format: audioFormat,
        request_id: requestId,
        streamed: response.headers.get('X-TTS-Streaming') === 'true'
      };
    } catch (error) {
      throw this.toUserFriendlyError(error);
    } finally {
      globalThis.clearTimeout(timeout);
      cancelExternalAbort();
    }
  }


  private tryCreateProgressiveMediaSourceUrl(body: ReadableStream<Uint8Array>, audioFormat: TTSAudioFormat, signal: AbortSignal): string | null {
    const mediaSourceType = `audio/${audioFormat}`;
    const maybeMediaSource = globalThis.MediaSource;
    if (!maybeMediaSource || !maybeMediaSource.isTypeSupported(mediaSourceType)) {
      return null;
    }

    const mediaSource = new maybeMediaSource();
    const objectUrl = URL.createObjectURL(mediaSource);

    mediaSource.addEventListener(
      'sourceopen',
      () => {
        const sourceBuffer = mediaSource.addSourceBuffer(mediaSourceType);
        const reader = body.getReader();
        const queue: ArrayBuffer[] = [];
        let done = false;

        const appendNext = () => {
          if (sourceBuffer.updating || queue.length === 0) {
            if (done && !sourceBuffer.updating && mediaSource.readyState === 'open') {
              mediaSource.endOfStream();
            }
            return;
          }
          const next = queue.shift();
          if (next) sourceBuffer.appendBuffer(next);
        };

        sourceBuffer.addEventListener('updateend', appendNext);

        const pump = async () => {
          try {
            while (!signal.aborted) {
              const { done: readDone, value } = await reader.read();
              if (readDone) break;
              if (value) {
                queue.push(value.slice().buffer as ArrayBuffer);
                appendNext();
              }
            }
            done = true;
            appendNext();
          } catch {
            if (mediaSource.readyState === 'open') {
              mediaSource.endOfStream('decode');
            }
          }
        };

        void pump();
      },
      { once: true }
    );

    return objectUrl;
  }

  private async parseJsonResponse<T>(response: Response): Promise<T> {
    const text = await response.text();

    if (!text) {
      return {} as T;
    }

    try {
      return JSON.parse(text) as T;
    } catch (error) {
      throw new TTSServiceError('The local voice service returned an unreadable response.', {
        status: response.status,
        cause: error
      });
    }
  }

  private toServiceError(response: Response, body: BackendErrorBody): TTSServiceError {
    const error = body.detail?.error;
    return new TTSServiceError(error?.message ?? 'The local voice service could not create speech for that line.', {
      status: response.status,
      code: error?.code,
      retryable: error?.retryable,
      details: error?.details
    });
  }

  private toUserFriendlyError(error: unknown): TTSServiceError {
    if (error instanceof TTSServiceError) {
      return error;
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      return new TTSServiceError('Speech playback was cancelled.', { code: 'tts_cancelled', retryable: true, cause: error });
    }

    return new TTSServiceError('Reverie could not reach the local voice service. Text chat is still available.', { cause: error });
  }

  private forwardAbort(signal: AbortSignal | undefined, controller: AbortController): () => void {
    if (!signal) {
      return () => undefined;
    }

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

  if (typeof envBaseUrl === 'string' && envBaseUrl.trim().length > 0) {
    return envBaseUrl;
  }

  if (dev) {
    return DEFAULT_API_BASE_URL;
  }

  return DEFAULT_API_BASE_URL;
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, '');
}

export const ttsService = new TTSService();
