export type JournalEntryStatus = 'active' | 'archived' | 'deleted';
export type TrainingEligibility = 'eligible' | 'needs_review' | 'not_eligible';

export interface JournalConversationWindow {
  turn_count?: number;
  first_turn_index?: number;
  last_turn_index?: number;
  captured_chars?: number;
}

export interface JournalInsight {
  kind?: string;
  summary: string;
  confidence?: number;
  evidence_count?: number;
  themes?: string[];
  source_turn_indices?: number[];
  memory_worthy?: boolean;
}

export interface JournalStructuredSummary {
  facts?: string[];
  interpretations?: string[];
  unresolved_questions?: string[];
  growth_hypotheses?: string[];
}

export interface JournalMemoryPromotion {
  should_promote?: boolean;
  promoted?: boolean;
  score?: number;
  threshold?: number;
  reasons?: string[];
  promoted_memory_id?: string;
}

export interface JournalEntryMetadata {
  source?: string;
  engine?: string;
  local_first?: boolean;
  memory_promotion?: JournalMemoryPromotion;
  [key: string]: unknown;
}

export interface JournalEntry {
  entry_id: string;
  created_at: string;
  status?: JournalEntryStatus;
  conversation_window?: JournalConversationWindow;
  linked_memory_ids?: string[];
  linked_journal_ids?: string[];
  character_summary?: string;
  structured_summary?: JournalStructuredSummary;
  insights?: JournalInsight[];
  emotional_valence?: number;
  emotional_intensity?: number;
  themes?: string[];
  confidence?: number;
  evidence_count?: number;
  privacy_tags?: string[];
  sensitivity_tags?: string[];
  training_eligibility?: TrainingEligibility;
  rollback_id?: string;
  metadata?: JournalEntryMetadata;
}
