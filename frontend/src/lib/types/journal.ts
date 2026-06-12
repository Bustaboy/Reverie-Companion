export type JournalEntryStatus = 'active' | 'archived' | 'deleted';
export type TrainingEligibility = 'eligible' | 'needs_review' | 'not_eligible';

export interface ConversationWindow {
  turn_count?: number;
  first_turn_index?: number;
  last_turn_index?: number;
  captured_chars?: number;
}

export interface ReflectionInsight {
  kind?: string;
  summary?: string;
  confidence?: number;
  evidence_count?: number;
  themes?: string[];
  source_turn_indices?: number[];
  memory_worthy?: boolean;
}

export interface StructuredSummary {
  facts?: string[];
  interpretations?: string[];
  unresolved_questions?: string[];
  growth_hypotheses?: string[];
  [key: string]: unknown;
}

export interface MemoryPromotionDecision {
  should_promote?: boolean;
  score?: number;
  threshold?: number;
  reasons?: string[];
  source_turn_indices?: number[];
  provenance?: Record<string, unknown>;
}


export interface GrowthNotification {
  id?: string;
  journal_entry_id?: string;
  created_at?: string;
  message?: string;
  why?: string;
  theme?: string;
  style?: string;
  controls?: string[];
}

export interface JournalEntryMetadata {
  source?: string;
  engine?: string;
  local_first?: boolean;
  lora_ready?: boolean;
  memory_promotion?: MemoryPromotionDecision;
  [key: string]: unknown;
}

export interface JournalEntry {
  entry_id: string;
  created_at: string;
  status?: JournalEntryStatus;
  conversation_window?: ConversationWindow;
  linked_memory_ids?: string[];
  linked_journal_ids?: string[];
  character_summary?: string;
  structured_summary?: StructuredSummary;
  insights?: ReflectionInsight[];
  emotional_valence?: number;
  emotional_intensity?: number;
  themes?: string[];
  confidence?: number;
  evidence_count?: number;
  privacy_tags?: string[];
  sensitivity_tags?: string[];
  training_eligibility?: TrainingEligibility;
  rollback_id?: string;
  growth_notification?: GrowthNotification | null;
  metadata?: JournalEntryMetadata;
}

export interface JournalEntriesResponse {
  entries: JournalEntry[];
  count: number;
}
