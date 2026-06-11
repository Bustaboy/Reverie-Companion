import { dev } from '$app/environment';
import type { GrowthNotification, MemoryContext, MemoryContextItem } from '$lib/types/chat';
import {
  VISUAL_EXPRESSIONS,
  VISUAL_POSES,
  type VisualExpression,
  type VisualPose,
  type VisualState
} from '$lib/types/visualNovel';

/** Backend origin used when no Vite/Tauri environment override is provided. */
const DEFAULT_API_BASE_URL = 'http://localhost:8000';

/** Default request timeout for local inference startup or slow first-token responses. */
const DEFAULT_TIMEOUT_MS = 60_000;

export type MessageRole = 'system' | 'user' | 'assistant';

/**
 * Chat history item accepted by the frontend service.
 *
 * The optional id/createdAt fields make this compatible with existing UI chat
 * messages while keeping the API payload focused on role + content.
 */
export interface Message {
  role: MessageRole;
  content: string;
  id?: string;
  createdAt?: Date | string;
}

export interface ChatRequest {
  messages: MessagePayload[];
  model?: string;
  temperature?: number;
  top_p?: number;
  num_predict?: number;
  /** False for regular JSON completions; true for Server-Sent Event streams. */
  stream: boolean;
}

export interface MessagePayload {
  role: MessageRole;
  content: string;
}

export interface ChatResponse {
  model: string;
  message: MessagePayload;
  done: boolean;
  /** Optional normalized memory context returned by newer backends. */
  memoryContext?: MemoryContext;
  /** Optional subtle note that a journaled growth signal is available. */
  growthNotification?: GrowthNotification;
  /** Deterministic visual metadata for the current assistant turn. */
  visualState?: VisualState;
}

export interface ChatStreamOptions {
  /** Optional cancellation signal for Svelte components to stop generation. */
  signal?: AbortSignal;
}

export interface ChatStreamMessageEvent {
  event: 'message';
  content: string;
  model?: string;
  requestId?: string;
  memoryContext?: MemoryContext;
  growthNotification?: GrowthNotification;
  visualState?: VisualState;
}

export interface ChatStreamMemoryEvent {
  event: 'memory';
  memoryContext: MemoryContext;
  requestId?: string;
}

export interface ChatStreamErrorEvent {
  event: 'error';
  error: string;
  requestId?: string;
  details?: unknown;
}

export interface ChatStreamDoneEvent {
  event: 'done';
  done: boolean;
  requestId?: string;
  memoryContext?: MemoryContext;
  growthNotification?: GrowthNotification;
  visualState?: VisualState;
}

export type ChatStreamEvent =
  | ChatStreamMessageEvent
  | ChatStreamMemoryEvent
  | ChatStreamErrorEvent
  | ChatStreamDoneEvent;

export interface ChatServiceOptions {
  /** Backend base URL, for example http://localhost:8000. */
  baseUrl?: string;
  /** Timeout applied to each JSON request and to stream startup/first event. */
  timeoutMs?: number;
  /** Optional fetch implementation for tests or future Tauri adapters. */
  fetcher?: typeof fetch;
}

interface BackendErrorBody {
  detail?: {
    error?: string;
    details?: unknown;
    request_id?: string;
  };
}

interface RawSseEvent {
  event: string;
  data: string;
}

interface BackendVisualStateBody {
  visual_state?: unknown;
  visualState?: unknown;
}

interface BackendGrowthNotificationBody extends BackendVisualStateBody {
  growth_notification?: unknown;
  growthNotification?: unknown;
}

interface BackendMemoryContextBody extends BackendGrowthNotificationBody {
  memory_context?: unknown;
  memoryContext?: unknown;
  memory?: unknown;
  memories?: unknown;
  context?: unknown;
  used?: unknown;
  memory_used?: unknown;
  has_context?: unknown;
  hasContext?: unknown;
  status?: unknown;
  summary?: unknown;
  preview?: unknown;
  label?: unknown;
  message?: unknown;
  items?: unknown;
  results?: unknown;
  item_count?: unknown;
  itemCount?: unknown;
  count?: unknown;
  memory_count?: unknown;
  memoryCount?: unknown;
  disabled?: unknown;
  unavailable?: unknown;
  error?: unknown;
  empty?: unknown;
  request_id?: unknown;
  requestId?: unknown;
}

