<script lang="ts">
  import Markdown from './Markdown.svelte';
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

  const playMessageAudio = () => {
    ttsStore.playMessage({ messageId: message.id, visibleText: message.content, tts: message.tts, source: 'message' });
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
  class="message-row"
>
  <div class="avatar" aria-hidden="true">
    {message.role === 'assistant' ? 'R' : 'You'}
  </div>

  <div class="bubble-shell">
    <div class="message-meta">
      <span>{message.role === 'assistant' ? 'Reverie' : 'You'}</span>
      <time datetime={message.createdAt.toISOString()}>{formatMessageTime(message.createdAt)}</time>
      {#if canPlayTTS}
        <button
          type="button"
          class="message-voice-button"
          aria-label={`Play this message with ${voiceLabel}`}
          title={`Play with ${voiceLabel}`}
          onclick={playMessageAudio}
        >
          <span aria-hidden="true">▶</span>
          <span>{voiceLabel}</span>
        </button>
      {/if}
    </div>

    <div class="bubble">
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
    </div>
  </div>
</article>
