export type ChatRole = 'user' | 'assistant';
export type ChatMessageStatus = 'thinking' | 'streaming' | 'complete' | 'error';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: Date;
  status?: ChatMessageStatus;
  errorMessage?: string;
  /** UI-only welcome/system copy should not be replayed into the backend prompt. */
  includeInHistory?: boolean;
}
