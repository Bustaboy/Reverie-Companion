import { describe, expect, it } from 'vitest';
import { ChatService } from './chatService';

describe('ChatService character runtime payloads', () => {
  it('sends the selected character_id with non-streaming chat requests', async () => {
    let payload: Record<string, unknown> = {};
    const service = new ChatService({
      baseUrl: 'http://localhost:8000',
      fetcher: (async (_input: RequestInfo | URL, init?: RequestInit) => {
        payload = JSON.parse(String(init?.body));
        return new Response(JSON.stringify({ model: 'test', message: { role: 'assistant', content: 'hi' }, done: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }) as typeof fetch
    });

    await service.sendMessage('Hello', [], 'aria');

    expect(payload).toMatchObject({
      character_id: 'aria',
      stream: false,
      messages: [{ role: 'user', content: 'Hello' }]
    });
  });

  it('omits character_id when using the default local fallback', async () => {
    let payload: Record<string, unknown> = {};
    const service = new ChatService({
      baseUrl: 'http://localhost:8000',
      fetcher: (async (_input: RequestInfo | URL, init?: RequestInit) => {
        payload = JSON.parse(String(init?.body));
        return new Response(JSON.stringify({ model: 'test', message: { role: 'assistant', content: 'hi' }, done: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }) as typeof fetch
    });

    await service.sendMessage('Hello', [], null);

    expect(payload).not.toHaveProperty('character_id');
  });
});
