import { browser } from '$app/environment';
import { settingsStore } from '$lib/stores/settingsStore';
import { TTSServiceError, ttsService, type TTSStreamEvent } from '$lib/api/ttsService';
import type { MessageTTSMetadata, TTSEmotionMetadata, TTSContextMetadata } from '$lib/types/chat';

export type TTSPlaybackState = 'idle' | 'queued' | 'loading' | 'playing' | 'paused' | 'error';
export type TTSPresenceState = 'off' | 'ready' | 'queued' | 'preparing' | 'speaking' | 'paused' | 'error';

export interface TTSQueueItem {
  id: string;
  messageId?: string;
  text: string;
  visibleText?: string;
  voiceId?: string;
  voiceName?: string;
  ttsContext?: TTSContextMetadata;
  emotion?: TTSEmotionMetadata;
  source: 'auto' | 'message' | 'vn';
  interrupt?: boolean;
}

interface ActiveAudio {
  element: HTMLAudioElement;
  objectUrl: string;
  item: TTSQueueItem;
}

const MAX_QUEUE_LENGTH = 3;
const PROGRESS_TIMER_MS = 250;
const FRONTEND_TTS_TEXT_SOFT_LIMIT = 1_800;

const toFriendlyVoiceName = (voiceId?: string, voiceName?: string): string => {
  if (voiceName?.trim()) return voiceName.trim();
  if (!voiceId?.trim()) return 'Default Reverie voice';

  return voiceId
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
};

const clamp = (value: number, min: number, max: number): number => Math.min(max, Math.max(min, value));

const clipForSpeech = (text: string): { text: string; clipped: boolean } => {
  const normalized = text.trim().replace(/\s+/g, ' ');
  if (normalized.length <= FRONTEND_TTS_TEXT_SOFT_LIMIT) {
    return { text: normalized, clipped: false };
  }

  const boundary = Math.max(
    normalized.lastIndexOf('.', FRONTEND_TTS_TEXT_SOFT_LIMIT),
    normalized.lastIndexOf('!', FRONTEND_TTS_TEXT_SOFT_LIMIT),
    normalized.lastIndexOf('?', FRONTEND_TTS_TEXT_SOFT_LIMIT)
  );
  const cutAt = boundary > FRONTEND_TTS_TEXT_SOFT_LIMIT * 0.55 ? boundary + 1 : FRONTEND_TTS_TEXT_SOFT_LIMIT;
  return { text: `${normalized.slice(0, cutAt).trim()} …`, clipped: true };
};

const normalizeAudioError = (error: unknown): string => {
  if (error instanceof TTSServiceError && error.code === 'tts_cancelled') {
    return 'Speech playback was cancelled.';
  }

  if (error instanceof TTSServiceError) {
    if (error.code === 'tts_backend_unavailable') {
      return 'No local voice backend is available right now. Text chat is safe; check Orpheus/Piper paths or let Piper handle fallback.';
    }
    if (error.code === 'tts_text_too_long') {
      return 'That reply is too long for one local voice line. Reverie kept the text intact; try a shorter passage.';
    }
    if (error.retryable) {
      return `${error.message} You can try again in a moment.`;
    }
    return error.message;
  }

  return 'Reverie could not play that voice line. Text chat is still available.';
};


type TTSBufferHealth = 'idle' | 'prebuffering' | 'healthy' | 'low' | 'rebuffering' | 'buffered-fallback';
type StreamPushStatus = 'prebuffering' | 'started' | 'streamed' | 'buffered' | 'rebuffering';

const STREAM_PREBUFFER_SECONDS = 0.7;
const STREAM_LOW_BUFFER_SECONDS = 0.25;
const STREAM_REBUFFER_SECONDS = 0.6;
const STREAM_SCHEDULE_JITTER_SECONDS = 0.04;

class ProgressiveAudioSink {
  private readonly context: AudioContext;
  private nextStartTime = 0;
  private playbackStartTime = 0;
  private scheduledSeconds = 0;
  private pendingSeconds = 0;
  private playbackStarted = false;
  private didRebuffer = false;
  private sources: AudioBufferSourceNode[] = [];
  private pendingPcmBuffers: AudioBuffer[] = [];
  private format: string | null = null;
  private chunks: Uint8Array[] = [];

