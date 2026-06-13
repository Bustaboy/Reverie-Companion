import { describe, expect, it } from 'vitest';
import { ImageService } from './imageService';

describe('ImageService visual feedback integration', () => {
  it('submits structured Moment Capture feedback with character scoping', async () => {
    let url = '';
    let payload: unknown;
    const fetcher = (async (requestUrl: RequestInfo | URL, init?: RequestInit) => {
      url = String(requestUrl);
      payload = JSON.parse(String(init?.body));
      return new Response(
        JSON.stringify({
          record: {
            capture_id: 'cap-1',
            image_job_id: 'job-1',
            character_id: 'char-1',
            feedback_state: 'looks_right',
            review_state: 'canon_requested',
            metadata: {}
          },
          visual_change_event: { event_id: 'evt-1', character_id: 'char-1', canon_status: 'proposed' }
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    }) as typeof fetch;

    const service = new ImageService({ baseUrl: 'http://test.local', fetcher });
    const response = await service.submitMomentCaptureFeedback('cap-1', {
      character_id: 'char-1',
      action: 'make_canon',
      trait_name: 'outfit',
      trait_value: 'red dress'
    });

    expect(url).toBe('http://test.local/api/moment-capture/cap-1/feedback');
    expect(payload).toMatchObject({ character_id: 'char-1', action: 'make_canon', trait_name: 'outfit', trait_value: 'red dress' });
    expect(response.visual_change_event?.event_id).toBe('evt-1');
  });

  it('loads and reviews pending visual changes', async () => {
    const calls: string[] = [];
    const fetcher = (async (requestUrl: RequestInfo | URL, init?: RequestInit) => {
      calls.push(`${init?.method ?? 'GET'} ${String(requestUrl)}`);
      if (String(requestUrl).includes('/approve')) {
        return new Response(JSON.stringify({ event: { event_id: 'evt-1', character_id: 'char-1', canon_status: 'approved' } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      return new Response(JSON.stringify([{ event_id: 'evt-1', character_id: 'char-1', canon_status: 'proposed' }]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }) as typeof fetch;

    const service = new ImageService({ baseUrl: 'http://test.local', fetcher });
    const events = await service.listVisualChanges({ characterId: 'char-1', status: 'proposed' });
    const reviewed = await service.reviewVisualChange('evt-1', 'approve', { characterId: 'char-1' });

    expect(events).toHaveLength(1);
    expect(calls[0]).toBe('GET http://test.local/api/moment-capture/visual-changes?character_id=char-1&status_filter=proposed');
    expect(calls[1]).toBe('POST http://test.local/api/moment-capture/visual-changes/evt-1/approve');
    expect(reviewed.event.canon_status).toBe('approved');
  });
});
