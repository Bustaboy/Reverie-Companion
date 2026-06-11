<script lang="ts">
  import MessageInput from './MessageInput.svelte';
  import MessageList from './MessageList.svelte';
  import { chatStore } from '$lib/stores/chatStore';

  const handleSend = (content: string) => {
    void chatStore.sendMessage(content);
  };

  const statusLabel = $derived(
    $chatStore.generationState === 'idle' ? 'Local backend ready' : 'Reverie is responding'
  );

  const dismissError = () => {
    chatStore.clearError();
  };
</script>

<section class="chat-window" aria-label="Reverie chat">
  <header class="chat-header">
    <div>
      <p class="eyebrow">Private local session</p>
      <h1>Reverie</h1>
      <p class="subtitle">A warm, offline companion interface built for long conversations.</p>
    </div>

    <div class:streaming={$chatStore.generationState !== 'idle'} class="status-pill" aria-label="Companion status">
      <span></span>
      {statusLabel}
    </div>
  </header>

  <MessageList messages={$chatStore.messages} generationState={$chatStore.generationState} />

  {#if $chatStore.error}
    <div class="chat-error-banner" role="status" aria-live="polite">
      <div>
        <strong>Reverie paused for a moment.</strong>
        <span>{$chatStore.error}</span>
      </div>
      <button type="button" aria-label="Dismiss connection message" onclick={dismissError}>Close</button>
    </div>
  {/if}

  <MessageInput onSend={handleSend} disabled={$chatStore.generationState !== 'idle'} />
</section>
