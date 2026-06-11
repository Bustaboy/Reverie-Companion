export type ChatRole = 'user' | 'assistant';

export type ChatMessageStatus = 'complete' | 'streaming' | 'error';

export interface MemoryContextItem {
  id?: string;
  label: string;
}

export interface MemoryContext {
  /** Whether retrieved long-term memory meaningfully shaped this reply. */
  used: boolean;
  /** Calm user-facing state; avoids exposing backend/retrieval internals. */
  status?: 'used' | 'empty' | 'disabled' | 'unavailable';
  /** Tiny, warm summary suitable for subtle UI hints. */
  summary?: string;
  /** Optional compact labels for future inspectable memory peeks. */
  items?: MemoryContextItem[];
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: Date;
  status?: ChatMessageStatus;
  error?: string;
  memoryContext?: MemoryContext;
}
