import { derived, get, writable } from 'svelte/store';
import { chatService, ChatServiceError, type ChatStreamEvent, type Message } from '$lib/api';
import { createChatMessage, createInitialMessages } from '$lib/chat/messages';
import type { ChatMessage } from '$lib/types/chat';

export type ChatConnectionState = 'idle' | 'thinking' | 'streaming' | 'error';

interface ChatState {
  messages: ChatMessage[];
  connectionState: ChatConnectionState;
  activeAssistantMessageId: string | null;
  errorMessage: string | null;
}

const createInitialState = (): ChatState => ({
  messages: createInitialMessages(),
  connectionState: 'idle',
  activeAssistantMessageId: null,
  errorMessage: null
});

const createFriendlyErrorMessage = (error: unknown): string => {
  if (error instanceof ChatServiceError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Reverie could not reach the local companion service. Please make sure the backend is running and try again.';
};

const createStreamErrorMessage = (event: Extract<ChatStreamEvent, { event: 'error' }>): string => {
  const suffix = event.requestId ? ` Request ID: ${event.requestId}.` : '';
  return `${event.error || 'The companion stream stopped unexpectedly.'}${suffix}`;
};

const toServiceHistory = (messages: ChatMessage[]): Message[] =>
  messages
    .filter((message) => message.includeInHistory !== false && message.status !== 'error' && message.content.trim().length > 0)
    .map((message) => ({
      id: message.id,
      role: message.role,
      content: message.content,
      createdAt: message.createdAt
    }));

const updateMessage = (
  messages: ChatMessage[],
  messageId: string,
  updater: (message: ChatMessage) => ChatMessage
): ChatMessage[] => messages.map((message) => (message.id === messageId ? updater(message) : message));

const createChatStore = () => {
  const store = writable<ChatState>(createInitialState());
  let streamAbortController: AbortController | null = null;

  const finishAssistantMessage = (assistantMessageId: string) => {
    store.update((state) => ({
      ...state,
      connectionState: 'idle',
      activeAssistantMessageId: null,
      messages: updateMessage(state.messages, assistantMessageId, (message) => ({
        ...message,
        status: message.status === 'error' ? 'error' : 'complete'
      }))
    }));
  };

  const markAssistantError = (assistantMessageId: string, errorMessage: string) => {
    store.update((state) => ({
      ...state,
      connectionState: 'error',
      activeAssistantMessageId: null,
      errorMessage,
      messages: updateMessage(state.messages, assistantMessageId, (message) => ({
        ...message,
        content: message.content || 'I had trouble answering just now.',
        errorMessage,
        status: 'error'
      }))
    }));
  };

  const sendMessageStream = async (content: string) => {
    const message = content.trim();

    if (!message || get(store).connectionState === 'thinking' || get(store).connectionState === 'streaming') {
      return;
    }

    const history = toServiceHistory(get(store).messages);
    const userMessage = createChatMessage('user', message);
    const assistantMessage = createChatMessage('assistant', '', { status: 'thinking' });
    let receivedToken = false;

    streamAbortController?.abort();
    streamAbortController = new AbortController();

    store.update((state) => ({
      ...state,
      messages: [...state.messages, userMessage, assistantMessage],
      connectionState: 'thinking',
      activeAssistantMessageId: assistantMessage.id,
      errorMessage: null
    }));

    try {
      for await (const event of chatService.sendMessageStream(message, history, { signal: streamAbortController.signal })) {
        if (event.event === 'message') {
          if (!event.content) {
            continue;
          }

          receivedToken = true;
          store.update((state) => ({
            ...state,
            connectionState: 'streaming',
            messages: updateMessage(state.messages, assistantMessage.id, (currentMessage) => ({
              ...currentMessage,
              content: `${currentMessage.content}${event.content}`,
              status: 'streaming'
            }))
          }));
          continue;
        }

        if (event.event === 'error') {
          markAssistantError(assistantMessage.id, createStreamErrorMessage(event));
          return;
        }

        finishAssistantMessage(assistantMessage.id);
        return;
      }

      if (!receivedToken) {
        markAssistantError(assistantMessage.id, 'Reverie did not receive a response from the local companion service.');
      } else {
        finishAssistantMessage(assistantMessage.id);
      }
    } catch (error) {
      markAssistantError(assistantMessage.id, createFriendlyErrorMessage(error));
    } finally {
      streamAbortController = null;
    }
  };

  const sendMessage = async (content: string) => {
    const message = content.trim();

    if (!message || get(store).connectionState === 'thinking' || get(store).connectionState === 'streaming') {
      return;
    }

    const history = toServiceHistory(get(store).messages);
    const userMessage = createChatMessage('user', message);
    const assistantMessage = createChatMessage('assistant', '', { status: 'thinking' });

    store.update((state) => ({
      ...state,
      messages: [...state.messages, userMessage, assistantMessage],
      connectionState: 'thinking',
      activeAssistantMessageId: assistantMessage.id,
      errorMessage: null
    }));

    try {
      const response = await chatService.sendMessage(message, history);
      store.update((state) => ({
        ...state,
        connectionState: 'idle',
        activeAssistantMessageId: null,
        messages: updateMessage(state.messages, assistantMessage.id, (currentMessage) => ({
          ...currentMessage,
          content: response.message.content,
          status: 'complete'
        }))
      }));
    } catch (error) {
      markAssistantError(assistantMessage.id, createFriendlyErrorMessage(error));
    }
  };

  const stopStreaming = () => {
    streamAbortController?.abort();
    streamAbortController = null;

    const state = get(store);
    if (!state.activeAssistantMessageId) {
      return;
    }

    store.update((currentState) => ({
      ...currentState,
      connectionState: 'idle',
      activeAssistantMessageId: null,
      messages: updateMessage(currentState.messages, state.activeAssistantMessageId!, (message) => ({
        ...message,
        status: message.content ? 'complete' : 'error',
        errorMessage: message.content ? undefined : 'Response stopped before Reverie could answer.'
      }))
    }));
  };

  return {
    subscribe: store.subscribe,
    sendMessageStream,
    sendMessage,
    stopStreaming,
    reset: () => store.set(createInitialState())
  };
};

export const chatStore = createChatStore();
export const chatMessages = derived(chatStore, ($chat) => $chat.messages);
export const chatConnectionState = derived(chatStore, ($chat) => $chat.connectionState);
export const chatErrorMessage = derived(chatStore, ($chat) => $chat.errorMessage);