interface BackendStreamMessageBody extends BackendMemoryContextBody {
  content?: unknown;
  model?: unknown;
  request_id?: unknown;
}

interface BackendStreamErrorBody {
  error?: unknown;
  details?: unknown;
  request_id?: unknown;
  requestId?: unknown;
}

interface BackendStreamDoneBody extends BackendMemoryContextBody {
  done?: unknown;
  request_id?: unknown;
}

/** User-facing error with optional diagnostic context for logs/support. */
export class ChatServiceError extends Error {
  readonly status?: number;
  readonly requestId?: string;
  readonly details?: unknown;

  constructor(message: string, options: { status?: number; requestId?: string; details?: unknown; cause?: unknown } = {}) {
    super(message, { cause: options.cause });
    this.name = 'ChatServiceError';
    this.status = options.status;
    this.requestId = options.requestId;
    this.details = options.details;
  }
}

/**
 * Small API client for Reverie's local FastAPI backend.
 *
 * The class intentionally keeps request creation and transport separate enough
 * to add streaming, memory context, character state, and settings later without
 * pushing backend details into Svelte components.
 */
export class ChatService {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly fetcher: typeof fetch;

  constructor(options: ChatServiceOptions = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? getConfiguredBaseUrl());
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.fetcher = options.fetcher ?? fetch;
  }

  /** Send one user message plus optional prior conversation history to /chat. */
  async sendMessage(message: string, history: Message[] = []): Promise<ChatResponse> {
    return this.postChat(this.createChatRequest(message, history, false));
  }

  /**
   * Stream one user message plus optional prior conversation history from /chat.
   *
   * Consumers can append `message` event content as it arrives, surface `error`
   * events without losing already-received text, and always clean up when a
   * terminal `done` event is yielded. Breaking from the async iterator aborts
   * the HTTP request so local generation work is not left running unnecessarily.
   */
  async *sendMessageStream(
    message: string,
    history: Message[] = [],
    options: ChatStreamOptions = {}
  ): AsyncGenerator<ChatStreamEvent, void, void> {
    const request = this.createChatRequest(message, history, true);
    const url = `${this.baseUrl}/chat`;
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);
    const cancelExternalAbort = this.forwardAbort(options.signal, controller);
    let responseBody: ReadableStream<Uint8Array> | null = null;
    let sawDoneEvent = false;

    this.logRequest(url, request);

    try {
      const response = await this.fetcher(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream'
        },
        body: JSON.stringify(request),
        signal: controller.signal
      });

      if (!response.ok) {
        const responseBody = await this.parseJsonResponse<BackendErrorBody>(response);
        throw this.toServiceError(response, responseBody);
      }

      if (!response.body) {
        throw new ChatServiceError('The companion service opened a stream without a readable response body.', {
          status: response.status
        });
      }

      responseBody = response.body;

      for await (const rawEvent of this.readSseEvents(response.body)) {
        globalThis.clearTimeout(timeout);
        const streamEvent = this.toChatStreamEvent(rawEvent);

        if (streamEvent.event === 'message') {
          this.logStreamToken(url, streamEvent);
          yield streamEvent;
          continue;
        }

        if (streamEvent.event === 'error') {
          this.logStreamError(url, streamEvent);
          yield streamEvent;
          continue;
        }

        sawDoneEvent = true;
        this.logResponse(url, streamEvent);
        yield streamEvent;
        return;
      }

      if (!sawDoneEvent) {
        throw new ChatServiceError('The companion stream ended before sending a completion event.');
      }
    } catch (error) {
      throw this.toUserFriendlyError(error);
    } finally {
      globalThis.clearTimeout(timeout);
      cancelExternalAbort();

      if (!sawDoneEvent && responseBody && !controller.signal.aborted) {
        controller.abort();
      }
    }
  }

  private createChatRequest(message: string, history: Message[], stream: boolean): ChatRequest {
    const trimmedMessage = message.trim();

    if (!trimmedMessage) {
      throw new ChatServiceError('Please enter a message before sending.');
    }

    return {
      messages: [...this.toPayloadMessages(history), { role: 'user', content: trimmedMessage }],
      stream
    };
  }

  private async postChat(request: ChatRequest): Promise<ChatResponse> {
    const url = `${this.baseUrl}/chat`;
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), this.timeoutMs);

    this.logRequest(url, request);

    try {
      const response = await this.fetcher(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json'
        },
        body: JSON.stringify(request),
        signal: controller.signal
      });

      const responseBody = await this.parseJsonResponse<ChatResponse | BackendErrorBody>(response);

      if (!response.ok) {
        throw this.toServiceError(response, responseBody as BackendErrorBody);
      }

      const chatResponse = this.toChatResponse(responseBody);
      this.logResponse(url, chatResponse);
      return chatResponse;
    } catch (error) {
      throw this.toUserFriendlyError(error);
    } finally {
      globalThis.clearTimeout(timeout);
    }
  }

  private toPayloadMessages(history: Message[]): MessagePayload[] {
    return history
      .map((item) => ({
        role: item.role,
        content: item.content.trim()
      }))
      .filter((item) => item.content.length > 0);
  }

  private async parseJsonResponse<T>(response: Response): Promise<T> {
    const text = await response.text();

    if (!text) {
      return {} as T;
    }

    try {
      return JSON.parse(text) as T;
    } catch (error) {
      throw new ChatServiceError('The companion service returned an unreadable response.', {
        status: response.status,
        cause: error
      });
    }
  }

  private toChatResponse(responseBody: unknown): ChatResponse {
    const body = responseBody as ChatResponse & BackendMemoryContextBody;
    return {
      ...body,
      memoryContext: this.extractMemoryContext(body),
      growthNotification: this.extractGrowthNotification(body),
      visualState: this.extractVisualState(body)
    };
  }

  private async *readSseEvents(stream: ReadableStream<Uint8Array>): AsyncGenerator<RawSseEvent, void, void> {
    const reader = stream.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const events = this.drainSseBuffer(buffer);
        buffer = events.remainder;

        for (const event of events.parsedEvents) {
          yield event;
        }
      }

      buffer += decoder.decode();

      if (buffer.trim().length > 0) {
        yield this.parseSseEvent(buffer);
      }
    } finally {
      try {
        await reader.cancel();
      } catch {
        // The stream may already be closed or aborted; cancellation is best-effort cleanup.
      }

      reader.releaseLock();
    }
  }

  private drainSseBuffer(buffer: string): { parsedEvents: RawSseEvent[]; remainder: string } {
    const parsedEvents: RawSseEvent[] = [];
    let remainder = buffer;
    let delimiterIndex = this.findSseDelimiter(remainder);

    while (delimiterIndex !== -1) {
      const frame = remainder.slice(0, delimiterIndex.index);
      parsedEvents.push(this.parseSseEvent(frame));
      remainder = remainder.slice(delimiterIndex.index + delimiterIndex.length);
      delimiterIndex = this.findSseDelimiter(remainder);
    }

    return { parsedEvents, remainder };
  }

  private findSseDelimiter(buffer: string): { index: number; length: number } | -1 {
    const delimiters = ['\r\n\r\n', '\n\n', '\r\r'];
    const matches = delimiters
      .map((delimiter) => ({ index: buffer.indexOf(delimiter), length: delimiter.length }))
      .filter((match) => match.index !== -1)
      .sort((left, right) => left.index - right.index);

    return matches[0] ?? -1;
  }

  private parseSseEvent(frame: string): RawSseEvent {
    let event = 'message';
    const dataLines: string[] = [];

    for (const rawLine of frame.split(/\r\n|\n|\r/)) {
      if (!rawLine || rawLine.startsWith(':')) {
        continue;
      }

      const separatorIndex = rawLine.indexOf(':');
      const field = separatorIndex === -1 ? rawLine : rawLine.slice(0, separatorIndex);
      const rawValue = separatorIndex === -1 ? '' : rawLine.slice(separatorIndex + 1);
      const value = rawValue.startsWith(' ') ? rawValue.slice(1) : rawValue;

      if (field === 'event') {
        event = value || 'message';
      }

      if (field === 'data') {
        dataLines.push(value);
      }
    }

    return { event, data: dataLines.join('\n') };
  }

  private toChatStreamEvent(rawEvent: RawSseEvent): ChatStreamEvent {
    const data = this.parseSseJson(rawEvent);

    if (rawEvent.event === 'message') {
      const body = data as BackendStreamMessageBody;
      return {
        event: 'message',
        content: typeof body.content === 'string' ? body.content : '',
        model: typeof body.model === 'string' ? body.model : undefined,
        requestId: this.readRequestId(body),
        memoryContext: this.extractMemoryContext(body),
        growthNotification: this.extractGrowthNotification(body),
        visualState: this.extractVisualState(body)
      };
    }

    if (['memory', 'context', 'memory_context'].includes(rawEvent.event)) {
      return this.toChatStreamMemoryEvent(data);
    }

    if (rawEvent.event === 'error') {
      const body = data as BackendStreamErrorBody;
      return {
        event: 'error',
        error: typeof body.error === 'string' ? body.error : 'The companion stream reported an error.',
        requestId: this.readRequestId(body),
        details: body.details
      };
    }

    if (rawEvent.event === 'done') {
      const body = data as BackendStreamDoneBody;
      return {
        event: 'done',
        done: typeof body.done === 'boolean' ? body.done : true,
        requestId: this.readRequestId(body),
        memoryContext: this.extractMemoryContext(body),
        growthNotification: this.extractGrowthNotification(body),
        visualState: this.extractVisualState(body)
      };
    }

    throw new ChatServiceError(`The companion stream sent an unsupported '${rawEvent.event}' event.`);
  }

  private toChatStreamMemoryEvent(data: unknown): ChatStreamMemoryEvent {
    const body = this.isRecord(data) ? data : {};
    const memoryContext = this.extractMemoryContext(body) ?? this.normalizeMemoryContext(body);

    return {
      event: 'memory',
      memoryContext: memoryContext ?? { used: false, status: 'unknown' },
      requestId: this.readRequestId(body)
    };
  }

  private extractGrowthNotification(body: BackendGrowthNotificationBody | Record<string, unknown>): GrowthNotification | undefined {
    const raw = body.growth_notification ?? body.growthNotification;
    if (!this.isRecord(raw)) {
      return undefined;
    }

    const id = this.normalizeText(raw.id);
    const journalEntryId = this.normalizeText(raw.journal_entry_id ?? raw.journalEntryId);
    const message = this.normalizeText(raw.message);
    if (!id || !journalEntryId || !message) {
      return undefined;
    }

    return {
      id,
      journalEntryId,
      createdAt: this.parseDate(raw.created_at ?? raw.createdAt),
      message,
      why: this.normalizeText(raw.why),
      theme: this.normalizeText(raw.theme),
      style: this.normalizeText(raw.style),
      controls: Array.isArray(raw.controls) ? raw.controls.filter((item): item is string => typeof item === 'string') : undefined
    };
  }

  private extractVisualState(body: BackendVisualStateBody | Record<string, unknown>): VisualState | undefined {
    const raw = body.visual_state ?? body.visualState;
    if (!this.isRecord(raw)) {
      return undefined;
    }

    const characterId = this.normalizeText(raw.character_id ?? raw.characterId) ?? 'reverie';
    const expression = this.normalizeVisualExpression(raw.expression);
    const emotion = this.normalizeVisualExpression(raw.emotion ?? raw.expression);
    const pose = this.normalizeVisualPose(raw.pose);
    const background = this.normalizeText(raw.background) ?? 'default';
    const sources = Array.isArray(raw.sources)
      ? raw.sources.filter((item): item is string => typeof item === 'string').slice(0, 8)
      : ['fallback_neutral'];

    return {
      characterId,
      emotion,
      expression,
      pose,
      background,
      intensity: this.clampNumber(this.normalizeNumber(raw.intensity), 0, 1, 0.15),
      confidence: this.clampNumber(this.normalizeNumber(raw.confidence), 0, 1, 0.25),
      sources,
      growthCue: this.normalizeText(raw.growth_cue ?? raw.growthCue)
    };
  }

  private extractMemoryContext(body: BackendMemoryContextBody | Record<string, unknown>): MemoryContext | undefined {
    const explicitContext = body.memory_context ?? body.memoryContext ?? body.memory ?? this.getNestedMemory(body);
    const explicitItems = body.memories ?? body.items ?? body.results;
    const normalized = this.normalizeMemoryContext(explicitContext, explicitItems);

    if (normalized) {
      return normalized;
    }

    return this.normalizeMemoryContext(body, explicitItems);
  }

  private getNestedMemory(body: BackendMemoryContextBody | Record<string, unknown>): unknown {
    const context = body.context;
    if (!this.isRecord(context)) {
      return context;
    }

    return context.memoryContext ?? context.memory_context ?? context.memory ?? context.memories;
  }

  private normalizeMemoryContext(context: unknown, fallbackItems?: unknown): MemoryContext | undefined {
    if (context === null || context === undefined || context === false) {
      return undefined;
    }

    if (typeof context === 'boolean') {
      return { used: context, status: context ? 'used' : 'empty' };
    }

    if (typeof context === 'string') {
      const summary = this.normalizeText(context);
      return summary ? { used: true, status: 'used', summary } : { used: false, status: 'empty' };
    }

    if (Array.isArray(context)) {
      const items = this.normalizeMemoryItems(context);
      return {
        used: context.length > 0,
        status: context.length > 0 ? 'used' : 'empty',
        itemCount: context.length,
        items: items.length > 0 ? items : undefined,
        summary: items[0]?.label
      };
    }

    if (!this.isRecord(context)) {
      return undefined;
    }

    const nestedItems = context.memories ?? context.items ?? context.results ?? fallbackItems;
    const items = this.normalizeMemoryItems(nestedItems);
    const itemCount =
      this.readNumber(context, ['item_count', 'itemCount', 'count', 'memory_count', 'memoryCount']) ??
      (Array.isArray(nestedItems) ? nestedItems.length : undefined);
    const status = this.normalizeMemoryStatus(context.status) ?? this.statusFromFlags(context);
    const used = this.readBoolean(context, ['used', 'has_context', 'hasContext', 'memory_used']);
    const summary = this.normalizeText(
      context.summary ?? context.preview ?? context.label ?? context.message ?? context.context
    );
    const hasMemorySignal =
      used !== undefined || status !== undefined || Boolean(summary) || items.length > 0 || itemCount !== undefined;

    if (!hasMemorySignal) {
      return undefined;
    }

    const unavailableStatus = status === 'disabled' || status === 'unavailable' || status === 'empty';
    const effectiveUsed =
      used ?? (!unavailableStatus && (status === 'used' || Boolean(summary) || items.length > 0 || (itemCount ?? 0) > 0));

    return {
      used: effectiveUsed,
      status: status ?? (effectiveUsed ? 'used' : 'empty'),
      itemCount,
      summary,
      items: items.length > 0 ? items : undefined
    };
  }

  private normalizeMemoryItems(items: unknown): MemoryContextItem[] {
    if (!Array.isArray(items)) {
      return [];
    }

    return items
      .map((item) => this.normalizeMemoryItem(item))
      .filter((item): item is MemoryContextItem => Boolean(item))
      .slice(0, 3);
  }

  private normalizeMemoryItem(item: unknown): MemoryContextItem | undefined {
    if (typeof item === 'string') {
      const label = this.compactMemoryLabel(item);
      return label ? { label } : undefined;
    }

    if (!this.isRecord(item)) {
      return undefined;
    }

    const label = this.compactMemoryLabel(
      item.label ?? item.summary ?? item.text ?? item.content ?? item.memory ?? item.title ?? item.message
    );

    if (!label) {
      return undefined;
    }

    return {
      label,
      id: typeof item.id === 'string' ? item.id : undefined
    };
  }

  private compactMemoryLabel(value: unknown): string | undefined {
    const text = this.normalizeText(value);
    if (!text) {
      return undefined;
    }

    return text.length > 72 ? `${text.slice(0, 69).trimEnd()}…` : text;
  }

  private parseDate(value: unknown): Date {
    if (typeof value === 'string') {
      const parsed = new Date(value);
      if (!Number.isNaN(parsed.getTime())) {
        return parsed;
      }
    }

    return new Date();
  }

  private normalizeText(value: unknown): string | undefined {
    return typeof value === 'string' && value.trim().length > 0 ? value.trim() : undefined;
  }

  private readRequestId(
    body: BackendMemoryContextBody | BackendStreamErrorBody | Record<string, unknown>
  ): string | undefined {
    const requestId = body.request_id ?? body.requestId;
    return typeof requestId === 'string' ? requestId : undefined;
  }

  private readBoolean(value: Record<string, unknown>, keys: string[]): boolean | undefined {
    for (const key of keys) {
      if (typeof value[key] === 'boolean') {
        return value[key];
      }
    }

    return undefined;
  }

  private readNumber(value: Record<string, unknown>, keys: string[]): number | undefined {
    for (const key of keys) {
      const candidate = value[key];
      if (typeof candidate === 'number' && Number.isFinite(candidate)) {
        return candidate;
      }
    }

    return undefined;
  }

  private statusFromFlags(value: Record<string, unknown>): MemoryContext['status'] | undefined {
    if (value.disabled === true) return 'disabled';
    if (value.unavailable === true || value.error === true) return 'unavailable';
    if (value.empty === true) return 'empty';
    return undefined;
  }

  private normalizeMemoryStatus(value: unknown): MemoryContext['status'] | undefined {
    if (typeof value !== 'string') {
      return undefined;
    }

    const normalized = value.toLowerCase();
    const knownStatuses: Array<MemoryContext['status']> = ['used', 'empty', 'disabled', 'unavailable', 'unknown'];
    return knownStatuses.includes(normalized as MemoryContext['status'])
      ? (normalized as MemoryContext['status'])
      : undefined;
  }

  private normalizeVisualExpression(value: unknown): VisualExpression {
    return typeof value === 'string' && VISUAL_EXPRESSIONS.includes(value as VisualExpression)
      ? (value as VisualExpression)
      : 'neutral';
  }

  private normalizeVisualPose(value: unknown): VisualPose {
    return typeof value === 'string' && VISUAL_POSES.includes(value as VisualPose) ? (value as VisualPose) : 'idle';
  }

  private normalizeNumber(value: unknown): number | undefined {
    return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
  }

  private clampNumber(value: number | undefined, min: number, max: number, fallback: number): number {
    if (value === undefined) {
      return fallback;
    }

    return Math.min(max, Math.max(min, value));
  }

  private isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
  }

  private parseSseJson(rawEvent: RawSseEvent): unknown {
    if (!rawEvent.data) {
      return {};
    }

    try {
      return JSON.parse(rawEvent.data) as unknown;
    } catch (error) {
      throw new ChatServiceError('The companion stream returned an unreadable event.', { cause: error });
    }
  }

  private forwardAbort(source: AbortSignal | undefined, target: AbortController): () => void {
    if (!source) {
      return () => undefined;
    }

    if (source.aborted) {
      target.abort(source.reason);
      return () => undefined;
    }

    const abortTarget = () => target.abort(source.reason);
    source.addEventListener('abort', abortTarget, { once: true });
    return () => source.removeEventListener('abort', abortTarget);
  }

  private toServiceError(response: Response, body: BackendErrorBody): ChatServiceError {
    const detail = body.detail;
    const message = detail?.error ?? this.defaultMessageForStatus(response.status);

    return new ChatServiceError(message, {
      status: response.status,
      requestId: detail?.request_id,
      details: detail?.details
    });
  }

  private toUserFriendlyError(error: unknown): ChatServiceError {
    if (error instanceof ChatServiceError) {
      return error;
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      return new ChatServiceError(
        'The companion service took too long to respond or the stream was cancelled. Make sure the local model is running and try again.',
        { cause: error }
      );
    }

    if (error instanceof TypeError) {
      return new ChatServiceError(
        'Could not connect to the local companion service. Make sure the backend is running on the configured address, then try again.',
        { cause: error }
      );
    }

    return new ChatServiceError('Something went wrong while talking to the companion service.', { cause: error });
  }

  private defaultMessageForStatus(status: number): string {
    if (status === 422) {
      return 'The message could not be sent because the request was not valid.';
    }

    if (status >= 500) {
      return 'The local companion service had trouble generating a response. Please try again.';
    }

    return 'The companion service could not process the message.';
  }

  private logRequest(url: string, request: ChatRequest): void {
    if (!dev) return;

    console.debug('[Reverie API] POST', url, {
      messageCount: request.messages.length,
      stream: request.stream
    });
  }

  private logResponse(url: string, response: unknown): void {
    if (!dev) return;

    console.debug('[Reverie API] Response', url, response);
  }

  private logStreamToken(url: string, event: ChatStreamMessageEvent): void {
    if (!dev) return;

    console.debug('[Reverie API] Stream token', url, {
      content: event.content,
      requestId: event.requestId,
      model: event.model
    });
  }

  private logStreamError(url: string, event: ChatStreamErrorEvent): void {
    if (!dev) return;

    console.debug('[Reverie API] Stream error', url, {
      error: event.error,
      requestId: event.requestId,
      details: event.details
    });
  }
}

const getConfiguredBaseUrl = (): string =>
  import.meta.env.VITE_REVERIE_API_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

const normalizeBaseUrl = (baseUrl: string): string => baseUrl.replace(/\/+$/, '');

export const chatService = new ChatService();
