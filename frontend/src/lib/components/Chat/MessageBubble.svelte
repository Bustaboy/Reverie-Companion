<script lang="ts">
  import Markdown from './Markdown.svelte';
  import { formatMessageTime } from '$lib/utils/dates';
  import type { ChatMessage } from '$lib/types/chat';

  interface Props {
    message: ChatMessage;
  }

  let { message }: Props = $props();
</script>

<article class:from-user={message.role === 'user'} class:from-assistant={message.role === 'assistant'} class="message-row">
  <div class="avatar" aria-hidden="true">
    {message.role === 'assistant' ? 'R' : 'You'}
  </div>

  <div class="bubble-shell">
    <div class="message-meta">
      <span>{message.role === 'assistant' ? 'Reverie' : 'You'}</span>
      <time datetime={message.createdAt.toISOString()}>{formatMessageTime(message.createdAt)}</time>
    </div>

    <div class="bubble">
      {#if message.role === 'assistant'}
        <Markdown content={message.content} />
      {:else}
        <p>{message.content}</p>
      {/if}
    </div>
  </div>
</article>
