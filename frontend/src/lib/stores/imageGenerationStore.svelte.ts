import { imageService, ImageServiceError, type ImageJobEvent, type ImageJobRead, type ImageQualityPreset } from '$lib/api/imageService';
import { settingsStore } from '$lib/stores/settingsStore';
import { ttsStore } from '$lib/stores/ttsStore.svelte';
import type { ChatMessage } from '$lib/types/chat';
import type { ResolvedVisualNovelScene } from '$lib/types/visualNovel';

export type ImageGenerationSource = 'chat-message' | 'chat-global' | 'visual-novel' | 'auto-chat';

export interface ImageGenerationJob extends ImageJobRead {
  source: ImageGenerationSource;
  sourceMessageId?: string;
  sourceLabel: string;
  displayPrompt: string;
  imageUrls: string[];
  submittedAt: Date;
}

interface QueueImageInput {
  source: ImageGenerationSource;
  prompt: string;
  sourceLabel: string;
  sourceMessageId?: string;
  context?: Record<string, unknown>;
  qualityPreset?: ImageQualityPreset;
}

const MAX_VISIBLE_JOBS = 8;
const PROMPT_SOFT_LIMIT = 900;

const TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled']);

const clipPrompt = (prompt: string): string => {
  const normalized = prompt.trim().replace(/\s+/g, ' ');
  if (normalized.length <= PROMPT_SOFT_LIMIT) return normalized;
  return `${normalized.slice(0, PROMPT_SOFT_LIMIT).trim()} …`;
};

const isTerminalStatus = (status: ImageJobRead['status']) => TERMINAL_STATUSES.has(status);

const normalizeError = (error: unknown): string => {
  if (error instanceof ImageServiceError) {
    if (error.code === 'image_generation_disabled') return 'Image generation is disabled in the local backend settings.';
    if (error.code === 'image_queue_full') return 'The local image queue is full. Wait for one scene to finish, then try again.';
    if (error.retryable) return `${error.message} You can try again in a moment.`;
    return error.message;
  }
  return 'Reverie could not queue that image. Chat and voice are still safe.';
};

const jobFromRead = (job: ImageJobRead, input: QueueImageInput): ImageGenerationJob => ({
  ...job,
  source: input.source,
  sourceMessageId: input.sourceMessageId,
  sourceLabel: input.sourceLabel,
  displayPrompt: input.prompt,
  imageUrls: job.output_paths.map((path) => imageService.resolveOutputUrl(path)).filter(Boolean),
  submittedAt: new Date()
});

const jobFromEvent = (existing: ImageGenerationJob, event: ImageJobEvent): ImageGenerationJob => ({
  ...existing,
  status: event.status,
  phase: event.phase,
  progress: event.progress,
  message: event.message,
  resource_mode: event.resource_mode,
  output_paths: event.output_paths,
  error: event.error,
  fallback_used: event.fallback_used,
  vram_free_mb: event.vram_free_mb,
  vram_required_mb: event.vram_required_mb,
  updated_at: event.timestamp,
  imageUrls: event.output_paths.map((path) => imageService.resolveOutputUrl(path)).filter(Boolean)
});

const contextFromMessage = (message: ChatMessage): Record<string, unknown> => ({
  source: 'chat',
  message_id: message.id,
  role: message.role,
  visible_text: message.content,
  visual_state: message.visualState,
  tts_context: message.tts?.ttsContext,
  emotion: message.tts?.emotion,
  memories: message.memoryContext?.items?.map((item) => item.label) ?? [],
  memory_summary: message.memoryContext?.summary
});

const promptFromMessage = (message: ChatMessage): string => {
  const prefix = message.role === 'assistant' ? 'Visualize Reverie in this moment:' : 'Visualize the user-described scene:';
  return clipPrompt(`${prefix} ${message.content}`);
};

const contextFromScene = (scene: ResolvedVisualNovelScene, latestDialogue: string): Record<string, unknown> => ({
  source: 'visual_novel',
  character: { name: scene.manifest.characterName },
  visual_state: scene.state,
  background: scene.state.background,
  scene: `${scene.expressionLabel}, ${scene.poseLabel}, ${scene.state.background}`,
  recent_messages: latestDialogue ? [{ role: 'assistant', content: latestDialogue }] : []
});

class ImageGenerationStore {
  jobs = $state<ImageGenerationJob[]>([]);
  error = $state<string | null>(null);
  announcement = $state('Images are ready when you ask.');
  autoGenerateOnAssistant = $state(settingsStore.getSnapshot().imageAutoGenerateOnAssistant);

  private controllers = new Map<string, AbortController>();

  constructor() {
    settingsStore.subscribe((settings) => {
      this.autoGenerateOnAssistant = settings.imageAutoGenerateOnAssistant;
    });
  }

  get activeJobs() {
    return this.jobs.filter((job) => !isTerminalStatus(job.status));
  }

  get completedJobs() {
    return this.jobs.filter((job) => job.status === 'completed');
  }

  get latestVisualNovelJob() {
    return this.jobs.find((job) => job.source === 'visual-novel' && job.status !== 'cancelled') ?? null;
  }

  get isBusy() {
    return this.activeJobs.length > 0;
  }

