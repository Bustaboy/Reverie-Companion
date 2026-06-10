<script lang="ts">
  import { marked } from 'marked';
  import type { ChatMessage } from '$lib/types/chat';

  export let message: ChatMessage;

  $: timestamp = new Intl.DateTimeFormat('en', {
    hour: 'numeric',
    minute: '2-digit'
  }).format(message.createdAt);

  function escapeHtml(content: string) {
    return content
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;');
  }

  $: renderedAssistantContent = marked.parse(escapeHtml(message.content), {
    async: false,
    breaks: true,
    gfm: true
  }) as string;
</script>

<article class:user={message.role === 'user'} class:assistant={message.role === 'assistant'} class="message-row">
  <div class="bubble">
    <div class="message-meta">
      <span>{message.role === 'user' ? 'You' : 'Seraphina'}</span>
      <time datetime={message.createdAt.toISOString()}>{timestamp}</time>
    </div>

    {#if message.role === 'assistant'}
      <div class="markdown-content">{@html renderedAssistantContent}</div>
    {:else}
      <p class="plain-content">{message.content}</p>
    {/if}
  </div>
</article>

<style>
  .message-row {
    display: flex;
    width: 100%;
  }

  .message-row.user {
    justify-content: flex-end;
  }

  .message-row.assistant {
    justify-content: flex-start;
  }

  .bubble {
    width: min(42rem, 82%);
    padding: 0.95rem 1rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 1.2rem;
    box-shadow: 0 18px 45px rgba(0, 0, 0, 0.18);
  }

  .assistant .bubble {
    border-top-left-radius: 0.35rem;
    background: rgba(255, 255, 255, 0.07);
  }

  .user .bubble {
    border-color: rgba(255, 176, 143, 0.24);
    border-top-right-radius: 0.35rem;
    background: linear-gradient(135deg, rgba(236, 113, 98, 0.3), rgba(124, 86, 255, 0.22));
  }

  .message-meta {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.45rem;
    color: #b7a8b7;
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 0.02em;
  }

  .user .message-meta {
    color: #ffe4da;
  }

  time {
    color: rgba(255, 255, 255, 0.48);
    font-weight: 500;
  }

  .plain-content,
  :global(.markdown-content p) {
    margin: 0;
  }

  .plain-content,
  .markdown-content {
    color: #fff8f4;
    font-size: 0.98rem;
    line-height: 1.68;
  }

  :global(.markdown-content p + p) {
    margin-top: 0.75rem;
  }

  :global(.markdown-content strong) {
    color: #ffe4d6;
  }

  :global(.markdown-content em) {
    color: #ffd2c2;
  }

  :global(.markdown-content ul),
  :global(.markdown-content ol) {
    margin: 0.6rem 0 0;
    padding-left: 1.25rem;
  }

  :global(.markdown-content code) {
    padding: 0.12rem 0.32rem;
    border-radius: 0.4rem;
    background: rgba(0, 0, 0, 0.26);
    color: #ffd4c6;
  }

  @media (max-width: 680px) {
    .bubble {
      width: 100%;
    }
  }
</style>
