import { dev } from '$app/environment';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const DEFAULT_COMFYUI_BASE_URL = 'http://127.0.0.1:8188';
const DEFAULT_TIMEOUT_MS = 15 * 60_000;

export type ImageQualityPreset = 'preview_8gb' | 'balanced_8gb' | 'high_8gb';
export type ImageJobStatus = 'queued' | 'waiting_for_resources' | 'paused' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface ImageGenerateRequest {
  prompt: string;
  context?: Record<string, unknown> | null;
  negative_prompt?: string;
  quality_preset?: ImageQualityPreset;
}

export interface ImageJobErrorPayload {
  code?: string;
  message?: string;
  details?: unknown;
  retryable?: boolean;
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
  error?: ImageJobErrorPayload | null;
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
  error?: ImageJobErrorPayload | null;
  fallback_used?: boolean;
  vram_free_mb?: number | null;
  vram_required_mb?: number | null;
}

export interface ImageEventCallbacks {
  onEvent?: (event: ImageJobEvent) => void | Promise<void>;
}

export interface ImageServiceOptions {
  baseUrl?: string;
  comfyUiBaseUrl?: string;
  timeoutMs?: number;
  fetcher?: typeof fetch;
}

interface BackendErrorBody {
  detail?: {
    error?: ImageJobErrorPayload;
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
  private readonly comfyUiBaseUrl: string;
  private readonly timeoutMs: number;
  private readonly fetcher: typeof fetch;

  constructor(options: ImageServiceOptions = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? getConfiguredBaseUrl());
    this.comfyUiBaseUrl = normalizeBaseUrl(options.comfyUiBaseUrl ?? getConfiguredComfyUiBaseUrl());
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.fetcher = options.fetcher ?? fetch;
  }

  async generateImage(request: ImageGenerateRequest, options: { signal?: AbortSignal } = {}): Promise<ImageGenerateResponse> {
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);
    const cancelExternalAbort = this.forwardAbort(options.signal, controller);

    try {
      const response = await this.fetcher(`${this.baseUrl}/api/images/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json'
        },
        body: JSON.stringify({ ...request, quality_preset: request.quality_preset ?? 'preview_8gb' }),
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

  async getJob(jobId: string): Promise<ImageJobRead> {
    const response = await this.fetcher(`${this.baseUrl}/api/images/${encodeURIComponent(jobId)}`, {
      headers: { Accept: 'application/json' }
    });
    const body = await this.parseJsonResponse<ImageJobRead | BackendErrorBody>(response);
    if (!response.ok) throw this.toServiceError(response, body as BackendErrorBody);
    return body as ImageJobRead;
  }

  async cancelJob(jobId: string): Promise<ImageJobRead> {
    const response = await this.fetcher(`${this.baseUrl}/api/images/${encodeURIComponent(jobId)}/cancel`, {
      method: 'POST',
      headers: { Accept: 'application/json' }
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
    if (!response.body) throw new ImageServiceError('The local image service did not open a progress stream.');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
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
    } catch (error) {
      throw this.toUserFriendlyError(error);
    }
  }

  resolveOutputUrl(outputPath: string): string {
    const trimmed = outputPath.trim();
    if (!trimmed) return '';
    if (/^(https?:|data:|blob:|file:)/i.test(trimmed)) return trimmed;
    if (trimmed.startsWith('/') || /^[a-z]:[\\/]/i.test(trimmed)) return `file://${trimmed}`;

    const [filename, query = ''] = trimmed.split('?');
    const params = new URLSearchParams(query);
    if (!params.has('filename')) params.set('filename', filename);
    if (!params.has('type')) params.set('type', 'output');
    return `${this.comfyUiBaseUrl}/view?${params.toString()}`;
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
      throw new ImageServiceError('The local image stream returned malformed progress metadata.', { cause: error });
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
      return new ImageServiceError('Image generation was cancelled.', { code: 'image_cancelled', retryable: true, cause: error });
    }
    return new ImageServiceError('Reverie could not reach the local image service. Chat and voice are still available.', { cause: error });
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

function getConfiguredComfyUiBaseUrl(): string {
  const envBaseUrl = import.meta.env.VITE_REVERIE_COMFYUI_BASE_URL;
  if (typeof envBaseUrl === 'string' && envBaseUrl.trim().length > 0) return envBaseUrl;
  return dev ? DEFAULT_COMFYUI_BASE_URL : DEFAULT_COMFYUI_BASE_URL;
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, '');
}

export const imageService = new ImageService();
