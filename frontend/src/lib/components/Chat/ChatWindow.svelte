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

  const dismissGrowthNotification = () => {
    chatStore.dismissGrowthNotification();
  };

  const disableGrowthNotifications = () => {
    chatStore.disableGrowthNotifications();
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

  {#if $chatStore.growthNotification}
    <aside class="growth-notification" role="status" aria-live="polite">
      <span class="growth-orb" aria-hidden="true">✦</span>
      <div>
        <strong>A quiet sign of growth</strong>
        <p>{$chatStore.growthNotification.message}</p>
        {#if $chatStore.growthNotification.why}
          <small>{$chatStore.growthNotification.why}</small>
        {/if}
      </div>
      <div class="growth-actions" aria-label="Growth notification controls">
        <button type="button" onclick={dismissGrowthNotification}>Dismiss</button>
        <button type="button" class="subtle" onclick={disableGrowthNotifications}>Hide future notes</button>
      </div>
    </aside>
  {/if}

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
