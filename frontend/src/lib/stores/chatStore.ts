import { get, writable } from 'svelte/store';
import { ChatServiceError, chatService, type Message } from '$lib/api';
import { createChatMessage, createInitialMessages } from '$lib/chat/messages';
import type { ChatMessage } from '$lib/types/chat';

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

const LOCAL_BACKEND_HELP =
  "I'm still here, but I couldn't reach the local companion service. Start the backend when you're ready and we can continue.";

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

const toFriendlyErrorMessage = (error: unknown): string => {
  if (error instanceof ChatServiceError) {
    return error.message;
  }

  return 'Something went wrong while Reverie was responding. Please try again.';
};

function createChatStore() {
  const store = writable<ChatState>(INITIAL_STATE);
  let activeController: AbortController | null = null;

  const finishAssistantMessage = (assistantMessageId: string) => {
    store.update((state) => ({
      ...state,
      generationState: 'idle',
      messages: updateMessage(state.messages, assistantMessageId, { status: 'complete' })
    }));
  };

  const failAssistantMessage = (assistantMessageId: string, errorMessage: string) => {
    store.update((state) => {
      const assistantMessage = state.messages.find((message) => message.id === assistantMessageId);
      const fallbackContent = assistantMessage?.content.trim() || LOCAL_BACKEND_HELP;

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

      if (!trimmedContent || currentState.generationState !== 'idle') {
        return;
      }

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
            if (!event.content) continue;

            // Append token chunks in-place by message id so Svelte only needs to
            // refresh the active assistant bubble during a stream.
            store.update((state) => ({
              ...state,
              generationState: 'streaming',
              messages: appendToMessage(state.messages, assistantMessage.id, event.content)
            }));
            continue;
          }

          if (event.event === 'error') {
            throw new ChatServiceError(event.error, { requestId: event.requestId, details: event.details });
          }

          finishAssistantMessage(assistantMessage.id);
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
