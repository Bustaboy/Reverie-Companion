import type { ImageQualityPreset } from '../api/imageService';

export const MOMENT_CAPTURE_SCHEMA_VERSION = 'moment_capture.v1' as const;
export const SCENE_STATE_SCHEMA_VERSION = 'scene_state.v1' as const;

export type RelationshipPhase =
  | 'strangers'
  | 'newly_met'
  | 'friends'
  | 'close'
  | 'romantic'
  | 'established_partners'
  | string;

export type MomentReviewState = 'pending' | 'approved' | 'rejected' | 'archived' | 'deleted';
export type VisualFeedbackState =
  | 'none'
  | 'liked'
  | 'disliked'
  | 'correction_requested'
  | 'canon_candidate'
  | 'canonized'
  | 'rolled_back';
export type VisualFeedbackActionType =
  | 'like'
  | 'dislike'
  | 'request_correction'
  | 'mark_canon_candidate'
  | 'canonize'
  | 'rollback';
export type VisualCanonStatus = 'proposed' | 'canon_candidate' | 'canonized' | 'rejected' | 'rolled_back';

export interface SceneState {
  schema_version?: typeof SCENE_STATE_SCHEMA_VERSION;
  location?: string | null;
  time_of_day?: string | null;
  mood?: string | null;
  emotional_tone?: string | null;
  character_appearance?: string[];
  expression?: string | null;
  pose?: string | null;
  outfit?: string | null;
  key_objects?: string[];
  nearby_characters?: string[];
  lighting?: string | null;
  camera_framing?: string | null;
  continuity_notes?: string[];
  wrong_appearance?: string[];
}

export interface VisualMemoryArtifact {
  schema_version: 'visual_memory_artifact.v1';
  artifact_id: string;
  memory_id?: string | null;
  journal_id?: string | null;
  character_id: string;
  source_record_id: string;
  created_at: string;
  deleted_at?: string | null;
  rollback_id?: string | null;
}

export interface MomentCaptureRequest {
  schema_version?: typeof MOMENT_CAPTURE_SCHEMA_VERSION;
  character_id: string;
  conversation_id: string;
  session_id?: string | null;
  source_message_id: string;
  source_turn_index: number;
  scene_state: SceneState;
  relationship_phase_snapshot: RelationshipPhase;
  visual_identity_version?: string | null;
  visual_identity_updated_at?: string | null;
  visual_identity_snapshot?: Record<string, unknown>;
  user_instruction?: string | null;
  quality_preset?: ImageQualityPreset;
  relevant_visual_memories?: VisualMemoryArtifact[];
  created_at?: string;
}

export interface VisualFeedbackAction {
  action_id: string;
  action: VisualFeedbackActionType;
  from_state: VisualFeedbackState;
  to_state: VisualFeedbackState;
  reason?: string | null;
  reviewer_id: string;
  created_at: string;
}

export interface VisualChangeEvent {
  schema_version: 'visual_change_event.v1';
  event_id: string;
  character_id: string;
  source_record_id: string;
  changed_trait: string;
  previous_value?: string | null;
  new_value?: string | null;
  reason: string;
  user_reaction?: VisualFeedbackState | null;
  canon_status: VisualCanonStatus;
  rollback_available: boolean;
  rollback_id?: string | null;
  rolled_back_by_event_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MomentCaptureRecord {
  schema_version: typeof MOMENT_CAPTURE_SCHEMA_VERSION;
  record_id: string;
  character_id: string;
  conversation_id: string;
  session_id?: string | null;
  source_message_id: string;
  source_turn_index: number;
  scene_state: SceneState;
  relationship_phase_snapshot: RelationshipPhase;
  visual_identity_version?: string | null;
  visual_identity_updated_at?: string | null;
  prompt_hash: string;
  image_job_id: string;
  output_paths: string[];
  thumbnail_paths: string[];
  feedback_state: VisualFeedbackState;
  review_state: MomentReviewState;
  feedback_actions: VisualFeedbackAction[];
  visual_change_events: VisualChangeEvent[];
  memory_artifacts: VisualMemoryArtifact[];
  created_at: string;
  updated_at: string;
  rollback_id?: string | null;
  legacy_image_record?: Record<string, unknown> | null;
  metadata: Record<string, unknown>;
}
