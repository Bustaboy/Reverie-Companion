export type ChatRole = 'user' | 'assistant' | 'system';

export type ChatMessageStatus = 'complete' | 'streaming' | 'error';

export type MemoryContextStatus = 'used' | 'empty' | 'disabled' | 'unavailable' | 'unknown';

export type GrowthNotificationStyle = 'whisper' | 'toast' | 'inline';

export interface GrowthNotification {
  id: string;
  journalEntryId?: string;
  text: string;
  theme?: string;
  style: GrowthNotificationStyle;
  createdAt: Date;
  controls: string[];
}

export interface MemoryContextItem {
  id?: string;
  label: string;
}

export interface MemoryContext {
  /** Whether retrieved long-term memory meaningfully shaped this reply. */
  used: boolean;
  /** Calm user-facing state; avoids exposing backend/retrieval internals. */
  status?: MemoryContextStatus;
  /** Number of memories or snippets, when the backend exposes it. */
  itemCount?: number;
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
  growthNotification?: GrowthNotification;
}
