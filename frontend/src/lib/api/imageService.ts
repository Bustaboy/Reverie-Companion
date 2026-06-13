import type { MomentCaptureRecord, MomentCaptureRequest, VisualChangeCanonStatus, VisualChangeEvent, VisualChangeReviewRequest, VisualChangeReviewResponse, VisualFeedbackRequest, VisualFeedbackResponse } from '$lib/types/momentCapture';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 15 * 60_000;

export type ImageQualityPreset = 'preview_8gb' | 'balanced_8gb' | 'high_8gb';
export type ImageJobStatus = 'queued' | 'waiting_for_resources' | 'paused' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface ImageGenerateRequest {
  conversation_id?: string;
  source?: string;
  source_message_id?: string;
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
  pressure?: 'unknown' | 'normal' | 'elevated' | 'critical';
  warning?: string | null;
  conversation_id?: string;
  source?: string | null;
  source_message_id?: string | null;
  character_id?: string | null;
  session_id?: string | null;
  moment_capture_id?: string | null;
  scene_summary?: string | null;
  prompt_hash?: string | null;
  feedback_status?: string;
  review_status?: string;
  canon_status?: string;
  saved_to_assets?: boolean;
}

export interface ImageGenerateResponse {
  request_id: string;
  job: ImageJobRead;
}

export interface MomentCaptureResponse {
  request_id: string;
  record: MomentCaptureRecord;
  job: ImageJobRead;
  prompt_bundle?: Record<string, unknown>;
}

export interface ImageHistoryItem {
  job_id: string;
  conversation_id: string;
  source?: string | null;
  source_message_id?: string | null;
  character_id?: string | null;
  session_id?: string | null;
  moment_capture_id?: string | null;
  scene_summary?: string | null;
  prompt_hash?: string | null;
  feedback_status?: string;
  review_status?: string;
  canon_status?: string;
  is_deleted?: boolean;
  deleted_at?: string | null;
  prompt: string;
  prompt_summary: string;
  negative_prompt: string;
  requested_preset: ImageQualityPreset;
  active_preset: ImageQualityPreset;
  created_at: string;
  completed_at: string;
  output_paths: string[];
  thumbnail_paths: string[];
  fallback_used?: boolean;
  saved_to_assets?: boolean;
  asset_manifest_path?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ImageHistoryResponse {
  items: ImageHistoryItem[];
}

export interface ImageSaveToAssetsResponse {
  item: ImageHistoryItem;
  asset_path: string;
  manifest_path: string;
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
  pressure?: 'unknown' | 'normal' | 'elevated' | 'critical';
  warning?: string | null;
  conversation_id?: string;
  source?: string | null;
  source_message_id?: string | null;
  character_id?: string | null;
  session_id?: string | null;
  moment_capture_id?: string | null;
  scene_summary?: string | null;
  prompt_hash?: string | null;
  feedback_status?: string;
  review_status?: string;
  canon_status?: string;
  saved_to_assets?: boolean;
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
  private readonly timeoutMs: number;
  private readonly fetcher: typeof fetch;

  constructor(options: ImageServiceOptions = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? getConfiguredBaseUrl());
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

  async createMomentCapture(request: MomentCaptureRequest, options: { signal?: AbortSignal } = {}): Promise<MomentCaptureResponse> {
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);
    const cancelExternalAbort = this.forwardAbort(options.signal, controller);

    try {
      const response = await this.fetcher(`${this.baseUrl}/api/moment-capture`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json'
        },
        body: JSON.stringify({ ...request, quality_preset: request.quality_preset ?? 'preview_8gb' }),
        signal: controller.signal
      });
      const body = await this.parseJsonResponse<MomentCaptureResponse | BackendErrorBody>(response);
      if (!response.ok) throw this.toServiceError(response, body as BackendErrorBody);
      return body as MomentCaptureResponse;
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

