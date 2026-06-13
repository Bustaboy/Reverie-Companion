import { describe, expect, it } from 'vitest';
import { buildMomentCaptureRequestFromMessage, buildMomentCaptureRequestFromScene } from './imageGenerationStore.svelte';
import type { CharacterBlueprint } from '$lib/api/characterService';
import type { ChatMessage } from '$lib/types/chat';
import type { ResolvedVisualNovelScene } from '$lib/types/visualNovel';

const character: CharacterBlueprint = {
  schema_version: 1,
  character_id: 'char-1',
  identity: { display_name: 'Reverie', pronouns: 'she/her', adult_age_range: 'mid_20s_adult' },
  relationship: { relationship_dynamic: 'trusted companion', current_relationship_phase: 'trusted' },
  visual_identity: {
    schema_version: 'visual_identity_profile.v1',
    identity_anchors: ['amber eyes', 'silver hair'],
    rejected_traits: ['blue eyes'],
    current_appearance: 'silver hair, amber eyes, warm smile',
    updated_at: '2026-06-13T00:00:00Z'
  },
  updated_at: '2026-06-13T00:00:00Z'
};

const messages: ChatMessage[] = [
  { id: 'user-1', role: 'user', content: 'Meet me at the cafe.', createdAt: new Date('2026-06-13T00:00:00Z'), status: 'complete' },
  {
    id: 'assistant-1',
    role: 'assistant',
    content: 'I lean closer by the cafe window and smile.',
    createdAt: new Date('2026-06-13T00:00:01Z'),
    status: 'complete',
    visualState: { characterId: 'char-1', expression: 'happy', pose: 'leaning', background: 'cafe' },
    memoryContext: { used: true, summary: 'They like quiet cafes.', items: [{ id: 'mem-1', label: 'quiet cafes' }] },
    tts: { ttsContext: { characterId: 'char-1', emotionHint: 'tender' }, emotion: { scene: 'cafe window', intensity: 0.7, tags: ['warm', 'intimate'] } }
  }
];

describe('Moment Capture request builders', () => {
  it('builds a chat MomentCaptureRequest with selected character, source turn, scene state, and visual continuity', () => {
    const request = buildMomentCaptureRequestFromMessage(messages[1], messages, character, {
      conversationId: 'conversation-1',
      qualityPreset: 'balanced_8gb'
    });

    expect(request).toMatchObject({
      schema_version: 'moment_capture.v1',
      character_id: 'char-1',
      conversation_id: 'conversation-1',
      source_message_id: 'assistant-1',
      source_turn_index: 1,
      relationship_phase_snapshot: 'trusted',
      visual_identity_version: 'visual_identity_profile.v1',
      quality_preset: 'balanced_8gb'
    });
    expect(request.scene_state).toMatchObject({
      schema_version: 'scene_state.v1',
      location: 'cafe',
      pose: 'leaning',
      key_objects: ['quiet cafes'],
      wrong_appearance: ['blue eyes']
    });
    expect(request.scene_state.character_appearance).toContain('amber eyes');
    expect(request.visual_identity_snapshot).toMatchObject({ current_appearance: 'silver hair, amber eyes, warm smile' });
    expect(request.prompt_hash).toMatch(/^fe[0-9a-f]{8}$/);
  });

  it('builds a visual novel MomentCaptureRequest from current scene and latest dialogue', () => {
    const scene: ResolvedVisualNovelScene = {
      manifest: {
        id: 'manifest-1',
        characterName: 'Reverie',
        version: 1,
        defaults: { expression: 'neutral', pose: 'idle', background: 'default' },
        expressions: { neutral: { label: 'Neutral' }, happy: { label: 'Happy' }, sad: { label: 'Sad' }, thinking: { label: 'Thinking' }, flirty: { label: 'Flirty' }, surprised: { label: 'Surprised' }, concerned: { label: 'Concerned' } },
        poses: { idle: { label: 'Idle' }, listening: { label: 'Listening' }, speaking: { label: 'Speaking' }, leaning: { label: 'Leaning' } },
        backgrounds: { default: { kind: 'placeholder', alt: 'Room' }, bedroom: { kind: 'placeholder', alt: 'Bedroom' }, cafe: { kind: 'placeholder', alt: 'Cafe booth' }, night: { kind: 'placeholder', alt: 'Night sky' } },
        sprites: { idle: {}, listening: {}, speaking: {}, leaning: {} }
      },
      state: { characterId: 'char-1', expression: 'happy', pose: 'leaning', background: 'cafe' },
      sprite: { kind: 'placeholder', alt: 'Reverie leaning' },
      characterLayers: [{ id: 'base', slot: 'base', label: 'Base Reverie', order: 0, asset: { kind: 'placeholder', alt: 'Base' }, usedFallback: false }],
      background: { kind: 'placeholder', alt: 'Cafe booth' },
      expressionLabel: 'Happy',
      poseLabel: 'Leaning',
      usedFallback: false
    };

    const request = buildMomentCaptureRequestFromScene(scene, 'She smiles across the cafe table.', character, {
      conversationId: 'conversation-1',
      qualityPreset: 'preview_8gb',
      sourceMessageId: 'assistant-1',
      sourceTurnIndex: 1
    });

    expect(request.character_id).toBe('char-1');
    expect(request.source_message_id).toBe('assistant-1');
    expect(request.scene_state).toMatchObject({ location: 'cafe', pose: 'leaning', emotional_tone: 'Happy' });
    expect(request.scene_state.visual_hint).toEqual({ expression: 'happy', background: 'cafe' });
    expect(request.metadata.capture_source).toBe('visual_novel');
  });
});
