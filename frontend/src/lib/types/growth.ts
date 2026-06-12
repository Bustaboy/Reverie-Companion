export type LoRAExampleStatus = 'pending_review' | 'approved' | 'rejected' | 'deleted';
export type LoRATrainingStatus = 'idle' | 'queued' | 'running' | 'cancelled' | 'completed' | 'failed';
export type LoRAApplyStatus = 'not_ready' | 'pending_apply' | 'applied' | 'rejected';

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
  require_approval_before_applying?: boolean;
  auto_training_enabled?: boolean;
  training_frequency_hours?: number;
  min_training_examples?: number;
  min_new_examples_for_auto_training?: number;
  min_memory_links_for_auto_training?: number;
  max_auto_jobs_per_day?: number;
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
  trigger_reason?: string | null;
  trigger_summary?: string | null;
  trigger_example_ids?: string[];
  learning_summary?: string[];
  apply_status?: LoRAApplyStatus;
}

export interface LoRATrainingStatusSummary {
  status: LoRATrainingStatus;
  message?: string;
  last_trained_at?: string | null;
  next_scheduled_at?: string | null;
  triggered_by?: string | null;
  trigger_reason?: string | null;
  learning_feedback?: string[];
  auto_training_enabled?: boolean;
  require_approval_before_applying?: boolean;
  min_training_examples?: number;
  training_frequency_hours?: number;
  approved_example_count?: number;
  pending_review_count?: number;
  pending_adapter_update?: LoRATrainingJob | null;
}

export interface PersonalLoRACounts {
  pending_review: number;
  approved: number;
  rejected: number;
}

export interface PersonalLoRAStatusResponse {
  settings: PersonalLoRASettings;
  current_job: LoRATrainingJob | null;
  training_status: LoRATrainingStatusSummary;
  examples: LoRATrainingExample[];
  counts: PersonalLoRACounts;
}

export interface PersonalLoRASettingsResponse {
  settings: PersonalLoRASettings;
}

export interface PersonalLoRAExampleResponse {
  example: LoRATrainingExample;
}

export interface PersonalLoRAJobResponse {
  job: LoRATrainingJob;
}

export type PersonalLoRASettingsUpdate = Pick<
  PersonalLoRASettings,
  | 'collection_opt_in'
  | 'training_opt_in'
  | 'batch_size'
  | 'pause_during_chat'
  | 'require_review_before_training'
  | 'require_approval_before_applying'
  | 'auto_training_enabled'
  | 'training_frequency_hours'
  | 'min_training_examples'
  | 'min_new_examples_for_auto_training'
  | 'min_memory_links_for_auto_training'
  | 'max_auto_jobs_per_day'
>;
