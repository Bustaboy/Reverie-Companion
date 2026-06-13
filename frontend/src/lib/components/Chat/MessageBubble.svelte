<script lang="ts">
  import Markdown from './Markdown.svelte';
  import { ImageJobCard } from '$lib/components/ImageGeneration';
  import { imageGenerationStore } from '$lib/stores/imageGenerationStore.svelte';
  import { ttsStore } from '$lib/stores/ttsStore.svelte';
  import { formatMessageTime } from '$lib/utils/dates';
  import type { ChatMessage } from '$lib/types/chat';

  interface Props {
    message: ChatMessage;
  }

  let { message }: Props = $props();

  const voiceLabel = $derived.by(() => {
    const voiceId = message.tts?.resolvedVoiceId;
    if (message.tts?.voiceName) return message.tts.voiceName;
    if (!voiceId) return 'Default voice';

    return voiceId.replace(/[_-]+/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  });

  const canPlayTTS = $derived(message.role === 'assistant' && message.status !== 'streaming' && message.content.trim().length > 0);
  const canGenerateImage = $derived(message.status !== 'streaming' && message.content.trim().length > 0);
  const imageJobs = $derived(imageGenerationStore.jobsForMessage(message.id));
  const imageBusy = $derived(imageJobs.some((job) => job.status === 'queued' || job.status === 'waiting_for_resources' || job.status === 'paused' || job.status === 'running'));
  const isCurrentVoiceLine = $derived(
    ttsStore.current?.messageId === message.id &&
      (ttsStore.presenceState === 'preparing' || ttsStore.presenceState === 'speaking' || ttsStore.presenceState === 'paused')
  );

  const playMessageAudio = () => {
    ttsStore.playMessage({ messageId: message.id, visibleText: message.content, tts: message.tts, source: 'message' });
  };

  const captureMoment = () => {
    imageGenerationStore.captureFromMessage(message);
  };

  const generateImage = () => {
    imageGenerationStore.generateFromMessage(message);
  };

  const cancelImage = (jobId: string) => {
    void imageGenerationStore.cancel(jobId);
  };

  const memoryHint = $derived.by(() => {
    if (message.role !== 'assistant' || !message.memoryContext?.used) {
      return null;
    }

    const firstMemory = message.memoryContext.items?.[0]?.label;
    return firstMemory ? `Remembering ${firstMemory}` : 'Remembering what matters';
  });
</script>

<article
  class:from-user={message.role === 'user'}
  class:from-assistant={message.role === 'assistant'}
  class:is-streaming={message.status === 'streaming'}
  class:has-error={message.status === 'error'}
  class:voice-active={isCurrentVoiceLine}
  class="message-row"
  aria-label={`${message.role === 'assistant' ? 'Reverie' : 'You'} message sent ${formatMessageTime(message.createdAt)}`}
>
  <div class="avatar" aria-hidden="true">
    {message.role === 'assistant' ? 'R' : 'You'}
  </div>

  <div class="bubble-shell">
    <div class="message-meta">
      <span>{message.role === 'assistant' ? 'Reverie' : 'You'}</span>
      <time datetime={message.createdAt.toISOString()}>{formatMessageTime(message.createdAt)}</time>
      {#if canGenerateImage}
        <button
          type="button"
          class="message-image-button"
          aria-label="Capture this moment from this message"
          title="Capture this moment with character continuity"
          disabled={imageBusy}
          onclick={captureMoment}
        >
          <span aria-hidden="true">✦</span>
          <span>{imageBusy ? 'Capturing' : 'Capture this moment'}</span>
        </button>
        <button type="button" class="message-image-button legacy" aria-label="Generate a legacy image from this message" title="Legacy generic image generation" disabled={imageBusy} onclick={generateImage}>Legacy image</button>
      {/if}
      {#if canPlayTTS}
        <button
          type="button"
          class="message-voice-button"
          aria-label={`Play this message with ${voiceLabel}`}
          title={`Play with ${voiceLabel}`}
          onclick={playMessageAudio}
        >
          <span aria-hidden="true">{isCurrentVoiceLine ? '▰' : '▶'}</span>
          <span>{isCurrentVoiceLine ? ttsStore.presenceState === 'paused' ? 'Paused' : 'Speaking' : voiceLabel}</span>
        </button>
      {/if}
    </div>

    <div class="bubble" aria-live={message.status === 'streaming' ? 'polite' : undefined}>
      {#if message.role === 'assistant'}
        {#if message.content}
          <Markdown content={message.content} />
        {:else}
          <p class="soft-placeholder">Reverie is gathering her thoughts...</p>
        {/if}

        {#if message.status === 'streaming' && message.content}
          <span class="stream-cursor" aria-hidden="true"></span>
        {/if}

        {#if memoryHint}
          <p class="memory-whisper" aria-label="Reverie used a relevant memory">{memoryHint}</p>
        {/if}

        {#if message.status === 'error' && message.error}
          <p class="message-error">{message.error}</p>
        {/if}
      {:else}
        <p>{message.content}</p>
      {/if}

      {#if imageJobs.length > 0}
        <div class="message-image-stack" aria-live="polite">
          {#each imageJobs as job (job.job_id)}
            <ImageJobCard
              {job}
              onCancel={() => cancelImage(job.job_id)}
              onRetry={() => imageGenerationStore.regenerate(job)}
              onVary={() => imageGenerationStore.vary(job)}
              onSave={() => imageGenerationStore.saveToCharacterAssets(job)}
              onDelete={() => imageGenerationStore.deleteImage(job.job_id)}
            />
          {/each}
        </div>
      {/if}
    </div>
  </div>
</article>
