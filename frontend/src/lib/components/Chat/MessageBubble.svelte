<script lang="ts">
  import Markdown from './Markdown.svelte';
  import { formatMessageTime } from '$lib/utils/dates';
  import type { ChatMessage } from '$lib/types/chat';

  interface Props {
    message: ChatMessage;
    onDismissGrowthNotification?: (notificationId: string) => void;
    onDisableGrowthNotifications?: () => void;
  }

  let { message, onDismissGrowthNotification, onDisableGrowthNotifications }: Props = $props();

  const dismissGrowthNotification = () => {
    if (message.growthNotification) {
      onDismissGrowthNotification?.(message.growthNotification.id);
    }
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
  class:from-system={message.role === 'system'}
  class:is-streaming={message.status === 'streaming'}
  class:has-error={message.status === 'error'}
  class="message-row"
>
  <div class="avatar" aria-hidden="true">
    {message.role === 'assistant' ? 'R' : message.role === 'system' ? '✦' : 'You'}
  </div>

  <div class="bubble-shell">
    <div class="message-meta">
      <span>{message.role === 'assistant' ? 'Reverie' : message.role === 'system' ? 'Growth whisper' : 'You'}</span>
      <time datetime={message.createdAt.toISOString()}>{formatMessageTime(message.createdAt)}</time>
    </div>

    <div class="bubble">
      {#if message.role === 'system' && message.growthNotification}
        <div class="growth-notification" role="status" aria-live="polite">
          <div>
            <span class="growth-kicker">Quiet growth</span>
            <p>{message.growthNotification.text}</p>
          </div>
          <div class="growth-actions">
            <button type="button" aria-label="Dismiss growth whisper" onclick={dismissGrowthNotification}>Dismiss</button>
            <button type="button" aria-label="Hide future growth whispers" onclick={onDisableGrowthNotifications}>Hide these</button>
          </div>
        </div>
      {:else if message.role === 'assistant'}
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
