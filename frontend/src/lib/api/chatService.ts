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
  /** Keep false for this first non-streaming client implementation. */
  stream: false;
}

export interface MessagePayload {
  role: MessageRole;
  content: string;
}

export interface ChatResponse {
  model: string;
  message: MessagePayload;
  done: boolean;
}

export interface ChatServiceOptions {
  /** Backend base URL, for example http://localhost:8000. */
  baseUrl?: string;
  /** Timeout applied to each request. */
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

  /**
   * Send one user message plus optional prior conversation history to /chat.
   *
   * Streaming is deliberately disabled for this first API layer. When streaming
   * is added, this method can remain the simple completion path while a sibling
   * method exposes an async iterable or SSE reader.
   */
  async sendMessage(message: string, history: Message[] = []): Promise<ChatResponse> {
    const trimmedMessage = message.trim();

    if (!trimmedMessage) {
      throw new ChatServiceError('Please enter a message before sending.');
    }

    const request: ChatRequest = {
      messages: [...this.toPayloadMessages(history), { role: 'user', content: trimmedMessage }],
      stream: false
    };

    return this.postChat(request);
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

      this.logResponse(url, responseBody);
      return responseBody as ChatResponse;
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
        'The companion service took too long to respond. Make sure the local model is running and try again.',
        { cause: error }
      );
    }

    if (error instanceof TypeError) {
      return new ChatServiceError(
        'Could not connect to the local companion service. Make sure the backend is running on the configured address.',
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
}

const getConfiguredBaseUrl = (): string =>
  import.meta.env.VITE_REVERIE_API_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

const normalizeBaseUrl = (baseUrl: string): string => baseUrl.replace(/\/+$/, '');

export const chatService = new ChatService();
