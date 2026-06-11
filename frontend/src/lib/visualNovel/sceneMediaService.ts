import type { SceneMediaCapabilities, VisualState } from '$lib/types/visualNovel';

export interface SceneMediaRequest {
  characterId: string;
  sceneId: string;
  intent: 'illustrate_current_scene' | 'generate_video_clip';
  visualState: VisualState;
  resourcePreset: 'preview_8gb' | 'balanced_8gb';
}

export interface SceneMediaJob {
  jobId: string;
  status: 'queued' | 'unavailable';
  message: string;
}

export class SceneMediaService {
  async checkCapabilities(): Promise<SceneMediaCapabilities> {
    return {
      available: false,
      modes: [],
      resourcePresets: ['preview_8gb', 'balanced_8gb'],
      message:
        'Visual generation is optional and not currently connected. Chat, memory, and growth still work normally.'
    };
  }

  async createSceneJob(_request: SceneMediaRequest): Promise<SceneMediaJob> {
    return {
      jobId: 'media_unavailable',
      status: 'unavailable',
      message:
        'Visual generation is optional and not currently connected. Connect a local media backend when scene generation is ready.'
    };
  }
}

export const sceneMediaService = new SceneMediaService();
