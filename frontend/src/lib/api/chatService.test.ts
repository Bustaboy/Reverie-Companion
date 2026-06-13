import { describe, expect, it } from 'vitest';
import { ChatService } from './chatService';

describe('ChatService character runtime payload', () => {
  it('includes the selected character_id when streaming chat requests', async () => {
    let payload: unknown;
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('event: done\ndata: {"done": true}\n\n'));
        controller.close();
      }
    });
    const fetcher = (async (_url: RequestInfo | URL, init?: RequestInit) => {
      payload = JSON.parse(String(init?.body));
      return new Response(stream, { status: 200, headers: { 'Content-Type': 'text/event-stream' } });
    }) as typeof fetch;

    const service = new ChatService({ baseUrl: 'http://test.local', fetcher });
    const events = [];

    for await (const event of service.sendMessageStream('Hello', [], { characterId: 'aria' })) {
      events.push(event.event);
    }

    expect(payload).toMatchObject({ character_id: 'aria', stream: true });
    expect(events).toEqual(['done']);
  });

  it('omits character_id so the backend can use its default fallback', async () => {
    let payload: unknown;
    const fetcher = (async (_url: RequestInfo | URL, init?: RequestInit) => {
      payload = JSON.parse(String(init?.body));
      return new Response(JSON.stringify({ model: 'test', message: { role: 'assistant', content: 'Hi' }, done: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }) as typeof fetch;

    const service = new ChatService({ baseUrl: 'http://test.local', fetcher });
    await service.sendMessage('Hello');

    expect(payload).toMatchObject({ stream: false });
    expect(payload).not.toHaveProperty('character_id');
  });
});
