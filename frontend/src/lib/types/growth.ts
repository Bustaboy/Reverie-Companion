export type LoRAExampleStatus = 'pending_review' | 'approved' | 'rejected' | 'deleted';
export type LoRATrainingStatus = 'idle' | 'queued' | 'running' | 'cancelled' | 'completed' | 'failed';

export interface PersonalLoRASettings {
  collection_opt_in?: boolean;
  training_opt_in?: boolean;
  rank?: number;
  max_steps?: number;
  learning_rate?: number;
  batch_size?: number;
  gradient_accumulation_steps?: number;
  max_sequence_length?: number;
  target_vram_gb?: number;
  pause_during_chat?: boolean;
  require_review_before_training?: boolean;
  active_adapter_id?: string | null;
  rollback_adapter_id?: string | null;
  updated_at?: string;
}

export interface LoRATrainingExample {
  item_id: string;
  source_journal_id?: string;
  source_memory_ids?: string[];
  source_turn_indices?: number[];
  purpose?: string;
  text?: string;
  themes?: string[];
  confidence?: number;
  evidence_count?: number;
  approved_by_user?: boolean;
  status?: LoRAExampleStatus;
  consent_flags?: string[];
  privacy_tags?: string[];
  sensitivity_tags?: string[];
  created_at?: string;
  updated_at?: string;
  rollback_id?: string;
}

export interface LoRATrainingJob {
  job_id: string;
  status: LoRATrainingStatus;
  adapter_id?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  stopped_at?: string | null;
  example_count?: number;
  rank?: number;
  settings?: Record<string, unknown>;
  progress?: number;
  message?: string;
  error?: string | null;
}

export interface PersonalLoRACounts {
  pending_review: number;
  approved: number;
  rejected: number;
}

export interface PersonalLoRAStatusResponse {
  settings: PersonalLoRASettings;
  current_job: LoRATrainingJob | null;
  examples: LoRATrainingExample[];
  counts: PersonalLoRACounts;
}

export type PersonalLoRASettingsUpdate = Pick<
  PersonalLoRASettings,
  'collection_opt_in' | 'training_opt_in' | 'pause_during_chat' | 'require_review_before_training'
>;
