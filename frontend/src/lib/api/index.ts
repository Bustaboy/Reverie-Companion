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

export { GrowthService, GrowthServiceError, growthService, type GrowthServiceOptions } from './growthService';
export type { LoRATrainingExample, LoRATrainingJob, PersonalLoRACounts, PersonalLoRASettings, PersonalLoRAStatusResponse } from '$lib/types/growth';

export { TtsService, TtsServiceError, ttsService, type TtsAudioFormat, type TtsContext, type TtsGenerateRequest, type TtsGenerateResponse, type TtsQualityPreference, type TtsServiceOptions } from './ttsService';
