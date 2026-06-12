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


export type TTSStreamEvent =
  | { type: 'start'; request_id: string }
  | {
      type: 'chunk';
      request_id: string;
      backend: 'orpheus' | 'piper';
      voice_id: string;
      audio_format: TTSAudioFormat;
      sample_rate: number;
      sequence: number;
      fallback_used?: boolean;
      audio_base64: string;
    }
  | {
      type: 'done';
      request_id: string;
      backend: 'orpheus' | 'piper';
      voice_id: string;
      audio_format: TTSAudioFormat;
      sample_rate: number;
      fallback_used?: boolean;
      duration_seconds?: number | null;
    }
  | { type: 'error'; request_id: string; error: { code?: string; message?: string; retryable?: boolean; details?: unknown } };

export interface TTSStreamCallbacks {
  onStart?: (event: Extract<TTSStreamEvent, { type: 'start' }>) => void;
  onChunk?: (event: Extract<TTSStreamEvent, { type: 'chunk' }>, bytes: Uint8Array) => void | Promise<void>;
  onDone?: (event: Extract<TTSStreamEvent, { type: 'done' }>) => void | Promise<void>;
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


  async streamSpeech(
    request: TTSGenerateRequest,
    callbacks: TTSStreamCallbacks,
    options: { signal?: AbortSignal } = {}
  ): Promise<void> {
    const url = `${this.baseUrl}/api/tts/generate`;
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);
    const cancelExternalAbort = this.forwardAbort(options.signal, controller);

    try {
      const response = await this.fetcher(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/x-ndjson'
        },
        body: JSON.stringify({ ...request, stream: true, audio_format: request.audio_format ?? 'wav' }),
        signal: controller.signal
      });

      if (!response.ok) {
        const body = await this.parseJsonResponse<BackendErrorBody>(response);
        throw this.toServiceError(response, body);
      }
      if (!response.body) {
        throw new TTSServiceError('The local voice service did not open a speech stream.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        for (const line of lines) {
          await this.handleStreamLine(line, callbacks);
        }
      }

      buffer += decoder.decode();
      if (buffer.trim()) await this.handleStreamLine(buffer, callbacks);
    } catch (error) {
      throw this.toUserFriendlyError(error);
    } finally {
      globalThis.clearTimeout(timeout);
      cancelExternalAbort();
    }
  }

  private async handleStreamLine(line: string, callbacks: TTSStreamCallbacks): Promise<void> {
    if (!line.trim()) return;
    let event: TTSStreamEvent;
    try {
      event = JSON.parse(line) as TTSStreamEvent;
    } catch (error) {
      throw new TTSServiceError('The local voice stream returned malformed audio metadata.', { cause: error });
    }
    if (event.type === 'start') {
      callbacks.onStart?.(event);
      return;
    }
    if (event.type === 'chunk') {
      await callbacks.onChunk?.(event, base64ToBytes(event.audio_base64));
      return;
    }
    if (event.type === 'done') {
      await callbacks.onDone?.(event);
      return;
    }
    throw new TTSServiceError(event.error.message ?? 'The local voice stream failed.', {
      code: event.error.code,
      retryable: event.error.retryable,
      details: event.error.details
    });
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

function base64ToBytes(audioBase64: string): Uint8Array {
  const binary = atob(audioBase64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes;
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, '');
}

export const ttsService = new TTSService();