  async listHistory(conversationId = 'default', filters: { characterId?: string } = {}): Promise<ImageHistoryResponse> {
    const params = new URLSearchParams();
    if (filters.characterId) params.set('character_id', filters.characterId);
    const query = params.toString() ? `?${params.toString()}` : '';
    const response = await this.fetcher(`${this.baseUrl}/api/images/history/${encodeURIComponent(conversationId)}${query}`, {
      headers: { Accept: 'application/json' }
    });
    const body = await this.parseJsonResponse<ImageHistoryResponse | BackendErrorBody>(response);
    if (!response.ok) throw this.toServiceError(response, body as BackendErrorBody);
    return body as ImageHistoryResponse;
  }

  async deleteHistoryItem(jobId: string): Promise<ImageHistoryResponse> {
    const response = await this.fetcher(`${this.baseUrl}/api/images/history/${encodeURIComponent(jobId)}`, {
      method: 'DELETE',
      headers: { Accept: 'application/json' }
    });
    const body = await this.parseJsonResponse<ImageHistoryResponse | BackendErrorBody>(response);
    if (!response.ok) throw this.toServiceError(response, body as BackendErrorBody);
    return body as ImageHistoryResponse;
  }


  async submitMomentCaptureFeedback(captureId: string, request: VisualFeedbackRequest): Promise<VisualFeedbackResponse> {
    const response = await this.fetcher(`${this.baseUrl}/api/moment-capture/${encodeURIComponent(captureId)}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(request)
    });
    const body = await this.parseJsonResponse<VisualFeedbackResponse | BackendErrorBody>(response);
    if (!response.ok) throw this.toServiceError(response, body as BackendErrorBody);
    return body as VisualFeedbackResponse;
  }

  async listVisualChanges(filters: { characterId?: string; status?: VisualChangeCanonStatus } = {}): Promise<VisualChangeEvent[]> {
    const params = new URLSearchParams();
    if (filters.characterId) params.set('character_id', filters.characterId);
    if (filters.status) params.set('status_filter', filters.status);
    const query = params.toString() ? `?${params.toString()}` : '';
    const response = await this.fetcher(`${this.baseUrl}/api/moment-capture/visual-changes${query}`, { headers: { Accept: 'application/json' } });
    const body = await this.parseJsonResponse<VisualChangeEvent[] | BackendErrorBody>(response);
    if (!response.ok) throw this.toServiceError(response, body as BackendErrorBody);
    return body as VisualChangeEvent[];
  }

  async reviewVisualChange(eventId: string, action: 'approve' | 'reject' | 'rollback', request: VisualChangeReviewRequest): Promise<VisualChangeReviewResponse> {
    const response = await this.fetcher(`${this.baseUrl}/api/moment-capture/visual-changes/${encodeURIComponent(eventId)}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(request)
    });
    const body = await this.parseJsonResponse<VisualChangeReviewResponse | BackendErrorBody>(response);
    if (!response.ok) throw this.toServiceError(response, body as BackendErrorBody);
    return body as VisualChangeReviewResponse;
  }

  async saveToCharacterAssets(jobId: string, input: { characterId?: string; assetLabel?: string; outputIndex?: number } = {}): Promise<ImageSaveToAssetsResponse> {
    const response = await this.fetcher(`${this.baseUrl}/api/images/${encodeURIComponent(jobId)}/save-to-assets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        character_id: input.characterId ?? 'default',
        asset_label: input.assetLabel,
        output_index: input.outputIndex ?? 0
      })
    });
    const body = await this.parseJsonResponse<ImageSaveToAssetsResponse | BackendErrorBody>(response);
    if (!response.ok) throw this.toServiceError(response, body as BackendErrorBody);
    return body as ImageSaveToAssetsResponse;
  }

  resolveOutputUrl(jobId: string, outputIndex: number): string {
    return `${this.baseUrl}/api/images/${encodeURIComponent(jobId)}/outputs/${outputIndex}`;
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

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, '');
}

export const imageService = new ImageService();
