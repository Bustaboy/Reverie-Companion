import { describe, expect, it } from 'vitest';
import { ImageService } from './imageService';
import type { MomentCaptureRequest } from '$lib/types/momentCapture';

const request: MomentCaptureRequest = {
  schema_version: 'moment_capture.v1',
  character_id: 'char-1',
  conversation_id: 'default',
  session_id: 'session-1',
  source_message_id: 'message-1',
  source_turn_index: 2,
  scene_state: {
    schema_version: 'scene_state.v1',
    location: 'cafe',
    mood: 'warm',
    emotional_tone: 'happy',
    character_appearance: ['silver hair'],
    pose: 'speaking',
    outfit: null,
    key_objects: ['coffee cup'],
    background_details: ['window booth'],
    continuity_notes: ['close friends'],
    wrong_appearance: ['blue eyes'],
    metadata: { source: 'chat' }
  },
  relationship_phase_snapshot: 'trusted',
  visual_identity_snapshot: {
    schema_version: 'visual_identity_profile.v1',
    identity_anchors: ['silver hair'],
    evolving_traits: [],
    scene_mutable_traits: [],
    rejected_traits: ['blue eyes'],
    current_appearance: 'silver hair and amber eyes',
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
  prompt_hash: 'fe12345678',
  quality_preset: 'preview_8gb',
  relevant_visual_memories: [],
  created_at: '2026-06-13T00:00:00Z',
  metadata: { capture_source: 'chat' }
};

describe('ImageService Moment Capture integration', () => {
  it('posts Moment Capture requests to the durable capture endpoint', async () => {
    let seenUrl = '';
    let payload: unknown;
    const fetcher = (async (url: RequestInfo | URL, init?: RequestInit) => {
      seenUrl = String(url);
      payload = JSON.parse(String(init?.body));
      return new Response(
        JSON.stringify({
          request_id: 'request-1',
          record: { ...request, capture_id: 'capture-1', image_job_id: 'job-1', output_paths: ['queued://image-job/job-1'], feedback_state: 'pending', review_state: 'unreviewed', feedback_actions: [], visual_memory_artifacts: [], updated_at: request.created_at, legacy_image_history: {} },
          job: { job_id: 'job-1', status: 'queued', prompt: 'prompt', negative_prompt: '', requested_preset: 'preview_8gb', active_preset: 'preview_8gb', created_at: request.created_at, updated_at: request.created_at, progress: 0, phase: 'queued', message: 'queued', output_paths: [], moment_capture_id: 'capture-1' }
        }),
        { status: 202, headers: { 'Content-Type': 'application/json' } }
      );
    }) as typeof fetch;

    const service = new ImageService({ baseUrl: 'http://test.local', fetcher });
    const response = await service.createMomentCapture(request);

    expect(seenUrl).toBe('http://test.local/api/moment-capture');
    expect(payload).toMatchObject({ character_id: 'char-1', source_message_id: 'message-1', scene_state: { location: 'cafe' } });
    expect(response.record.capture_id).toBe('capture-1');
    expect(response.job.moment_capture_id).toBe('capture-1');
  });
});
