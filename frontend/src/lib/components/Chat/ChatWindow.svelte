<script lang="ts">
  import MessageInput from './MessageInput.svelte';
  import { CharacterSelector } from '$lib/components/Characters';
  import { AudioPlayer } from '$lib/components/TTS';
  import MessageList from './MessageList.svelte';
  import { chatStore } from '$lib/stores/chatStore';
  import { imageGenerationStore } from '$lib/stores/imageGenerationStore.svelte';
  import { ttsStore } from '$lib/stores/ttsStore.svelte';

  const handleSend = (content: string) => {
    void chatStore.sendMessage(content);
  };

  const statusLabel = $derived.by(() => {
    if ($chatStore.generationState !== 'idle') return 'Reverie is responding';
    if (imageGenerationStore.isBusy) return imageGenerationStore.statusLabel;
    if (ttsStore.presenceState === 'speaking' || ttsStore.presenceState === 'preparing') return ttsStore.presenceLabel;
    return 'Local backend ready';
  });

  const dismissError = () => {
    chatStore.clearError();
  };

  const visualizeLatest = () => {
    imageGenerationStore.generateFromLatestMessage($chatStore.messages);
  };

  const dismissImageError = () => {
    imageGenerationStore.dismissError();
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

    <div class="chat-header-actions">
      <button
        type="button"
        class="ghost-button image-header-button"
        disabled={imageGenerationStore.isBusy || !$chatStore.messages.some((message) => message.content.trim() && message.status !== 'streaming')}
        onclick={visualizeLatest}
      >
        Generate image
      </button>
      <div
        class:streaming={$chatStore.generationState !== 'idle' || imageGenerationStore.isBusy}
        class:voice-active={ttsStore.presenceState === 'speaking' || ttsStore.presenceState === 'preparing'}
        class="status-pill"
        aria-label="Companion status"
      >
        <span></span>
        {statusLabel}
      </div>
    </div>
  </header>

  <CharacterSelector />

  <MessageList messages={$chatStore.messages} generationState={$chatStore.generationState} />

  <AudioPlayer />

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

  {#if imageGenerationStore.isBusy || imageGenerationStore.error}
    <div class:has-error={Boolean(imageGenerationStore.error)} class="image-status-banner" role="status" aria-live="polite">
      <div>
        <strong>{imageGenerationStore.statusLabel}</strong>
        <span>{imageGenerationStore.error ?? imageGenerationStore.resourceAwarenessLabel}</span>
      </div>
      {#if imageGenerationStore.error}
        <button type="button" aria-label="Dismiss image generation message" onclick={dismissImageError}>Close</button>
      {/if}
    </div>
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
