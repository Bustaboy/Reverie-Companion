<script lang="ts">
  import Markdown from './Markdown.svelte';
  import { formatMessageTime } from '$lib/utils/dates';
  import type { ChatMessage } from '$lib/types/chat';

  interface Props {
    message: ChatMessage;
  }

  let { message }: Props = $props();

  const isAssistant = $derived(message.role === 'assistant');
  const isThinking = $derived(isAssistant && message.status === 'streaming' && !message.content);
</script>

<article
  class:from-user={message.role === 'user'}
  class:from-assistant={isAssistant}
  class:is-streaming={message.status === 'streaming'}
  class:is-thinking={isThinking}
  class:has-error={message.status === 'error'}
  class="message-row"
>
  <div class="avatar" aria-hidden="true">
    {isAssistant ? 'R' : 'You'}
  </div>

  <div class="bubble-shell">
    <div class="message-meta">
      <span>{isAssistant ? 'Reverie' : 'You'}</span>
      <time datetime={message.createdAt.toISOString()}>{formatMessageTime(message.createdAt)}</time>
    </div>

    <div class="bubble">
      {#if isAssistant}
        {#if message.content}
          <Markdown content={message.content} />
        {:else}
          <div class="thinking-bubble" aria-live="polite" aria-label="Reverie is thinking">
            <span aria-hidden="true"></span>
            <span aria-hidden="true"></span>
            <span aria-hidden="true"></span>
            <p>Reverie is thinking</p>
          </div>
        {/if}

        {#if message.status === 'streaming' && message.content}
          <span class="stream-cursor" aria-hidden="true"></span>
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