  constructor(private readonly volume: number, private readonly speed: number) {
    const audioGlobal = globalThis as typeof globalThis & { webkitAudioContext?: typeof AudioContext };
    const AudioContextConstructor = audioGlobal.AudioContext ?? audioGlobal.webkitAudioContext;
    if (!AudioContextConstructor) throw new Error('Web Audio is unavailable.');
    this.context = new AudioContextConstructor();
  }

  async push(bytes: Uint8Array, event: Extract<TTSStreamEvent, { type: 'chunk' }>): Promise<StreamPushStatus> {
    this.format = event.audio_format;
    if (event.audio_format !== 'pcm') {
      this.chunks.push(bytes);
      return 'buffered';
    }

    if (this.context.state === 'suspended') await this.context.resume();
    const buffer = this.toPcmBuffer(bytes, event.sample_rate);

    if (!this.playbackStarted) {
      this.pendingPcmBuffers.push(buffer);
      this.pendingSeconds += this.adjustedDuration(buffer);
      if (this.pendingSeconds < STREAM_PREBUFFER_SECONDS) {
        return 'prebuffering';
      }

      this.playbackStarted = true;
      this.flushPendingBuffers(this.context.currentTime + STREAM_SCHEDULE_JITTER_SECONDS);
      return 'started';
    }

    const status: StreamPushStatus = this.remainingSeconds < STREAM_LOW_BUFFER_SECONDS ? 'rebuffering' : 'streamed';
    const earliestStart = this.context.currentTime + (status === 'rebuffering' ? STREAM_REBUFFER_SECONDS : STREAM_SCHEDULE_JITTER_SECONDS);
    this.scheduleBuffer(buffer, Math.max(this.nextStartTime, earliestStart));
    if (status === 'rebuffering') this.didRebuffer = true;
    return status;
  }

  get remainingSeconds() {
    if (!this.playbackStarted) return this.pendingSeconds;
    return Math.max(0, this.nextStartTime - this.context.currentTime);
  }

  get elapsedSeconds() {
    if (!this.playbackStarted) return 0;
    return Math.max(0, this.context.currentTime - this.playbackStartTime);
  }

  get estimatedDurationSeconds() {
    return this.scheduledSeconds + this.pendingSeconds;
  }

  get health(): TTSBufferHealth {
    if (this.chunks.length > 0) return 'buffered-fallback';
    if (!this.playbackStarted) return 'prebuffering';
    if (this.remainingSeconds < STREAM_LOW_BUFFER_SECONDS) return this.didRebuffer ? 'rebuffering' : 'low';
    return 'healthy';
  }

  startPendingPcm(): boolean {
    if (this.chunks.length > 0 || this.playbackStarted || this.pendingPcmBuffers.length === 0) return false;
    this.playbackStarted = true;
    this.flushPendingBuffers(this.context.currentTime + STREAM_SCHEDULE_JITTER_SECONDS);
    return true;
  }

  toObjectUrl(fallbackFormat = 'wav'): string | null {
    if (this.chunks.length === 0) return null;
    const totalBytes = this.chunks.reduce((total, chunk) => total + chunk.byteLength, 0);
    const merged = new Uint8Array(totalBytes);
    let offset = 0;
    for (const chunk of this.chunks) {
      merged.set(chunk, offset);
      offset += chunk.byteLength;
    }
    return URL.createObjectURL(new Blob([merged], { type: `audio/${this.format ?? fallbackFormat}` }));
  }

  stop() {
    for (const source of this.sources) {
      try {
        source.stop();
      } catch {
        // Already stopped by the browser audio graph.
      }
    }
    this.sources = [];
    if (this.context.state !== 'closed') void this.context.close();
  }

  private toPcmBuffer(bytes: Uint8Array, sampleRate: number): AudioBuffer {
    const samples = new Float32Array(Math.floor(bytes.byteLength / 2));
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    for (let index = 0; index < samples.length; index += 1) {
      samples[index] = view.getInt16(index * 2, true) / 32768;
    }

    const buffer = this.context.createBuffer(1, samples.length, sampleRate);
    buffer.copyToChannel(samples, 0);
    return buffer;
  }

  private flushPendingBuffers(startAt: number) {
    let scheduledAt = startAt;
    for (const buffer of this.pendingPcmBuffers) {
      scheduledAt = this.scheduleBuffer(buffer, scheduledAt);
    }
    this.pendingPcmBuffers = [];
    this.pendingSeconds = 0;
  }

