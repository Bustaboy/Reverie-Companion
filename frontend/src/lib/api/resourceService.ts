const API_BASE_URL = import.meta.env.VITE_REVERIE_API_BASE_URL ?? 'http://localhost:8000';

export type ResourcePressure = 'unknown' | 'normal' | 'elevated' | 'critical';

export interface ResourceStatus {
  pressure: ResourcePressure;
  vram: {
    free_mb: number | null;
    used_mb: number | null;
    total_mb: number | null;
    source: string;
    available: boolean;
  };
  tts_active: boolean;
  image_jobs_active: number;
  warning: string | null;
  recommended_action: string;
  headroom_mb: number | null;
}

export const resourceService = {
  async getStatus(): Promise<ResourceStatus> {
    const response = await fetch(`${API_BASE_URL}/api/resources/status`);
    if (!response.ok) throw new Error('Resource status is unavailable.');
    return (await response.json()) as ResourceStatus;
  }
};
