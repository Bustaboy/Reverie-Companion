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

export { JournalService, JournalServiceError, journalService, type GetJournalEntriesOptions, type JournalServiceOptions } from './journalService';
export type { JournalEntry, JournalInsight, JournalEntryMetadata, JournalMemoryPromotion } from '$lib/types/journal';
