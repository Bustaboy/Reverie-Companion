<script lang="ts">
  import type { ChatMessage } from '$lib/types/chat';
  import { renderAssistantMarkdown } from '$lib/utils/markdown';

  interface Props {
    message: ChatMessage;
  }

  let { message }: Props = $props();

  const formatTime = (date: Date) =>
    new Intl.DateTimeFormat(undefined, {
      hour: 'numeric',
      minute: '2-digit'
    }).format(date);
</script>

<article class:from-user={message.role === 'user'} class="message-row">
  <div class="message-meta" aria-hidden="true">
    <span class="speaker">{message.role === 'user' ? 'You' : 'Reverie'}</span>
    <time>{formatTime(message.createdAt)}</time>
  </div>

  <div class="message-bubble">
    {#if message.role === 'assistant'}
      <div class="markdown-body">{@html renderAssistantMarkdown(message.content)}</div>
    {:else}
      <p>{message.content}</p>
    {/if}
  </div>
</article>
