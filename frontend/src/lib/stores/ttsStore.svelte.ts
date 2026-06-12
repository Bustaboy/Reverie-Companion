import { browser } from '$app/environment';
import { settingsStore, type SettingsState } from '$lib/stores/settingsStore';
import { ttsService, type TtsContext, type TtsGenerateRequest } from '$lib/api/ttsService';
import type { ChatMessage, ChatTtsMetadata } from '$lib/types/chat';

export type TtsPlaybackStatus = 'idle' | 'queued' | 'synthesizing' | 'playing' | 'paused' | 'error';
export type TtsQueueSource = 'chat' | 'visual-novel' | 'manual';

export interface TtsQueueItem {
  id: string;
  text: string;
  ttsText?: string;
  voiceId?: string;
  voiceName?: string;
  context?: TtsContext;
  messageId?: string;
  source: TtsQueueSource;
  createdAt: Date;
}

interface LoadedAudio {
  url: string;
  itemId: string;
}

const MAX_QUEUE_ITEMS = 3;
const MIN_SPEAKABLE_CHARS = 2;

const createQueueId = () =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `tts-${Date.now()}-${Math.random().toString(36).slice(2)}`;

const voiceLabel = (voiceId?: string, voiceName?: string): string => {
  if (voiceName) return voiceName;
  if (!voiceId) return 'Reverie voice';
  return voiceId
    .split(/[_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
};

const audioMimeType = (format: string): string => {
  if (format === 'mp3') return 'audio/mpeg';
  if (format === 'pcm') return 'audio/wav';
  return `audio/${format}`;
};

const base64ToBlob = (base64: string, mimeType: string): Blob => {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return new Blob([bytes], { type: mimeType });
};

class ReverieTtsStore {
  queue = $state<TtsQueueItem[]>([]);
  currentItem = $state<TtsQueueItem | null>(null);
  status = $state<TtsPlaybackStatus>('idle');
  progress = $state(0);
  durationSeconds = $state(0);
  currentTimeSeconds = $state(0);
  error = $state<string | null>(null);
  liveAnnouncement = $state('Voice playback ready.');
  enabled = $state(settingsStore.getSnapshot().ttsEnabled);
  autoPlay = $state(settingsStore.getSnapshot().ttsAutoPlay);
  volume = $state(settingsStore.getSnapshot().ttsVolume);
  speed = $state(settingsStore.getSnapshot().ttsSpeed);
  qualityPreference = $state(settingsStore.getSnapshot().ttsQualityPreference);

  currentVoiceName = $derived(voiceLabel(this.currentItem?.voiceId, this.currentItem?.voiceName));
  isBusy = $derived(this.status === 'queued' || this.status === 'synthesizing' || this.status === 'playing' || this.status === 'paused');
  canPause = $derived(this.status === 'playing');
  canResume = $derived(this.status === 'paused');

  private audio: HTMLAudioElement | null = null;
  private activeController: AbortController | null = null;
  private loadedAudio: LoadedAudio | null = null;
  constructor() {
    if (browser) {
      this.audio = new Audio();
      this.audio.preload = 'metadata';
      this.audio.volume = this.volume;
      this.audio.playbackRate = this.speed;
      this.audio.addEventListener('timeupdate', this.handleTimeUpdate);
      this.audio.addEventListener('loadedmetadata', this.handleLoadedMetadata);
      this.audio.addEventListener('ended', this.handleEnded);
      this.audio.addEventListener('error', this.handleAudioError);
    }

    settingsStore.subscribe((settings) => this.applySettings(settings));
  }

  enqueueFromDone(metadata: ChatTtsMetadata | undefined, options: { messageId?: string; source?: TtsQueueSource; interrupt?: boolean } = {}) {
    if (!metadata || !this.enabled || !this.autoPlay) return;
    this.enqueue(
      {
        text: metadata.text,
        ttsText: metadata.ttsText,
        voiceId: metadata.voiceId,
        voiceName: metadata.voiceName,
        context: metadata.context,
        messageId: options.messageId,
        source: options.source ?? 'chat'
      },
      { interrupt: options.interrupt ?? true }
    );
  }

  playMessage(message: ChatMessage, source: TtsQueueSource = 'manual') {
    if (message.role !== 'assistant' || message.status === 'streaming') return;

    this.enqueue(
      {
        text: message.tts?.text ?? message.content,
        ttsText: message.tts?.ttsText,
        voiceId: message.tts?.voiceId,
        voiceName: message.tts?.voiceName,
        context: message.tts?.context,
        messageId: message.id,
        source
      },
      { interrupt: true }
    );
  }

  enqueue(
    item: Omit<TtsQueueItem, 'id' | 'createdAt'>,
    options: { interrupt?: boolean; startImmediately?: boolean } = {}
  ) {
    const text = item.text.trim();
    if (!this.enabled || text.length < MIN_SPEAKABLE_CHARS) return;

    const queueItem: TtsQueueItem = {
      ...item,
      text,
      ttsText: item.ttsText?.trim() || undefined,
      id: createQueueId(),
      createdAt: new Date()
    };

    if (options.interrupt) {
      this.cancel('Starting the newest voice line.');
    }

    this.queue = [...this.queue, queueItem].slice(-MAX_QUEUE_ITEMS);
    this.error = null;
    this.liveAnnouncement = `Queued ${voiceLabel(queueItem.voiceId, queueItem.voiceName)}.`;

    if (options.startImmediately !== false) {
      void this.playNext();
    }
  }

  async playNext() {
    if (!browser || !this.audio || this.status === 'synthesizing' || this.status === 'playing' || this.status === 'paused') return;

    const nextItem = this.queue[0];
    if (!nextItem) {
      this.status = 'idle';
      this.currentItem = null;
      this.progress = 0;
      return;
    }

    this.queue = this.queue.slice(1);
    this.currentItem = nextItem;
    this.status = 'synthesizing';
    this.progress = 0;
    this.currentTimeSeconds = 0;
    this.durationSeconds = 0;
    this.error = null;
    this.liveAnnouncement = `Preparing ${voiceLabel(nextItem.voiceId, nextItem.voiceName)}.`;

    const controller = new AbortController();
    this.activeController = controller;

    try {
      const response = await ttsService.generateSpeech(this.toGenerateRequest(nextItem), controller.signal);
      if (controller.signal.aborted || this.currentItem?.id !== nextItem.id) return;

      this.revokeLoadedAudio();
      const audioBlob = base64ToBlob(response.audio_base64, audioMimeType(response.audio_format));
      const url = URL.createObjectURL(audioBlob);
      this.loadedAudio = { url, itemId: nextItem.id };
      this.audio.src = url;
      this.audio.volume = this.volume;
      this.audio.playbackRate = this.speed;
      this.durationSeconds = response.duration_seconds ?? 0;
      this.status = 'playing';
      this.liveAnnouncement = `Speaking with ${voiceLabel(nextItem.voiceId, nextItem.voiceName)}.`;
      await this.audio.play();
    } catch (error) {
      if (controller.signal.aborted) return;
      const message = error instanceof Error ? error.message : 'Voice playback failed.';
      this.status = 'error';
      this.error = message;
      this.liveAnnouncement = message;
      this.finishCurrentLine();
    } finally {
      if (this.activeController === controller) {
        this.activeController = null;
      }
    }
  }

  pause() {
    if (!this.audio || this.status !== 'playing') return;
    this.audio.pause();
    this.status = 'paused';
    this.liveAnnouncement = 'Voice playback paused.';
  }

  resume() {
    if (!this.audio || this.status !== 'paused') return;
    this.status = 'playing';
    this.liveAnnouncement = 'Voice playback resumed.';
    void this.audio.play().catch((error: unknown) => {
      this.status = 'error';
      this.error = error instanceof Error ? error.message : 'Voice playback could not resume.';
    });
  }

  stop() {
    if (this.audio) {
      this.audio.pause();
      this.audio.currentTime = 0;
    }
    this.status = 'idle';
    this.progress = 0;
    this.currentTimeSeconds = 0;
    this.liveAnnouncement = 'Voice playback stopped.';
  }

  cancel(reason = 'Voice playback cancelled.') {
    this.activeController?.abort();
    this.queue = [];
    this.stop();
    this.currentItem = null;
    this.error = null;
    this.liveAnnouncement = reason;
    this.revokeLoadedAudio();
  }

  setAutoPlay(enabled: boolean) {
    settingsStore.setTtsAutoPlay(enabled);
  }

  setEnabled(enabled: boolean) {
    settingsStore.setTtsEnabled(enabled);
    if (!enabled) {
      this.cancel('Voice playback disabled.');
    }
  }

  clearError() {
    this.error = null;
    if (this.status === 'error') this.status = 'idle';
  }

  private toGenerateRequest(item: TtsQueueItem): TtsGenerateRequest {
    return {
      text: item.text,
      tts_text: item.ttsText,
      voice_id: item.voiceId,
      context: item.context,
      audio_format: this.qualityPreference === 'quality' ? 'wav' : 'wav',
      stream: false
    };
  }

  private applySettings(settings: SettingsState) {
    this.enabled = settings.ttsEnabled;
    this.autoPlay = settings.ttsAutoPlay;
    this.volume = settings.ttsVolume;
    this.speed = settings.ttsSpeed;
    this.qualityPreference = settings.ttsQualityPreference;

    if (this.audio) {
      this.audio.volume = this.volume;
      this.audio.playbackRate = this.speed;
    }

    if (!settings.ttsEnabled && this.isBusy) {
      this.cancel('Voice playback disabled.');
    }
  }

  private handleTimeUpdate = () => {
    if (!this.audio) return;
    const duration = Number.isFinite(this.audio.duration) ? this.audio.duration : this.durationSeconds;
    this.currentTimeSeconds = this.audio.currentTime;
    this.durationSeconds = duration || this.durationSeconds;
    this.progress = duration ? Math.min(1, Math.max(0, this.audio.currentTime / duration)) : 0;
  };

  private handleLoadedMetadata = () => {
    if (!this.audio || !Number.isFinite(this.audio.duration)) return;
    this.durationSeconds = this.audio.duration;
  };

  private handleEnded = () => {
    this.finishCurrentLine();
    void this.playNext();
  };

  private handleAudioError = () => {
    this.status = 'error';
    this.error = 'This voice line could not be played.';
    this.liveAnnouncement = this.error;
    this.finishCurrentLine();
  };

  private finishCurrentLine() {
    this.currentItem = null;
    this.progress = 0;
    this.currentTimeSeconds = 0;
    this.status = this.queue.length > 0 ? 'queued' : this.status === 'error' ? 'error' : 'idle';
    this.revokeLoadedAudio();
  }

  private revokeLoadedAudio() {
    if (!this.loadedAudio) return;
    URL.revokeObjectURL(this.loadedAudio.url);
    this.loadedAudio = null;
  }
}

export const ttsStore = new ReverieTtsStore();
