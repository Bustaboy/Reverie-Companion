import type { TtsContext } from '$lib/api/ttsService';
import type { VisualStateMetadata } from '$lib/types/visualNovel';

export type ChatRole = 'user' | 'assistant';

export type ChatMessageStatus = 'complete' | 'streaming' | 'error';

export type MemoryContextStatus = 'used' | 'empty' | 'disabled' | 'unavailable' | 'unknown';

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

export interface GrowthNotification {
  id: string;
  journalEntryId: string;
  createdAt: Date;
  message: string;
  why?: string;
  theme?: string;
  style?: 'whisper' | string;
  controls?: string[];
}

export interface ChatTtsMetadata {
  text: string;
  ttsText?: string;
  voiceId?: string;
  voiceName?: string;
  context?: TtsContext;
  emotion?: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: Date;
  status?: ChatMessageStatus;
  error?: string;
  memoryContext?: MemoryContext;
  visualState?: VisualStateMetadata;
  tts?: ChatTtsMetadata;
}