  private scheduleBuffer(buffer: AudioBuffer, startAt: number): number {
    const source = this.context.createBufferSource();
    const gain = this.context.createGain();
    source.buffer = buffer;
    source.playbackRate.value = clamp(this.speed, 0.75, 1.35);
    gain.gain.value = clamp(this.volume, 0, 1);
    source.connect(gain).connect(this.context.destination);

    source.start(startAt);
    const adjustedDuration = this.adjustedDuration(buffer);
    if (this.playbackStartTime === 0) this.playbackStartTime = startAt;
    this.nextStartTime = startAt + adjustedDuration;
    this.scheduledSeconds += adjustedDuration;
    this.sources.push(source);
    source.onended = () => {
      this.sources = this.sources.filter((candidate) => candidate !== source);
    };
    return this.nextStartTime;
  }

  private adjustedDuration(buffer: AudioBuffer): number {
    return buffer.duration / clamp(this.speed, 0.75, 1.35);
  }
}

class TTSStore {
  enabled = $state(settingsStore.getSnapshot().ttsEnabled);
  autoPlay = $state(settingsStore.getSnapshot().ttsAutoPlay);
  volume = $state(settingsStore.getSnapshot().ttsVolume);
  speed = $state(settingsStore.getSnapshot().ttsSpeed);
  latencyPreset = $state(settingsStore.getSnapshot().ttsLatencyPreset);
  playbackState = $state<TTSPlaybackState>('idle');
  queue = $state<TTSQueueItem[]>([]);
  current = $state<TTSQueueItem | null>(null);
  currentTime = $state(0);
  duration = $state(0);
  error = $state<string | null>(null);
  announcement = $state('Speech is ready.');
  streamedChunks = $state(0);
  bufferHealth = $state<TTSBufferHealth>('idle');
  bufferedSeconds = $state(0);

  private activeAudio: ActiveAudio | null = null;
  private activeSink: ProgressiveAudioSink | null = null;
  private generationController: AbortController | null = null;
  private progressTimer: ReturnType<typeof globalThis.setInterval> | null = null;
  private runToken = 0;

  constructor() {
    settingsStore.subscribe((settings) => {
      this.enabled = settings.ttsEnabled;
      this.autoPlay = settings.ttsAutoPlay;
      this.volume = settings.ttsVolume;
      this.speed = settings.ttsSpeed;
      this.latencyPreset = settings.ttsLatencyPreset;
      this.applyPlaybackSettings();

      if (!settings.ttsEnabled) {
        this.cancel('Speech is disabled.');
      }
    });
  }

  get isBusy() {
    return this.playbackState === 'loading' || this.playbackState === 'playing' || this.playbackState === 'paused';
  }

  get isSpeaking() {
    return this.playbackState === 'playing' || this.playbackState === 'loading';
  }

  get progress() {
    return this.duration > 0 ? clamp(this.currentTime / this.duration, 0, 1) : 0;
  }

  get currentVoiceName() {
    return toFriendlyVoiceName(this.current?.voiceId, this.current?.voiceName);
  }

  get presenceState(): TTSPresenceState {
    if (!this.enabled) return 'off';
    if (this.error || this.playbackState === 'error') return 'error';
    if (this.playbackState === 'loading') return 'preparing';
    if (this.playbackState === 'playing') return 'speaking';
    if (this.playbackState === 'paused') return 'paused';
    if (this.playbackState === 'queued' || this.queue.length > 0) return 'queued';
    return 'ready';
  }

  get presenceLabel() {
    switch (this.presenceState) {
      case 'off':
        return 'Voice off';
      case 'preparing':
        return `Voice warming · ${this.currentVoiceName}`;
      case 'speaking':
        return `Speaking · ${this.currentVoiceName}`;
      case 'paused':
        return `Voice paused · ${this.currentVoiceName}`;
      case 'queued':
        return `${this.queue.length} voice line${this.queue.length === 1 ? '' : 's'} queued`;
      case 'error':
        return 'Voice needs attention';
      default:
        return 'Voice ready';
    }
  }

  get queueCount() {
    return this.queue.length;
  }

  setEnabled(enabled: boolean) {
    settingsStore.setTTSEnabled(enabled);
  }

  setAutoPlay(autoPlay: boolean) {
    settingsStore.setTTSAutoPlay(autoPlay);
  }

