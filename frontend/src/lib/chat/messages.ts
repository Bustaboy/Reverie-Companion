import type { ChatMessage, ChatMessageStatus, ChatRole } from '$lib/types/chat';

export const createChatMessage = (
  role: ChatRole,
  content: string,
  status: ChatMessageStatus = 'complete'
): ChatMessage => ({
  id: crypto.randomUUID(),
  role,
  content,
  status,
  createdAt: new Date()
});

export const createInitialMessages = (): ChatMessage[] => [
  {
    id: 'welcome-1',
    role: 'assistant',
    content:
      "Good evening. I'm here with you. Tell me what kind of scene, mood, or memory you want to explore first.",
    status: 'complete',
    createdAt: new Date()
  }
];
