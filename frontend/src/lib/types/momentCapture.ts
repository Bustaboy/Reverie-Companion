import type { VisualBackground, VisualExpression, VisualPose } from './visualNovel';

export type MomentCaptureSchemaVersion = 'moment_capture.v1';
export type SceneStateSchemaVersion = 'scene_state.v1';
export type VisualChangeEventSchemaVersion = 'visual_change_event.v1';

export type FeedbackState = 'pending' | 'looks_right' | 'wrong_appearance' | 'favorite' | 'rejected' | 'deleted';
export type ReviewState = 'unreviewed' | 'accepted' | 'needs_changes' | 'canon_requested' | 'canonized' | 'rolled_back' | 'deleted';
export type VisualFeedbackAction = 'looks_right' | 'wrong_appearance' | 'make_canon' | 'use_outfit_again' | 'scene_only' | 'never_use_trait' | 'favorite' | 'delete' | 'rollback';
export type VisualChangeCanonStatus = 'proposed' | 'approved' | 'canonized' | 'rolled_back' | 'rejected';
export type ImageQualityPreset = 'preview_8gb' | 'balanced_8gb' | 'high_8gb';

export interface SceneState {
  schema_version: SceneStateSchemaVersion;
  location?: string | null;
  time_of_day?: string | null;
  mood?: string | null;
  emotional_tone?: string | null;
  character_appearance: string[];
  pose?: VisualPose | string | null;
  outfit?: string | null;
  key_objects: string[];
  background_details: string[];
  continuity_notes: string[];
  wrong_appearance: string[];
  metadata: Record<string, unknown>;
  /** Optional visual-novel hints for future capture previews; not required by backend. */
  visual_hint?: { expression?: VisualExpression; background?: VisualBackground };
}

export interface VisualMemoryArtifact {
  schema_version: 'visual_memory_artifact.v1';
  artifact_id: string;
  artifact_type: string;
  path?: string | null;
  memory_id?: string | null;
  training_candidate: boolean;
  created_at: string;
  metadata: Record<string, unknown>;
}

export interface MomentCaptureRequest {
  schema_version: MomentCaptureSchemaVersion;
  character_id: string;
  conversation_id: string;
  session_id: string;
  source_message_id: string;
  source_turn_index: number;
  scene_state: SceneState;
  relationship_phase_snapshot: string;
  visual_identity_snapshot: Record<string, unknown>;
  visual_identity_version: string;
  visual_identity_updated_at: string;
  prompt_hash: string;
  quality_preset: ImageQualityPreset;
  relevant_visual_memories: VisualMemoryArtifact[];
  created_at: string;
  metadata: Record<string, unknown>;
}

export interface MomentCaptureRecord extends Omit<MomentCaptureRequest, 'visual_identity_snapshot' | 'relevant_visual_memories' | 'quality_preset'> {
  capture_id: string;
  image_job_id: string;
  output_paths: string[];
  feedback_state: FeedbackState;
  review_state: ReviewState;
  review_transition_from?: ReviewState | null;
  feedback_actions: VisualFeedbackAction[];
  visual_memory_artifacts: VisualMemoryArtifact[];
  updated_at: string;
  rollback_id?: string | null;
  legacy_image_history: Record<string, unknown>;
}

export interface VisualChangeEvent {
  schema_version: VisualChangeEventSchemaVersion;
  event_id: string;
  character_id: string;
  capture_id?: string | null;
  changed_trait: string;
  previous_value?: string | null;
  new_value: string;
  reason: string;
  feedback_action?: VisualFeedbackAction | null;
  canon_status: VisualChangeCanonStatus;
  rollback_id?: string | null;
  rollback_available: boolean;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}