  setVolume(volume: number) {
    settingsStore.setTTSVolume(volume);
  }

  setSpeed(speed: number) {
    settingsStore.setTTSSpeed(speed);
  }

  enqueueFromDone(input: {
    messageId: string;
    visibleText: string;
    tts?: MessageTTSMetadata;
    source?: 'auto' | 'vn';
    interrupt?: boolean;
  }) {
    if (!this.enabled || !this.autoPlay || !input.visibleText.trim()) {
      return;
    }

    this.enqueue({
      id: `tts-${input.messageId}-${Date.now()}`,
      messageId: input.messageId,
      text: input.tts?.ttsText ?? input.visibleText,
      visibleText: input.visibleText,
      voiceId: input.tts?.resolvedVoiceId,
      voiceName: input.tts?.voiceName,
      ttsContext: input.tts?.ttsContext,
      emotion: input.tts?.emotion,
      source: input.source ?? 'auto',
      interrupt: input.interrupt ?? true
    });
  }

  playMessage(input: { messageId: string; visibleText: string; tts?: MessageTTSMetadata; source?: 'message' | 'vn' }) {
    if (!input.visibleText.trim()) {
      return;
    }

    this.enqueue({
      id: `tts-manual-${input.messageId}-${Date.now()}`,
      messageId: input.messageId,
      text: input.tts?.ttsText ?? input.visibleText,
      visibleText: input.visibleText,
      voiceId: input.tts?.resolvedVoiceId,
      voiceName: input.tts?.voiceName,
      ttsContext: input.tts?.ttsContext,
      emotion: input.tts?.emotion,
      source: input.source ?? 'message',
      interrupt: true
    });
  }

  enqueue(item: TTSQueueItem) {
    const clippedSpeech = clipForSpeech(item.text);
    if (!this.enabled || !clippedSpeech.text) {
      return;
    }

    if (item.interrupt) {
      this.stopActiveAudio({ clearQueue: true, announce: false });
    }

    this.error = null;
    const clippedVisibleSpeech = item.visibleText ? clipForSpeech(item.visibleText) : null;
    const queuedItem = {
      ...item,
      text: clippedSpeech.text,
      visibleText: clippedVisibleSpeech?.text ?? item.visibleText
    };
    const withoutDuplicateMessage = queuedItem.messageId
      ? this.queue.filter((candidate) => candidate.messageId !== queuedItem.messageId)
      : this.queue;
    this.queue = [...withoutDuplicateMessage, queuedItem].slice(-MAX_QUEUE_LENGTH);
    this.announcement = clippedSpeech.clipped
      ? `Queued the first part of this long reply with ${toFriendlyVoiceName(item.voiceId, item.voiceName)}.`
      : `Queued speech with ${toFriendlyVoiceName(item.voiceId, item.voiceName)}.`;

    if (this.playbackState === 'idle' || this.playbackState === 'error') {
      void this.playNext();
    } else if (this.playbackState !== 'playing' && this.playbackState !== 'paused' && this.playbackState !== 'loading') {
      this.playbackState = 'queued';
    }
  }

  async play() {
    if (!this.enabled) {
      this.error = 'Speech is disabled in settings.';
      this.playbackState = 'error';
      return;
    }

    if (this.activeAudio) {
      await this.activeAudio.element.play();
      this.playbackState = 'playing';
      this.announcement = `Speaking with ${this.currentVoiceName}.`;
      this.startProgressTimer();
      return;
    }

    if (this.queue.length > 0) {
      await this.playNext();
    }
  }

  pause() {
    if (this.activeAudio && this.playbackState === 'playing') {
      this.activeAudio.element.pause();
      this.playbackState = 'paused';
      this.announcement = 'Speech paused.';
      this.stopProgressTimer();
      this.updateProgressFromAudio();
      return;
    }

    if (this.activeSink && this.playbackState === 'playing') {
      this.stopActiveAudio({ clearQueue: false, announce: false });
      this.announcement = 'Speech stream paused.';
    }
  }

  stop() {
    this.stopActiveAudio({ clearQueue: false, announce: true });
  }

  cancel(reason = 'Speech playback cancelled.') {
    this.stopActiveAudio({ clearQueue: true, announce: false });
    this.error = null;
    this.announcement = reason;
  }

  clearError() {
    this.error = null;
    if (this.playbackState === 'error') {
      this.playbackState = this.queue.length > 0 ? 'queued' : 'idle';
    }
  }

