import type { VisualStateMetadata } from '$lib/types/visualNovel';

export type ChatRole = 'user' | 'assistant';

export type TTSMode = 'one_to_one' | 'rpg';

export interface TTSContextMetadata {
  characterId?: string;
  isNarration?: boolean;
  mode?: TTSMode;
  emotionHint?: string;
  intensity?: number;
}

export interface TTSEmotionMetadata {
  scene: string;
  intensity: number;
  tags: string[];
  isHighEmotion?: boolean;
  isIntimate?: boolean;
  cues?: string[];
  visibleTextStripped?: boolean;
  extra?: Record<string, unknown>;
}

export interface MessageTTSMetadata {
  /** Backend-provided speech-safe text, which may include TTS emotion tags and must not replace visible clean text. */
  ttsText?: string;
  /** Resolved voice profile id from VoiceManager/TTSContextRouter, when available. */
  resolvedVoiceId?: string;
  /** Optional display name from future voice profile APIs; frontend falls back to a friendly id label. */
  voiceName?: string;
  ttsContext?: TTSContextMetadata;
  emotion?: TTSEmotionMetadata;
}

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

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: Date;
  status?: ChatMessageStatus;
  error?: string;
  memoryContext?: MemoryContext;
  visualState?: VisualStateMetadata;
  tts?: MessageTTSMetadata;
}
