import { browser } from '$app/environment';
import { resourceService, type ResourceStatus } from '$lib/api/resourceService';
import { settingsStore } from '$lib/stores/settingsStore';

const POLL_MS = 10_000;
const INITIAL_STATUS: ResourceStatus = {
  pressure: 'unknown',
  vram: { free_mb: null, used_mb: null, total_mb: null, source: 'unavailable', available: false },
  tts_active: false,
  image_jobs_active: 0,
  warning: null,
  recommended_action: 'Use conservative 8GB defaults until local telemetry is available.',
  headroom_mb: null
};

class ResourceStore {
  status = $state<ResourceStatus>(INITIAL_STATUS);
  lastUpdatedAt = $state<Date | null>(null);
  error = $state<string | null>(null);
  enabled = $state(settingsStore.getSnapshot().proactiveResourceWarnings);

  private timer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    settingsStore.subscribe((settings) => {
      this.enabled = settings.proactiveResourceWarnings;
      this.configurePolling();
    });
    this.configurePolling();
  }

  get warningLabel() {
    if (!this.enabled) return null;
    if (this.status.warning) return this.status.warning;
    if (this.status.pressure === 'unknown') return 'GPU telemetry is unavailable; Reverie will keep preview-quality media defaults.';
    return null;
  }

  get compactLabel() {
    if (!this.status.vram.available) return 'VRAM telemetry unavailable';
    return `${this.status.vram.free_mb} MiB free · ${this.status.pressure} pressure`;
  }

  async refresh() {
    if (!browser || !this.enabled) return;
    try {
      this.status = await resourceService.getStatus();
      this.lastUpdatedAt = new Date();
      this.error = null;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Resource status is unavailable.';
    }
  }

  private configurePolling() {
    if (!browser) return;
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    if (!this.enabled) return;
    void this.refresh();
    this.timer = setInterval(() => void this.refresh(), POLL_MS);
  }
}

export const resourceStore = new ResourceStore();
