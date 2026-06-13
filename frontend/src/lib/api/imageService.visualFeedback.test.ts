import { describe, expect, it } from 'vitest';
import { ImageService } from './imageService';

describe('ImageService visual feedback integration', () => {
  it('submits structured Moment Capture feedback to the character-scoped endpoint', async () => {
    let seenUrl = '';
    let payload: unknown;
    const fetcher = (async (url: RequestInfo | URL, init?: RequestInit) => {
      seenUrl = String(url);
      payload = JSON.parse(String(init?.body));
      return new Response(JSON.stringify({ record: { feedback_state: 'looks_right', review_state: 'accepted' }, visual_change_event: null }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }) as typeof fetch;

    const service = new ImageService({ baseUrl: 'http://test.local', fetcher });
    await service.submitMomentCaptureFeedback('capture 1', {
      character_id: 'char-1',
      action: 'looks_right',
      source_image_ref: 'job-1'
    });

    expect(seenUrl).toBe('http://test.local/api/moment-capture/capture%201/feedback');
    expect(payload).toMatchObject({ character_id: 'char-1', action: 'looks_right', source_image_ref: 'job-1' });
  });


  it('submits detailed trait feedback for wrong appearance corrections', async () => {
    let payload: unknown;
    const fetcher = (async (_url: RequestInfo | URL, init?: RequestInit) => {
      payload = JSON.parse(String(init?.body));
      return new Response(
        JSON.stringify({
          record: { feedback_state: 'wrong_appearance', review_state: 'unreviewed' },
          visual_change_event: { event_id: 'event-trait', character_id: 'char-1', canon_status: 'proposed' }
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    }) as typeof fetch;

    const service = new ImageService({ baseUrl: 'http://test.local', fetcher });
    await service.submitMomentCaptureFeedback('capture-trait', {
      character_id: 'char-1',
      action: 'wrong_appearance',
      trait_name: 'eye color',
      trait_value: 'eyes should stay amber',
      note: 'Generated blue eyes on this capture.'
    });

    expect(payload).toMatchObject({
      character_id: 'char-1',
      action: 'wrong_appearance',
      trait_name: 'eye color',
      trait_value: 'eyes should stay amber',
      note: 'Generated blue eyes on this capture.'
    });
  });

  it('lists and reviews visual change events through the M5-P05 review flow', async () => {
    const calls: string[] = [];
    const fetcher = (async (url: RequestInfo | URL, init?: RequestInit) => {
      calls.push(`${init?.method ?? 'GET'} ${String(url)}`);
      if (String(url).includes('/approve')) {
        return new Response(JSON.stringify({ event: { event_id: 'event-1', character_id: 'char-1', canon_status: 'canonized' } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      return new Response(JSON.stringify([{ event_id: 'event-1', character_id: 'char-1', canon_status: 'proposed' }]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }) as typeof fetch;

    const service = new ImageService({ baseUrl: 'http://test.local', fetcher });
    await service.listVisualChanges({ characterId: 'char-1', status: 'proposed' });
    await service.reviewVisualChange('event-1', 'approve', { character_id: 'char-1' });

    expect(calls).toEqual([
      'GET http://test.local/api/moment-capture/visual-changes?character_id=char-1&status_filter=proposed',
      'POST http://test.local/api/moment-capture/visual-changes/event-1/approve'
    ]);
  });
});
