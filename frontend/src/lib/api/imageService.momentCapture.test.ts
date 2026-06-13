import { describe, expect, it } from 'vitest';
import { ImageService } from './imageService';
import type { MomentCaptureRequest } from '$lib/types/momentCapture';

const request: MomentCaptureRequest = {
  schema_version: 'moment_capture.v1',
  character_id: 'char-1',
  conversation_id: 'conversation-1',
  session_id: 'session-1',
  source_message_id: 'message-1',
  source_turn_index: 2,
  scene_state: {
    schema_version: 'scene_state.v1',
    mood: 'warm',
    emotional_tone: 'happy',
    character_appearance: ['Reverie'],
    pose: 'speaking',
    outfit: null,
    key_objects: ['journal'],
    background_details: ['cafe'],
    continuity_notes: ['assistant: hello'],
    wrong_appearance: [],
    metadata: { source: 'chat' }
  },
  relationship_phase_snapshot: 'trusted_companion',
  visual_identity_snapshot: {
    schema_version: 'visual_identity_profile.v1',
    identity_anchors: ['Reverie'],
    evolving_traits: [],
    scene_mutable_traits: [],
    rejected_traits: [],
    adult_only_policy: {
      schema_version: 'adult_only_visual_policy.v1',
      clearly_adult: true,
      adult_age_range: 'mid_20s_adult',
      adult_baseline_note: 'clearly adult presentation; no underage or deliberately childlike sexual presentation',
      disallow_underage_or_childlike_sexualization: true
    },
    updated_at: '2026-06-13T00:00:00Z'
  },
  visual_identity_version: 'visual_identity_profile.v1',
  visual_identity_updated_at: '2026-06-13T00:00:00Z',
  prompt_hash: 'ui12345678',
  quality_preset: 'preview_8gb',
  relevant_visual_memories: [],
  created_at: '2026-06-13T00:00:00Z',
  metadata: { ui_source: 'chat' }
};

describe('ImageService Moment Capture integration', () => {
  it('posts full MomentCaptureRequest metadata to the Moment Capture endpoint', async () => {
    let seenUrl = '';
    let payload: MomentCaptureRequest | undefined;
    const fetcher = (async (url: RequestInfo | URL, init?: RequestInit) => {
      seenUrl = String(url);
      payload = JSON.parse(String(init?.body));
      return new Response(
        JSON.stringify({
          request_id: 'request-1',
          record: { capture_id: 'capture-1', ...request, image_job_id: 'job-1', output_paths: [], feedback_state: 'pending', review_state: 'unreviewed', feedback_actions: [], visual_memory_artifacts: [], updated_at: request.created_at, legacy_image_history: {} },
          job: { job_id: 'job-1', status: 'queued', prompt: 'compiled prompt', negative_prompt: '', requested_preset: 'preview_8gb', active_preset: 'preview_8gb', created_at: request.created_at, updated_at: request.created_at, progress: 0, phase: 'queued', message: 'queued', output_paths: [], character_id: 'char-1', moment_capture_id: 'capture-1' },
          prompt_bundle: {}
        }),
        { status: 202, headers: { 'Content-Type': 'application/json' } }
      );
    }) as typeof fetch;

    const service = new ImageService({ baseUrl: 'http://test.local', fetcher });
    const response = await service.createMomentCapture(request);

    expect(seenUrl).toBe('http://test.local/api/moment-capture');
    expect(payload).toMatchObject({
      character_id: 'char-1',
      source_message_id: 'message-1',
      source_turn_index: 2,
      scene_state: { metadata: { source: 'chat' }, key_objects: ['journal'] },
      relationship_phase_snapshot: 'trusted_companion',
      metadata: { ui_source: 'chat' }
    });
    expect(response.record.capture_id).toBe('capture-1');
    expect(response.job.moment_capture_id).toBe('capture-1');
  });
});
