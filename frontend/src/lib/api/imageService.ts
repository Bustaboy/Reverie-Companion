import { dev } from '$app/environment';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 30_000;

export type ImageQualityPreset = 'preview_8gb' | 'balanced_8gb' | 'high_8gb';
export type ImageJobStatus = 'queued' | 'waiting_for_resources' | 'paused' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface ImageGenerateRequest {
  prompt: string;
  context?: Record<string, unknown> | null;
  negative_prompt?: string | null;
  quality_preset?: ImageQualityPreset;
}

export interface ImageJobRead {
  job_id: string;
  status: ImageJobStatus;
  prompt: string;
  negative_prompt: string;
  requested_preset: ImageQualityPreset;
  active_preset: ImageQualityPreset;
  created_at: string;
  updated_at: string;
  progress: number;
  phase: string;
  message: string;
  output_paths: string[];
  error?: { code?: string; message?: string; details?: unknown; retryable?: boolean } | null;
  fallback_used?: boolean;
  resource_mode?: string;
  vram_free_mb?: number | null;
  vram_required_mb?: number | null;
}

export interface ImageGenerateResponse {
  request_id: string;
  job: ImageJobRead;
}

export interface ImageJobEvent {
  event: string;
  job_id: string;
  sequence: number;
  timestamp: string;
  status: ImageJobStatus;
  phase: string;
  progress: number;
  message: string;
  resource_mode?: string;
  output_paths: string[];
  error?: { code?: string; message?: string; details?: unknown; retryable?: boolean } | null;
  fallback_used?: boolean;
  vram_free_mb?: number | null;
  vram_required_mb?: number | null;
}

export interface ImageEventCallbacks {
  onEvent?: (event: ImageJobEvent) => void | Promise<void>;
}

export interface ImageServiceOptions {
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

export class ImageServiceError extends Error {
  readonly status?: number;
  readonly code?: string;
  readonly retryable?: boolean;
  readonly details?: unknown;

  constructor(message: string, options: { status?: number; code?: string; retryable?: boolean; details?: unknown; cause?: unknown } = {}) {
    super(message, { cause: options.cause });
    this.name = 'ImageServiceError';
    this.status = options.status;
    this.code = options.code;
    this.retryable = options.retryable;
    this.details = options.details;
  }
}

export class ImageService {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly fetcher: typeof fetch;

  constructor(options: ImageServiceOptions = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? getConfiguredBaseUrl());
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.fetcher = options.fetcher ?? fetch;
  }

  getImageUrl(jobId: string, outputPath: string): string {
    if (/^(https?:|data:|blob:|file:)/i.test(outputPath)) return outputPath;
    const filename = outputPath.split(/[\\/]/).filter(Boolean).pop() ?? outputPath;
    return `${this.baseUrl}/api/images/${encodeURIComponent(jobId)}/outputs/${encodeURIComponent(filename)}`;
  }

  async generateImage(request: ImageGenerateRequest, options: { signal?: AbortSignal } = {}): Promise<ImageGenerateResponse> {
    const url = `${this.baseUrl}/api/images/generate`;
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);
    const cancelExternalAbort = this.forwardAbort(options.signal, controller);

    try {
      const response = await this.fetcher(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify(request),
        signal: controller.signal
      });
      const body = await this.parseJsonResponse<ImageGenerateResponse | BackendErrorBody>(response);
      if (!response.ok) throw this.toServiceError(response, body as BackendErrorBody);
      return body as ImageGenerateResponse;
    } catch (error) {
      throw this.toUserFriendlyError(error);
    } finally {
      globalThis.clearTimeout(timeout);
      cancelExternalAbort();
    }
  }

  async cancelJob(jobId: string, options: { signal?: AbortSignal } = {}): Promise<ImageJobRead> {
    const response = await this.fetcher(`${this.baseUrl}/api/images/${encodeURIComponent(jobId)}/cancel`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
      signal: options.signal
    });
    const body = await this.parseJsonResponse<ImageJobRead | BackendErrorBody>(response);
    if (!response.ok) throw this.toServiceError(response, body as BackendErrorBody);
    return body as ImageJobRead;
  }

  async streamJobEvents(jobId: string, callbacks: ImageEventCallbacks, options: { signal?: AbortSignal } = {}): Promise<void> {
    const response = await this.fetcher(`${this.baseUrl}/api/images/${encodeURIComponent(jobId)}/events`, {
      headers: { Accept: 'text/event-stream' },
      signal: options.signal
    });

    if (!response.ok) {
      const body = await this.parseJsonResponse<BackendErrorBody>(response);
      throw this.toServiceError(response, body);
    }
    if (!response.body) throw new ImageServiceError('The local image worker did not open a progress stream.');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split('\n\n');
      buffer = frames.pop() ?? '';
      for (const frame of frames) await this.handleSseFrame(frame, callbacks);
    }

    buffer += decoder.decode();
    if (buffer.trim()) await this.handleSseFrame(buffer, callbacks);
  }

  private async handleSseFrame(frame: string, callbacks: ImageEventCallbacks): Promise<void> {
    const dataLines = frame
      .split('\n')
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart());
    if (dataLines.length === 0) return;

    try {
      await callbacks.onEvent?.(JSON.parse(dataLines.join('\n')) as ImageJobEvent);
    } catch (error) {
      throw new ImageServiceError('The local image progress stream returned unreadable metadata.', { cause: error });
    }
  }

  private async parseJsonResponse<T>(response: Response): Promise<T> {
    const text = await response.text();
    if (!text) return {} as T;
    try {
      return JSON.parse(text) as T;
    } catch (error) {
      throw new ImageServiceError('The local image service returned an unreadable response.', { status: response.status, cause: error });
    }
  }

  private toServiceError(response: Response, body: BackendErrorBody): ImageServiceError {
    const error = body.detail?.error;
    return new ImageServiceError(error?.message ?? 'The local image service could not queue that image.', {
      status: response.status,
      code: error?.code,
      retryable: error?.retryable,
      details: error?.details
    });
  }

  private toUserFriendlyError(error: unknown): ImageServiceError {
    if (error instanceof ImageServiceError) return error;
    if (error instanceof DOMException && error.name === 'AbortError') {
      return new ImageServiceError('Image generation was cancelled.', { code: 'image_cancelled' });
    }
    if (error instanceof TypeError) {
      return new ImageServiceError('The local image backend is unreachable. Chat and voice are still safe to use.', {
        code: 'image_backend_unavailable',
        retryable: true,
        cause: error
      });
    }
    return new ImageServiceError('The local image worker paused unexpectedly. Chat and TTS can continue.', { cause: error });
  }

  private forwardAbort(signal: AbortSignal | undefined, controller: AbortController): () => void {
    if (!signal) return () => undefined;
    const abort = () => controller.abort();
    if (signal.aborted) abort();
    signal.addEventListener('abort', abort, { once: true });
    return () => signal.removeEventListener('abort', abort);
  }
}

const normalizeBaseUrl = (url: string): string => url.replace(/\/$/, '');

const getConfiguredBaseUrl = (): string => {
  const envValue = import.meta.env.VITE_REVERIE_API_BASE_URL as string | undefined;
  if (envValue) return envValue;
  return dev ? DEFAULT_API_BASE_URL : DEFAULT_API_BASE_URL;
};

export const imageService = new ImageService();
