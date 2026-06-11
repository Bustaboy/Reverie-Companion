import type { ChatMessage, ChatMessageStatus, ChatRole } from '$lib/types/chat';

interface CreateChatMessageOptions {
  status?: ChatMessageStatus;
  errorMessage?: string;
  includeInHistory?: boolean;
}

export const createChatMessage = (
  role: ChatRole,
  content: string,
  options: CreateChatMessageOptions = {}
): ChatMessage => ({
  id: crypto.randomUUID(),
  role,
  content,
  createdAt: new Date(),
  status: options.status ?? 'complete',
  errorMessage: options.errorMessage,
  includeInHistory: options.includeInHistory ?? true
});

export const createInitialMessages = (): ChatMessage[] => [
  {
    id: 'welcome-1',
    role: 'assistant',
    content:
      "Good evening. I'm here with you. Tell me what kind of scene, mood, or memory you want to explore first.",
    createdAt: new Date(),
    status: 'complete',
    includeInHistory: false
  }
];
