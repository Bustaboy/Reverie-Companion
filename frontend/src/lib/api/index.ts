export {
  ChatService,
  ChatServiceError,
  chatService,
  type ChatRequest,
  type ChatResponse,
  type ChatStreamEvent,
  type ChatStreamMemoryEvent,
  type ChatServiceOptions,
  type Message,
  type MessagePayload,
  type MessageRole
} from './chatService';

export type { MemoryContext, MemoryContextItem, MemoryContextStatus } from '$lib/types/chat';

export { JournalService, JournalServiceError, journalService, type JournalServiceOptions } from './journalService';
export type { JournalEntriesResponse, JournalEntry, JournalEntryMetadata, ReflectionInsight } from '$lib/types/journal';
