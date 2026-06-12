export type LoRAExampleStatus = 'pending_review' | 'approved' | 'rejected' | 'deleted';
export type LoRATrainingStatus = 'idle' | 'queued' | 'running' | 'cancelled' | 'completed' | 'failed';
export type LoRAApplicationStatus = 'not_applicable' | 'pending_approval' | 'applied' | 'rejected';

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
  auto_training_enabled?: boolean;
  training_frequency_hours?: number;
  min_training_examples?: number;
  min_new_examples_since_training?: number;
  max_auto_jobs_per_day?: number;
  require_approval_before_applying?: boolean;
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
  trigger_data?: LoRATrainingTriggerData;
  learning_focus?: string[];
  application_status?: LoRAApplicationStatus;
  requires_application_approval?: boolean;
}

export interface LoRATrainingTriggerData {
  trigger_reason?: string;
  approved_example_count?: number;
  new_examples_since_last_training?: number;
  source_journal_count?: number;
  source_memory_count?: number;
  source_example_ids?: string[];
  top_themes?: Array<{ theme: string; count: number }>;
  top_purposes?: Array<{ purpose: string; count: number }>;
}

export interface LoRATrainingStatusSummary {
  status: LoRATrainingStatus;
  current_job_id?: string | null;
  last_trained_at?: string | null;
  next_scheduled_training?: string | null;
  trigger_data?: LoRATrainingTriggerData;
  learning_focus?: string[];
  approval_required_before_applying?: boolean;
  application_status?: LoRAApplicationStatus;
  auto_training_enabled?: boolean;
  auto_training_reason?: string;
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
  training_status?: LoRATrainingStatusSummary;
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
  | 'auto_training_enabled'
  | 'training_frequency_hours'
  | 'min_training_examples'
  | 'min_new_examples_since_training'
  | 'max_auto_jobs_per_day'
  | 'require_approval_before_applying'
>;
