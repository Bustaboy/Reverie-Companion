import { writable } from 'svelte/store';
import type { ExtensionEvent, ExtensionEventScope } from './contracts';

type Listener<TPayload extends Record<string, unknown> = Record<string, unknown>> = (
  event: ExtensionEvent<TPayload>
) => void;

const MAX_EVENT_HISTORY = 100;
const listeners = new Map<string, Set<Listener>>();
const historyStore = writable<ExtensionEvent[]>([]);

const safeNotify = (listener: Listener, event: ExtensionEvent) => {
  try {
    listener(event);
  } catch (error) {
    console.warn('Reverie extension event listener failed', { event: event.event_type, error });
  }
};

export const extensionEventBus = {
  history: { subscribe: historyStore.subscribe },

  publish<TPayload extends Record<string, unknown>>(
    event_type: string,
    scope: ExtensionEventScope,
    source: string,
    payload: TPayload
  ): ExtensionEvent<TPayload> {
    const event: ExtensionEvent<TPayload> = {
      event_id: `fe_evt_${crypto.randomUUID?.() ?? Date.now().toString(36)}`,
      event_type,
      scope,
      source,
      payload,
      created_at: new Date().toISOString()
    };

    historyStore.update((history) => [...history.slice(-(MAX_EVENT_HISTORY - 1)), event]);
    listeners.get(event_type)?.forEach((listener) => safeNotify(listener, event));
    listeners.get('*')?.forEach((listener) => safeNotify(listener, event));
    return event;
  },

  subscribe<TPayload extends Record<string, unknown>>(eventType: string, listener: Listener<TPayload>) {
    const typedListener = listener as Listener;
    const bucket = listeners.get(eventType) ?? new Set<Listener>();
    bucket.add(typedListener);
    listeners.set(eventType, bucket);
    return () => {
      bucket.delete(typedListener);
      if (bucket.size === 0) listeners.delete(eventType);
    };
  }
};
