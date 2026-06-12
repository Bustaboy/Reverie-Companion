import { describe, expect, it, vi } from 'vitest';

describe('settingsStore performance presets', () => {
  it('maps quiet 8GB mode to conservative media defaults', async () => {
    vi.resetModules();
    const { settingsStore } = await import('./settingsStore');

    settingsStore.setPerformancePreset('quiet_8gb');
    const snapshot = settingsStore.getSnapshot();

    expect(snapshot.performancePreset).toBe('quiet_8gb');
    expect(snapshot.ttsLatencyPreset).toBe('speed');
    expect(snapshot.imageDefaultPreset).toBe('preview_8gb');
    expect(snapshot.backgroundTaskLimit).toBe('minimal');
  });
});
