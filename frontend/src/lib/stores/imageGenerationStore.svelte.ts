import {
  imageService,
  ImageServiceError,
  type ImageHistoryItem,
  type ImageJobEvent,
  type ImageJobRead,
  type ImageQualityPreset,
  type VisualFeedbackSubmitRequest
} from '$lib/api/imageService';
import type { VisualChangeEvent, VisualFeedbackAction } from '$lib/types/momentCapture';
import { settingsStore } from '$lib/stores/settingsStore';
import { ttsStore } from '$lib/stores/ttsStore.svelte';
import type { ChatMessage } from '$lib/types/chat';
import type { ResolvedVisualNovelScene } from '$lib/types/visualNovel';

export type ImageGenerationSource = 'chat-message' | 'chat-global' | 'visual-novel' | 'auto-chat' | 'gallery';

export interface ImageGenerationJob extends ImageJobRead {
  source: ImageGenerationSource;
  sourceMessageId?: string;
  sourceLabel: string;
  displayPrompt: string;
  imageUrls: string[];
  submittedAt: Date;
}

export interface ImageGalleryItem extends ImageHistoryItem {
  imageUrls: string[];
  thumbnailUrls: string[];
}

interface QueueImageInput {
  source: ImageGenerationSource;
  prompt: string;
  sourceLabel: string;
  sourceMessageId?: string;
  context?: Record<string, unknown>;
  qualityPreset?: ImageQualityPreset;
  conversationId?: string;
  characterId?: string;
}

const MAX_VISIBLE_JOBS = 8;
const PROMPT_SOFT_LIMIT = 900;
const DEFAULT_CONVERSATION_ID = 'default';

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
    if (error.code === 'image_asset_source_unavailable') return 'That image file is not reachable locally yet. Open ComfyUI or regenerate, then save again.';
    if (error.code === 'image_asset_manifest_write_failed') return 'The image copied, but Reverie could not update the character asset manifest. Check local file permissions and retry.';
    if (error.code === 'image_history_write_failed') return 'Reverie could not update the local image gallery metadata. Check that the data folder is writable, then retry.';
    if (error.code === 'image_history_not_found') return 'That image is no longer in this conversation gallery.';
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
  imageUrls: job.output_paths.map((_, index) => imageService.resolveOutputUrl(job.job_id, index)).filter(Boolean),
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
  saved_to_assets: event.saved_to_assets,
  character_id: event.character_id,
  session_id: event.session_id,
  moment_capture_id: event.moment_capture_id,
  scene_summary: event.scene_summary,
  prompt_hash: event.prompt_hash,
  feedback_status: event.feedback_status,
  review_status: event.review_status,
  canon_status: event.canon_status,
  pressure: event.pressure,
  warning: event.warning,
  imageUrls: event.output_paths.map((_, index) => imageService.resolveOutputUrl(event.job_id, index)).filter(Boolean)
});