  private async playNext() {
    if (!browser || !this.enabled || this.queue.length === 0) {
      this.playbackState = this.queue.length > 0 ? 'queued' : 'idle';
      return;
    }

    const [nextItem, ...remainingQueue] = this.queue;
    const token = (this.runToken += 1);
    this.queue = remainingQueue;
    this.current = nextItem;
    this.currentTime = 0;
    this.duration = 0;
    this.error = null;
    this.playbackState = 'loading';
    this.announcement = `Preparing ${toFriendlyVoiceName(nextItem.voiceId, nextItem.voiceName)}.`;

    this.generationController?.abort();
    const controller = new AbortController();
    this.generationController = controller;

    try {
      const sink = new ProgressiveAudioSink(this.volume, this.speed);
      this.activeSink = sink;
      let streamedProgressively = false;
      let fallbackObjectUrl: string | null = null;
      let doneAudioFormat = 'wav';
      let doneVoiceId = nextItem.voiceId;
      this.streamedChunks = 0;
      this.bufferHealth = 'idle';
      this.bufferedSeconds = 0;

      await ttsService.streamSpeech(
        {
          text: nextItem.visibleText ?? nextItem.text,
          tts_text: nextItem.text,
          voice_id: nextItem.voiceId,
          context: nextItem.ttsContext
            ? {
                character_id: nextItem.ttsContext.characterId,
                is_narration: nextItem.ttsContext.isNarration,
                mode: nextItem.ttsContext.mode,
                emotion_hint: nextItem.ttsContext.emotionHint,
                intensity: nextItem.ttsContext.intensity,
                mood_settings: nextItem.ttsContext.moodSettings,
                scene_tags: nextItem.ttsContext.sceneTags
              }
            : undefined,
          emotion: nextItem.emotion
        },
        {
          onStart: () => {
            this.announcement = `Starting voice stream with ${toFriendlyVoiceName(nextItem.voiceId, nextItem.voiceName)}.`;
          },
          onChunk: async (event, bytes) => {
            if (token !== this.runToken || controller.signal.aborted) return;
            this.streamedChunks = event.sequence;
            const mode = await sink.push(bytes, event);
            this.bufferedSeconds = sink.remainingSeconds;
            this.bufferHealth = sink.health;

            if ((mode === 'started' || mode === 'streamed') && !streamedProgressively) {
              streamedProgressively = true;
              this.playbackState = 'playing';
              this.announcement = `Speaking with ${toFriendlyVoiceName(event.voice_id ?? nextItem.voiceId, nextItem.voiceName)}.`;
              this.startProgressTimer();
            } else if (mode === 'prebuffering') {
              this.playbackState = 'loading';
              this.announcement = `Pre-buffering voice… ${sink.remainingSeconds.toFixed(1)}s ready.`;
            } else if (mode === 'rebuffering') {
              this.announcement = 'Voice stream is catching up to avoid stutter.';
            } else if (!streamedProgressively) {
              this.announcement = `Receiving voice audio… ${event.sequence} chunk${event.sequence === 1 ? '' : 's'}.`;
            }
          },
          onDone: (event) => {
            doneAudioFormat = event.audio_format;
            doneVoiceId = event.voice_id;
            this.duration = event.duration_seconds ?? Math.max(this.duration, sink.estimatedDurationSeconds);
            this.bufferedSeconds = sink.remainingSeconds;
            this.bufferHealth = sink.health;
          }
        },
        { signal: controller.signal }
      );

      if (token !== this.runToken || controller.signal.aborted) {
        sink.stop();
        return;
      }

      const flushedShortStream = sink.startPendingPcm();
      if (flushedShortStream && !streamedProgressively) {
        streamedProgressively = true;
        this.playbackState = 'playing';
        this.announcement = `Speaking with ${toFriendlyVoiceName(doneVoiceId ?? nextItem.voiceId, nextItem.voiceName)}.`;
        this.startProgressTimer();
      }

      fallbackObjectUrl = sink.toObjectUrl(doneAudioFormat);
      if (fallbackObjectUrl) {
        const element = new Audio(fallbackObjectUrl);
        this.activeAudio = { element, objectUrl: fallbackObjectUrl, item: nextItem };
        this.applyPlaybackSettings();
        element.onloadedmetadata = () => {
          this.duration = Number.isFinite(element.duration) ? element.duration : this.duration;
        };
        element.ontimeupdate = () => this.updateProgressFromAudio();
        element.onerror = () => {
          this.error = 'The generated voice audio could not be played.';
          this.playbackState = 'error';
          this.cleanupActiveAudio();
        };
        element.onended = () => this.finishCurrentLine();
        await element.play();
        this.playbackState = 'playing';
        this.announcement = `Speaking with ${toFriendlyVoiceName(doneVoiceId ?? nextItem.voiceId, nextItem.voiceName)}.`;
        this.startProgressTimer();
      } else {
        const finishDelayMs = Math.max(250, sink.remainingSeconds * 1000 + 120);
        globalThis.setTimeout(() => {
          if (token === this.runToken) {
            this.finishCurrentLine();
            return;
          }
          sink.stop();
        }, finishDelayMs);
      }
    } catch (error) {
      if (token !== this.runToken) {
        return;
      }

      this.activeSink?.stop();
      this.activeSink = null;
      this.cleanupActiveAudio();
      this.error = normalizeAudioError(error);
      this.playbackState = 'error';
      this.announcement = this.error;
    } finally {
      if (this.generationController === controller) {
        this.generationController = null;
      }
    }
  }

