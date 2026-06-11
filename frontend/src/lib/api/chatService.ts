import { dev } from '$app/environment';

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

export type ChatMemoryStatus = 'used' | 'empty' | 'disabled' | 'unavailable' | 'unknown';

/** Lightweight metadata that tells the UI whether long-term memory shaped a reply. */
export interface ChatMemoryContext {
  status: ChatMemoryStatus;
  used: boolean;
  /** Number of memories or context snippets, when the backend exposes it. */
  itemCount?: number;
  /** Optional warm, non-technical label from the backend. Never required. */
  label?: string;
}

export interface ChatResponse {
  model: string;
  message: MessagePayload;
  done: boolean;
  memoryContext?: ChatMemoryContext;
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
  memoryContext?: ChatMemoryContext;
}

export interface ChatStreamMemoryEvent {
  event: 'memory';
  memoryContext: ChatMemoryContext;
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
  memoryContext?: ChatMemoryContext;
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

interface BackendStreamMessageBody {
  content?: unknown;
  model?: unknown;
  request_id?: unknown;
  requestId?: unknown;
  memory?: unknown;
  memory_context?: unknown;
  memoryContext?: unknown;
  memory_used?: unknown;
}

interface BackendStreamErrorBody {
  error?: unknown;
  details?: unknown;
  request_id?: unknown;
  requestId?: unknown;
}

interface BackendStreamDoneBody {
  done?: unknown;
  request_id?: unknown;
  requestId?: unknown;
  memory?: unknown;
  memory_context?: unknown;
  memoryContext?: unknown;
  memory_used?: unknown;
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
        requestId: this.readRequestId(body as unknown as Record<string, unknown>),
        memoryContext: this.extractMemoryContext(body as unknown as Record<string, unknown>)
      };
    }

    if (rawEvent.event === 'memory') {
      return this.toChatStreamMemoryEvent(data);
    }

    if (rawEvent.event === 'error') {
      const body = data as BackendStreamErrorBody;
      return {
        event: 'error',
        error: typeof body.error === 'string' ? body.error : 'The companion stream reported an error.',
        requestId: this.readRequestId(body as unknown as Record<string, unknown>),
        details: body.details
      };
    }

    if (rawEvent.event === 'done') {
      const body = data as BackendStreamDoneBody;
      return {
        event: 'done',
        done: typeof body.done === 'boolean' ? body.done : true,
        requestId: this.readRequestId(body as unknown as Record<string, unknown>),
        memoryContext: this.extractMemoryContext(body as unknown as Record<string, unknown>)
      };
    }

    throw new ChatServiceError(`The companion stream sent an unsupported '${rawEvent.event}' event.`);
  }

  private toChatResponse(body: unknown): ChatResponse {
    const response = body as ChatResponse & Record<string, unknown>;

    return {
      ...response,
      memoryContext: this.extractMemoryContext(response)
    };
  }

  private toChatStreamMemoryEvent(data: unknown): ChatStreamMemoryEvent {
    const body = this.isRecord(data) ? data : {};
    const memoryContext = this.extractMemoryContext(body) ?? this.normalizeMemoryContext(body);

    return {
      event: 'memory',
      memoryContext: memoryContext ?? { status: 'unknown', used: false },
      requestId: this.readRequestId(body as unknown as Record<string, unknown>)
    };
  }

  private extractMemoryContext(body: Record<string, unknown>): ChatMemoryContext | undefined {
    const candidate = body.memoryContext ?? body.memory_context ?? body.memory ?? this.getNestedMemory(body);
    const normalized = this.normalizeMemoryContext(candidate);

    if (normalized) {
      return normalized;
    }

    if (typeof body.memory_used === 'boolean') {
      return { status: body.memory_used ? 'used' : 'empty', used: body.memory_used };
    }

    return undefined;
  }

  private getNestedMemory(body: Record<string, unknown>): unknown {
    const context = body.context;
    if (!this.isRecord(context)) {
      return undefined;
    }

    return context.memoryContext ?? context.memory_context ?? context.memory;
  }

  private normalizeMemoryContext(value: unknown): ChatMemoryContext | undefined {
    if (value === undefined || value === null || value === false) {
      return undefined;
    }

    if (typeof value === 'boolean') {
      return { status: value ? 'used' : 'empty', used: value };
    }

    if (typeof value === 'string') {
      return value.trim().length > 0 ? { status: 'used', used: true } : { status: 'empty', used: false };
    }

    if (Array.isArray(value)) {
      return { status: value.length > 0 ? 'used' : 'empty', used: value.length > 0, itemCount: value.length };
    }

    if (!this.isRecord(value)) {
      return undefined;
    }

    const explicitUsed = this.readBoolean(value, ['used', 'has_context', 'hasContext', 'memory_used']);
    const status = this.readMemoryStatus(value.status) ?? this.statusFromFlags(value);
    const itemCount = this.readNumber(value, ['item_count', 'itemCount', 'count', 'memory_count', 'memoryCount']);
    const label = this.readString(value, ['label', 'message']);
    const hasSummary = Boolean(this.readString(value, ['summary', 'context']));
    const used = explicitUsed ?? status === 'used';
    const inferredUsed = used || hasSummary || (itemCount !== undefined && itemCount > 0);
    const resolvedStatus = status && status !== 'empty' ? status : inferredUsed ? 'used' : status ?? 'empty';

    return {
      status: resolvedStatus,
      used: resolvedStatus === 'used' && inferredUsed,
      ...(itemCount !== undefined ? { itemCount } : {}),
      ...(label ? { label } : {})
    };
  }

  private statusFromFlags(value: Record<string, unknown>): ChatMemoryStatus | undefined {
    if (value.disabled === true) return 'disabled';
    if (value.unavailable === true || value.error === true) return 'unavailable';
    if (value.empty === true) return 'empty';
    return undefined;
  }

  private readMemoryStatus(value: unknown): ChatMemoryStatus | undefined {
    if (typeof value !== 'string') {
      return undefined;
    }

    const normalized = value.toLowerCase();
    if (['used', 'empty', 'disabled', 'unavailable', 'unknown'].includes(normalized)) {
      return normalized as ChatMemoryStatus;
    }

    return undefined;
  }

  private readRequestId(body: Record<string, unknown>): string | undefined {
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

  private readString(value: Record<string, unknown>, keys: string[]): string | undefined {
    for (const key of keys) {
      const candidate = value[key];
      if (typeof candidate === 'string' && candidate.trim()) {
        return candidate.trim();
      }
    }

    return undefined;
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
