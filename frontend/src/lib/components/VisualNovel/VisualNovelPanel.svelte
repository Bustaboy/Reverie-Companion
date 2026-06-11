<script lang="ts">
  import { onMount } from 'svelte';
  import { chatStore } from '$lib/stores/chatStore';
  import { visualNovelStore, visualNovelView } from '$lib/stores/visualNovelStore';
  import VNScene from './VNScene.svelte';

  interface Props {
    onReturnToChat: () => void;
  }

  let { onReturnToChat }: Props = $props();

  const latestAssistantMessage = $derived.by(() =>
    [...$chatStore.messages].reverse().find((message) => message.role === 'assistant' && message.content.trim())
  );

  const requestSceneMedia = () => {
    void visualNovelStore.requestCurrentSceneMedia();
  };

  const dismissMediaStatus = () => {
    visualNovelStore.clearMediaStatus();
  };

  const isTextEntryTarget = (target: EventTarget | null): boolean => {
    if (!(target instanceof HTMLElement)) {
      return false;
    }

    const tagName = target.tagName.toLowerCase();
    return target.isContentEditable || ['input', 'textarea', 'select'].includes(tagName);
  };

  const handleKeyboardShortcut = (event: KeyboardEvent) => {
    if (event.defaultPrevented || isTextEntryTarget(event.target)) {
      return;
    }

    if (event.key === 'Escape') {
      event.preventDefault();
      onReturnToChat();
      return;
    }

    if (
      event.key.toLowerCase() === 'g' &&
      !event.altKey &&
      !event.ctrlKey &&
      !event.metaKey &&
      $visualNovelView.mediaCapabilities.available
    ) {
      event.preventDefault();
      requestSceneMedia();
    }
  };

  onMount(() => {
    void visualNovelStore.refreshMediaCapabilities();
    window.addEventListener('keydown', handleKeyboardShortcut);

    return () => {
      window.removeEventListener('keydown', handleKeyboardShortcut);
    };
  });
</script>

<section class="visual-novel-panel" aria-label="Visual Novel mode">
  <header class="visual-novel-header">
    <div>
      <p class="eyebrow">Visual novel mode</p>
      <h1>Reverie</h1>
      <p class="subtitle">
        {$visualNovelView.visualState.expression} expression · {$visualNovelView.visualState.pose} pose
      </p>
    </div>

    <button
      type="button"
      class="ghost-button"
      aria-label="Return to chat mode"
      aria-keyshortcuts="Escape"
      onclick={onReturnToChat}
    >
      Back to Chat
    </button>
  </header>

  <VNScene
    view={$visualNovelView}
    latestMessage={latestAssistantMessage}
    onGenerateScene={requestSceneMedia}
    onDismissMediaStatus={dismissMediaStatus}
  />
</section>