  private applyPlaybackSettings() {
    if (!this.activeAudio) return;

    this.activeAudio.element.volume = clamp(this.volume, 0, 1);
    this.activeAudio.element.playbackRate = clamp(this.speed, 0.75, 1.35);
  }

  private updateProgressFromAudio() {
    if (this.activeAudio) {
      const { element } = this.activeAudio;
      this.currentTime = Number.isFinite(element.currentTime) ? element.currentTime : 0;
      this.duration = Number.isFinite(element.duration) ? element.duration : this.duration;
      return;
    }

    if (this.activeSink) {
      this.currentTime = this.activeSink.elapsedSeconds;
      this.duration = Math.max(this.duration, this.activeSink.estimatedDurationSeconds);
      this.bufferedSeconds = this.activeSink.remainingSeconds;
      this.bufferHealth = this.activeSink.health;
      if (this.bufferHealth === 'low') {
        this.announcement = 'Voice buffer is low; smoothing playback.';
      } else if (this.bufferHealth === 'rebuffering') {
        this.announcement = 'Voice stream is catching up to avoid stutter.';
      }
    }
  }

  private startProgressTimer() {
    this.stopProgressTimer();
    this.progressTimer = globalThis.setInterval(() => this.updateProgressFromAudio(), PROGRESS_TIMER_MS);
  }

  private stopProgressTimer() {
    if (!this.progressTimer) return;

    globalThis.clearInterval(this.progressTimer);
    this.progressTimer = null;
  }

  private stopActiveAudio(options: { clearQueue: boolean; announce: boolean }) {
    this.runToken += 1;
    this.generationController?.abort();
    this.generationController = null;

    if (this.activeAudio) {
      this.activeAudio.element.pause();
      this.activeAudio.element.currentTime = 0;
    }

    this.activeSink?.stop();
    this.activeSink = null;
    this.cleanupActiveAudio();

    if (options.clearQueue) {
      this.queue = [];
    }

    this.current = null;
    this.currentTime = 0;
    this.duration = 0;
    this.bufferHealth = 'idle';
    this.bufferedSeconds = 0;
    this.playbackState = this.queue.length > 0 ? 'queued' : 'idle';

    if (options.announce) {
      this.announcement = 'Speech stopped.';
    }
  }

  private finishCurrentLine() {
    this.updateProgressFromAudio();
    this.activeSink?.stop();
    this.activeSink = null;
    this.cleanupActiveAudio();
    this.playbackState = this.queue.length > 0 ? 'queued' : 'idle';
    this.announcement = this.queue.length > 0 ? 'Continuing queued speech.' : 'Speech finished.';
    void this.playNext();
  }

  private cleanupActiveAudio() {
    this.stopProgressTimer();

    if (!this.activeAudio) return;

    this.activeAudio.element.onloadedmetadata = null;
    this.activeAudio.element.ontimeupdate = null;
    this.activeAudio.element.onended = null;
    this.activeAudio.element.onerror = null;
    URL.revokeObjectURL(this.activeAudio.objectUrl);
    this.activeAudio = null;
  }
}

export const ttsStore = new TTSStore();
