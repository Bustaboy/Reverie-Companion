<script lang="ts">
  import MessageInput from './MessageInput.svelte';
  import MessageList from './MessageList.svelte';
  import { chatStore } from '$lib/stores/chatStore';

  const handleSend = (content: string) => {
    void chatStore.sendMessage(content);
  };

  const isGenerating = $derived($chatStore.generationState !== 'idle');
  const statusLabel = $derived(
    $chatStore.generationState === 'idle'
      ? 'Local backend ready'
      : $chatStore.generationState === 'thinking'
        ? 'Reverie is thinking'
        : 'Reverie is responding'
  );
</script>

<section class="chat-window" aria-label="Reverie chat">
  <header class="chat-header">
    <div>
      <p class="eyebrow">Private local session</p>
      <h1>Reverie</h1>
      <p class="subtitle">A warm, offline companion interface built for long conversations.</p>
    </div>

    <div class:streaming={isGenerating} class="status-pill" aria-label="Companion status">
      <span></span>
      {statusLabel}
    </div>
  </header>

  {#if $chatStore.error}
    <div class="chat-notice" role="status" aria-live="polite">
      <div>
        <strong>Reverie lost the thread for a moment.</strong>
        <span>{$chatStore.error}</span>
      </div>
      <button type="button" onclick={() => chatStore.clearError()} aria-label="Dismiss connection notice">Dismiss</button>
    </div>
  {/if}

  <MessageList messages={$chatStore.messages} generationState={$chatStore.generationState} />
  <MessageInput onSend={handleSend} disabled={isGenerating} />
</section>