const galleryItemFromHistory = (item: ImageHistoryItem): ImageGalleryItem => ({
  ...item,
  imageUrls: item.output_paths.map((_, index) => imageService.resolveOutputUrl(item.job_id, index)).filter(Boolean),
  thumbnailUrls: (item.thumbnail_paths.length ? item.thumbnail_paths : item.output_paths)
    .slice(0, 1)
    .map((_, index) => imageService.resolveOutputUrl(item.job_id, index))
    .filter(Boolean)
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
  gallery = $state<ImageGalleryItem[]>([]);
  galleryLoading = $state(false);
  visualChanges = $state<VisualChangeEvent[]>([]);
  visualChangesLoading = $state(false);
  feedbackSubmitting = $state<Record<string, boolean>>({});
  error = $state<string | null>(null);
  announcement = $state('Images are ready when you ask.');
  autoGenerateOnAssistant = $state(settingsStore.getSnapshot().imageAutoGenerateOnAssistant);
  defaultPreset = $state<ImageQualityPreset>(settingsStore.getSnapshot().imageDefaultPreset);
  currentConversationId = $state(DEFAULT_CONVERSATION_ID);
  currentCharacterFilter = $state<string | undefined>(undefined);

  private controllers = new Map<string, AbortController>();

  constructor() {
    settingsStore.subscribe((settings) => {
      this.autoGenerateOnAssistant = settings.imageAutoGenerateOnAssistant;
      this.defaultPreset = settings.imageDefaultPreset;
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
      qualityPreset: this.defaultPreset
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
      qualityPreset: this.defaultPreset
    });
  }

  maybeAutoGenerateFromAssistant(message: ChatMessage) {
    if (!this.autoGenerateOnAssistant || message.role !== 'assistant' || message.status !== 'complete') return;
    if (this.jobs.some((job) => job.sourceMessageId === message.id)) return;
    this.generateFromMessage(message, 'auto-chat');
  }

  regenerate(jobOrItem: ImageGenerationJob | ImageGalleryItem) {
    void this.queueImage({
      source: 'gallery',
      sourceLabel: 'Regenerated image',
      sourceMessageId: 'sourceMessageId' in jobOrItem ? jobOrItem.sourceMessageId : jobOrItem.source_message_id ?? undefined,
      prompt: 'displayPrompt' in jobOrItem ? jobOrItem.displayPrompt : jobOrItem.prompt,
      context: { source: 'regenerate', original_job_id: jobOrItem.job_id },
      qualityPreset: jobOrItem.requested_preset ?? this.defaultPreset,
      conversationId: jobOrItem.conversation_id ?? this.currentConversationId
    });
  }

  vary(jobOrItem: ImageGenerationJob | ImageGalleryItem) {
    const prompt = 'displayPrompt' in jobOrItem ? jobOrItem.displayPrompt : jobOrItem.prompt;
    void this.queueImage({
      source: 'gallery',
      sourceLabel: 'Image variation',
      sourceMessageId: 'sourceMessageId' in jobOrItem ? jobOrItem.sourceMessageId : jobOrItem.source_message_id ?? undefined,
      prompt: clipPrompt(`${prompt} Subtle variation: keep the same character identity and scene mood, but change composition, lighting, pose, or camera angle.`),
      context: { source: 'variation', original_job_id: jobOrItem.job_id },
      qualityPreset: jobOrItem.requested_preset ?? this.defaultPreset,
      conversationId: jobOrItem.conversation_id ?? this.currentConversationId
    });
  }

  async loadGallery(conversationId = this.currentConversationId, characterId = this.currentCharacterFilter) {
    this.galleryLoading = true;
    this.error = null;
    this.currentConversationId = conversationId;
    this.currentCharacterFilter = characterId;
    try {
      const response = await imageService.listHistory(conversationId, { characterId });
      this.gallery = response.items.slice(0, 80).map(galleryItemFromHistory);
      this.announcement = this.gallery.length ? `Loaded ${this.gallery.length} saved images.` : 'No saved images for this conversation yet.';
      void this.loadVisualChanges(characterId);
    } catch (error) {
      this.error = normalizeError(error);
      this.announcement = this.error;
    } finally {
      this.galleryLoading = false;
    }
  }

  async deleteImage(jobId: string) {
    try {
      const response = await imageService.deleteHistoryItem(jobId);
      this.gallery = response.items.slice(0, 80).map(galleryItemFromHistory);
      this.jobs = this.jobs.filter((job) => job.job_id !== jobId);
      this.announcement = 'Image removed from this conversation gallery.';
    } catch (error) {
      this.error = normalizeError(error);
      this.announcement = this.error;
      void this.loadGallery();
    }
  }

  async saveToCharacterAssets(jobOrItem: ImageGenerationJob | ImageGalleryItem, characterId = 'default') {
    try {
      const response = await imageService.saveToCharacterAssets(jobOrItem.job_id, {
        characterId,
        assetLabel: 'prompt_summary' in jobOrItem ? jobOrItem.prompt_summary : jobOrItem.displayPrompt,
        outputIndex: 0
      });
      this.gallery = this.gallery.map((item) => (item.job_id === response.item.job_id ? galleryItemFromHistory(response.item) : item));
      this.jobs = this.jobs.map((job) => (job.job_id === response.item.job_id ? { ...job, saved_to_assets: true } : job));
      this.announcement = 'Saved image to the character asset manifest.';
    } catch (error) {
      this.error = normalizeError(error);
      this.announcement = this.error;
    }
  }


  async submitFeedback(item: ImageGalleryItem, action: VisualFeedbackAction, input: { traitName?: string; traitValue?: string; note?: string } = {}) {
    if (!item.moment_capture_id || !item.character_id) {
      this.error = 'This legacy image can be regenerated, saved, or deleted, but structured visual feedback needs a character-linked Moment Capture record.';
      this.announcement = this.error;
      return;
    }
    this.feedbackSubmitting = { ...this.feedbackSubmitting, [item.job_id]: true };
    this.error = null;
    try {
      const request: VisualFeedbackSubmitRequest = {
        character_id: item.character_id,
        action,
        trait_name: input.traitName || undefined,
        trait_value: input.traitValue || undefined,
        note: input.note || undefined,
        source_image_ref: item.output_paths[0] ?? item.job_id,
        metadata: { image_job_id: item.job_id, prompt_hash: item.prompt_hash }
      };
      const response = await imageService.submitMomentCaptureFeedback(item.moment_capture_id, request);
      this.patchGalleryFromRecord(response.record);
      if (response.visual_change_event) this.upsertVisualChange(response.visual_change_event);
      this.announcement = response.visual_change_event
        ? 'Feedback saved as a pending visual change for review.'
        : 'Visual feedback saved to this gallery record.';
      void this.loadGallery(item.conversation_id, item.character_id);
    } catch (error) {
      this.error = normalizeError(error);
      this.announcement = this.error;
    } finally {
      const { [item.job_id]: _done, ...rest } = this.feedbackSubmitting;
      this.feedbackSubmitting = rest;
    }
  }

  async loadVisualChanges(characterId = this.currentCharacterFilter, status: string | null = 'proposed') {
    this.visualChangesLoading = true;
    try {
      this.visualChanges = await imageService.listVisualChanges({ characterId, status });
    } catch (error) {
      this.error = normalizeError(error);
      this.announcement = this.error;
    } finally {
      this.visualChangesLoading = false;
    }
  }

  async reviewVisualChange(event: VisualChangeEvent, action: 'approve' | 'reject' | 'rollback') {
    try {
      const response = await imageService.reviewVisualChange(event.event_id, action, { characterId: event.character_id });
      this.upsertVisualChange(response.event);
      this.announcement = `Visual change ${action === 'approve' ? 'approved' : action === 'reject' ? 'rejected' : 'rolled back'}.`;
      void this.loadGallery(this.currentConversationId, event.character_id);
    } catch (error) {
      this.error = normalizeError(error);
      this.announcement = this.error;
    }
  }

  private patchGalleryFromRecord(record: { image_job_id: string; feedback_state: string; review_state: string; rollback_id?: string | null; metadata?: Record<string, unknown> }) {
    this.gallery = this.gallery.map((item) =>
      item.job_id === record.image_job_id
        ? {
            ...item,
            feedback_status: record.feedback_state,
            review_status: record.review_state,
            canon_status: record.review_state === 'canon_requested' ? 'proposed' : item.canon_status,
            metadata: { ...(item.metadata ?? {}), moment_capture_record: record, feedback_summary: record.metadata?.feedback_summary }
          }
        : item
    );
  }

  private upsertVisualChange(event: VisualChangeEvent) {
    this.visualChanges = [event, ...this.visualChanges.filter((candidate) => candidate.event_id !== event.event_id)];
  }

  async cancel(jobId: string) {
    this.controllers.get(jobId)?.abort();
    try {
      const cancelled = await imageService.cancelJob(jobId);
      this.patchJob(jobId, (job) => ({
        ...job,
        ...cancelled,
        source: job.source,
        sourceMessageId: job.sourceMessageId,
        sourceLabel: job.sourceLabel,
        displayPrompt: job.displayPrompt,
        submittedAt: job.submittedAt,
        imageUrls: cancelled.output_paths.map((_, index) => imageService.resolveOutputUrl(cancelled.job_id, index)).filter(Boolean)
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

  setDefaultPreset(preset: ImageQualityPreset) {
    settingsStore.setImageDefaultPreset(preset);
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
        conversation_id: input.conversationId ?? this.currentConversationId,
        source: input.source,
        source_message_id: input.sourceMessageId,
        prompt,
        context: input.characterId ? { ...(input.context ?? {}), character: { ...((input.context?.character as Record<string, unknown> | undefined) ?? {}), id: input.characterId } } : input.context,
        quality_preset: input.qualityPreset ?? this.defaultPreset
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
            if (event.warning) this.announcement = event.warning;
            if (event.status === 'completed') void this.loadGallery(event.conversation_id ?? this.currentConversationId);
            if (isTerminalStatus(event.status)) this.controllers.get(event.job_id)?.abort();
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
