import type { ChatMemoryContext } from '$lib/api';

export type ChatRole = 'user' | 'assistant';

export type ChatMessageStatus = 'complete' | 'streaming' | 'error';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: Date;
  status?: ChatMessageStatus;
  error?: string;
  memoryContext?: ChatMemoryContext;
}
