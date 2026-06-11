import { get, writable } from 'svelte/store';
import { ChatServiceError, chatService, type Message } from '$lib/api';
import { createChatMessage, createInitialMessages } from '$lib/chat/messages';
import type { ChatMessage, MemoryContext } from '$lib/types/chat';

export type ChatGenerationState = 'idle' | 'thinking' | 'streaming';

export interface ChatState {
  messages: ChatMessage[];
  generationState: ChatGenerationState;
  error: string | null;
}

const INITIAL_STATE: ChatState = {
  messages: createInitialMessages(),
  generationState: 'idle',
  error: null
};

const createAssistantPlaceholder = (): ChatMessage => ({
  ...createChatMessage('assistant', ''),
  status: 'streaming'
});

const OFFLINE_ASSISTANT_FALLBACK =
  "I'm still here, but I couldn't reach the local companion service. Start the backend when you're ready and we can continue.";
const GENERIC_RESPONSE_ERROR = 'Something went wrong while Reverie was responding. Please try again.';

const toServiceHistory = (messages: ChatMessage[]): Message[] =>
  messages
    .filter((message) => message.role === 'user' || message.role === 'assistant')
    .filter((message) => message.status !== 'error')
    .filter((message) => message.content.trim().length > 0)
    .map((message) => ({
      role: message.role,
      content: message.content,
      id: message.id,
      createdAt: message.createdAt
    }));

const appendToMessage = (messages: ChatMessage[], messageId: string, content: string): ChatMessage[] =>
  messages.map((message) =>
    message.id === messageId
      ? {
          ...message,
          content: `${message.content}${content}`,
          status: 'streaming'
        }
      : message
  );

const updateMessage = (messages: ChatMessage[], messageId: string, patch: Partial<ChatMessage>): ChatMessage[] =>
  messages.map((message) => (message.id === messageId ? { ...message, ...patch } : message));

const applyMemoryContext = (messages: ChatMessage[], messageId: string, memoryContext?: MemoryContext): ChatMessage[] => {
  if (!memoryContext || !memoryContext.used) {
    return messages;
  }

  return updateMessage(messages, messageId, { memoryContext });
};

const getAssistantFailureContent = (message: ChatMessage | undefined): string =>
  message?.content.trim() || OFFLINE_ASSISTANT_FALLBACK;

const toFriendlyErrorMessage = (error: unknown): string => {
  if (error instanceof ChatServiceError) {
    return error.message;
  }

  return GENERIC_RESPONSE_ERROR;
};

function createChatStore() {
  const store = writable<ChatState>(INITIAL_STATE);
  let activeController: AbortController | null = null;

  const hasActiveSend = () => activeController !== null;

  const finishAssistantMessage = (assistantMessageId: string, memoryContext?: MemoryContext) => {
    store.update((state) => ({
      ...state,
      generationState: 'idle',
      messages: applyMemoryContext(
        updateMessage(state.messages, assistantMessageId, { status: 'complete' }),
        assistantMessageId,
        memoryContext
      )
    }));
  };

  const failAssistantMessage = (assistantMessageId: string, errorMessage: string) => {
    store.update((state) => {
      const assistantMessage = state.messages.find((message) => message.id === assistantMessageId);
      const fallbackContent = getAssistantFailureContent(assistantMessage);

      return {
        ...state,
        generationState: 'idle',
        error: errorMessage,
        messages: updateMessage(state.messages, assistantMessageId, {
          content: fallbackContent,
          status: 'error',
          error: errorMessage
        })
      };
    });
  };

  return {
    subscribe: store.subscribe,
    async sendMessage(content: string) {
      const trimmedContent = content.trim();
      const currentState = get(store);

      if (!trimmedContent || currentState.generationState !== 'idle' || hasActiveSend()) {
        return;
      }

      // The empty assistant message is intentionally created before the request:
      // it anchors the thinking/streaming UI and gives incoming chunks a stable
      // id to update without remounting the whole transcript.
      // Capture history before appending the optimistic messages so the backend
      // receives exactly the conversation the user saw before pressing Send.
      const history = toServiceHistory(currentState.messages);
      const userMessage = createChatMessage('user', trimmedContent);
      const assistantMessage = createAssistantPlaceholder();
      const controller = new AbortController();
      activeController = controller;

      store.update((state) => ({
        ...state,
        error: null,
        generationState: 'thinking',
        messages: [...state.messages, userMessage, assistantMessage]
      }));

      try {
        for await (const event of chatService.sendMessageStream(trimmedContent, history, { signal: controller.signal })) {
          if (event.event === 'message') {
            if (!event.content && !event.memoryContext?.used) continue;

            // Append token chunks in-place by message id so Svelte only needs to
            // refresh the active assistant bubble during a stream. Memory metadata
            // may arrive beside a chunk or as its own event, so keep both paths light.
            store.update((state) => ({
              ...state,
              generationState: event.content ? 'streaming' : state.generationState,
              messages: applyMemoryContext(
                event.content ? appendToMessage(state.messages, assistantMessage.id, event.content) : state.messages,
                assistantMessage.id,
                event.memoryContext
              )
            }));
            continue;
          }

          if (event.event === 'memory') {
            store.update((state) => ({
              ...state,
              messages: applyMemoryContext(state.messages, assistantMessage.id, event.memoryContext)
            }));
            continue;
          }

          if (event.event === 'error') {
            throw new ChatServiceError(event.error, { requestId: event.requestId, details: event.details });
          }

          finishAssistantMessage(assistantMessage.id, event.memoryContext);
        }
      } catch (error) {
        failAssistantMessage(assistantMessage.id, toFriendlyErrorMessage(error));
      } finally {
        if (activeController === controller) {
          activeController = null;
        }
      }
    },
    stopStreaming() {
      activeController?.abort();
    },
    clearError() {
      store.update((state) => ({ ...state, error: null }));
    }
  };
}

export const chatStore = createChatStore();
