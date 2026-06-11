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

  onMount(() => {
    void visualNovelStore.refreshMediaCapabilities();
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

    <button type="button" class="ghost-button" onclick={onReturnToChat}>Back to Chat</button>
  </header>

  <VNScene
    view={$visualNovelView}
    latestMessage={latestAssistantMessage}
    onGenerateScene={requestSceneMedia}
    onDismissMediaStatus={dismissMediaStatus}
  />
</section>