  get statusLabel() {
    const active = this.activeJobs[0];
    if (!active) return this.error ? 'Image generation needs attention' : 'Images ready';
    if (ttsStore.isSpeaking || ttsStore.presenceState === 'preparing') return 'Images paused for voice';
    if (active.status === 'paused') return 'Image generation paused';
    if (active.status === 'waiting_for_resources') return 'Checking VRAM for image generation';
    if (active.status === 'running') return 'Composing image';
    return 'Image queued';
  }

  get resourceAwarenessLabel() {
    if (ttsStore.isSpeaking || ttsStore.presenceState === 'preparing') {
      return 'Voice has priority; image work will resume automatically.';
    }
    const active = this.activeJobs[0];
    if (!active) return 'Image generation stays idle until you ask.';
    if (active.vram_free_mb !== null && active.vram_free_mb !== undefined && active.vram_required_mb) {
      return `${active.vram_free_mb} MiB VRAM free · ${active.vram_required_mb} MiB target.`;
    }
    return active.message;
  }

  jobsForMessage(messageId: string): ImageGenerationJob[] {
    return this.jobs.filter((job) => job.sourceMessageId === messageId);
  }

  latestCompletedForMessage(messageId: string): ImageGenerationJob | null {
    return this.jobs.find((job) => job.sourceMessageId === messageId && job.status === 'completed') ?? null;
  }

  generateFromMessage(message: ChatMessage, source: ImageGenerationSource = 'chat-message') {
    if (!message.content.trim()) return;
    void this.queueImage({
      source,
      sourceMessageId: message.id,
      sourceLabel: message.role === 'assistant' ? 'Chat reply' : 'User message',
      prompt: promptFromMessage(message),
      context: contextFromMessage(message),
      qualityPreset: 'preview_8gb'
    });
  }

  generateFromLatestMessage(messages: ChatMessage[]) {
    const message = [...messages].reverse().find((candidate) => candidate.content.trim() && candidate.status !== 'streaming');
    if (message) this.generateFromMessage(message, 'chat-global');
  }

  visualizeScene(scene: ResolvedVisualNovelScene, latestDialogue: string) {
    const dialogue = latestDialogue.trim();
    const prompt = clipPrompt(
      `Visualize the current visual novel scene with ${scene.manifest.characterName}: ${scene.expressionLabel}, ${scene.poseLabel}, ${scene.state.background}${dialogue ? `. Dialogue mood: ${dialogue}` : ''}`
    );
    void this.queueImage({
      source: 'visual-novel',
      sourceLabel: 'Visual novel scene',
      prompt,
      context: contextFromScene(scene, dialogue),
      qualityPreset: 'preview_8gb'
    });
  }

  maybeAutoGenerateFromAssistant(message: ChatMessage) {
    if (!this.autoGenerateOnAssistant || message.role !== 'assistant' || message.status !== 'complete') return;
    if (this.jobs.some((job) => job.sourceMessageId === message.id)) return;
    this.generateFromMessage(message, 'auto-chat');
  }

  async cancel(jobId: string) {
    this.controllers.get(jobId)?.abort();
    try {
      const cancelled = await imageService.cancelJob(jobId);
      this.patchJob(jobId, (job) => ({
        ...job,
        ...cancelled,
        imageUrls: cancelled.output_paths.map((path) => imageService.resolveOutputUrl(path)).filter(Boolean)
      }));
      this.announcement = 'Image generation cancelled.';
    } catch (error) {
      this.error = normalizeError(error);
      this.announcement = this.error;
    }
  }

  dismissError() {
    this.error = null;
  }

  setAutoGenerateOnAssistant(enabled: boolean) {
    settingsStore.setImageAutoGenerateOnAssistant(enabled);
  }

  private async queueImage(input: QueueImageInput) {
    const prompt = clipPrompt(input.prompt);
    if (!prompt) return;

    this.error = null;
    this.announcement = ttsStore.isSpeaking
      ? 'Queued a scene image. Voice has priority, so rendering will wait safely.'
      : 'Queued a local scene image.';

    try {
      const response = await imageService.generateImage({
        prompt,
        context: input.context,
        quality_preset: input.qualityPreset ?? 'preview_8gb'
      });
      const job = jobFromRead(response.job, { ...input, prompt });
      this.upsertJob(job);
      this.watchJob(job.job_id);
    } catch (error) {
      this.error = normalizeError(error);
      this.announcement = this.error;
    }
  }

  private watchJob(jobId: string) {
    const controller = new AbortController();
    this.controllers.set(jobId, controller);
    void imageService
      .streamJobEvents(
        jobId,
        {
          onEvent: (event) => {
            this.patchJob(event.job_id, (job) => jobFromEvent(job, event));
            this.announcement = event.message;
            if (event.error?.message) this.error = event.error.message;
          }
        },
        { signal: controller.signal }
      )
      .catch((error) => {
        if (controller.signal.aborted) return;
        this.error = normalizeError(error);
        this.announcement = this.error;
      })
      .finally(() => {
        if (this.controllers.get(jobId) === controller) this.controllers.delete(jobId);
      });
  }

  private upsertJob(job: ImageGenerationJob) {
    const withoutExisting = this.jobs.filter((candidate) => candidate.job_id !== job.job_id);
    this.jobs = [job, ...withoutExisting].slice(0, MAX_VISIBLE_JOBS);
  }

  private patchJob(jobId: string, patcher: (job: ImageGenerationJob) => ImageGenerationJob) {
    this.jobs = this.jobs.map((job) => (job.job_id === jobId ? patcher(job) : job));
  }
}

export const imageGenerationStore = new ImageGenerationStore();
