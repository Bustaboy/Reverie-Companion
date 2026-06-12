import { writable } from 'svelte/store';
import type { ExtensionCommandRequest, ExtensionCommandResult, ExtensionEventEnvelope } from './types';
const MAX_LOCAL_EVENTS = 100;
const createEventBus = () => {
  const events = writable<ExtensionEventEnvelope[]>([]);
  const remember = (event: ExtensionEventEnvelope) => events.update((items) => [event, ...items].slice(0, MAX_LOCAL_EVENTS));
  return {
    events,
    async dispatch(request: ExtensionCommandRequest): Promise<ExtensionCommandResult> {
      try {
        const response = await fetch('/extensions/commands', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source: 'reverie.frontend', payload: {}, ...request }) });
        if (!response.ok) throw new Error(`Command ${request.command_id} failed with HTTP ${response.status}.`);
        const result = (await response.json()) as ExtensionCommandResult;
        if (result.event) remember(result.event);
        return result;
      } catch (error) {
        return { accepted: false, error: { code: 'frontend_extension_command_failed', message: error instanceof Error ? error.message : 'Extension command failed locally.', retryable: false } };
      }
    },
    publishLocal(event: ExtensionEventEnvelope) { remember(event); }
  };
};
export const extensionEventBus = createEventBus();
