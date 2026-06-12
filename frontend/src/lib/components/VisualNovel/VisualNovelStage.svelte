<script lang="ts">
  import { chatStore } from '$lib/stores/chatStore';
  import { visualNovelScene, visualNovelStore } from '$lib/stores/visualNovelStore';

  interface Props {
    onReturnToChat: () => void;
  }

  let { onReturnToChat }: Props = $props();

  const latestAssistantLine = $derived.by(() => {
    const assistantMessage = [...$chatStore.messages]
      .reverse()
      .find((message) => message.role === 'assistant' && message.content.trim().length > 0);

    return assistantMessage?.content.trim() ?? 'Reverie settles into the quiet, ready for the next moment with you.';
  });

  const stateSummary = $derived(
    `${$visualNovelScene.expressionLabel} expression, ${$visualNovelScene.poseLabel.toLowerCase()} pose`
  );

  const handleSpriteError = () => {
    visualNovelStore.markAssetFailed($visualNovelScene.sprite.src);
  };

  const handleBackgroundError = () => {
    visualNovelStore.markAssetFailed($visualNovelScene.background.src);
  };
</script>

<section class:full-immersive={$visualNovelStore.fullImmersive} class="visual-novel-stage" aria-label="Visual novel mode">
  <div class="vn-scene" aria-label="Visual novel scene canvas">
    {#if $visualNovelScene.background.kind === 'image' && $visualNovelScene.background.src}
      <img
        class="vn-background-image"
        src={$visualNovelScene.background.src}
        alt={$visualNovelScene.background.alt}
        loading="lazy"
        decoding="async"
        onerror={handleBackgroundError}
      />
    {:else}
      <div
        class="vn-background-placeholder"
        aria-label={$visualNovelScene.background.alt}
        style={`--vn-bg-tone: ${$visualNovelScene.background.dominantColor ?? '#1b1723'}`}
      ></div>
    {/if}

    <div class="vn-topbar" aria-label="Visual novel controls">
      <div>
        <p class="eyebrow">Visual novel foundation</p>
        <h1>{$visualNovelScene.manifest.characterName}</h1>
      </div>

      <div class="vn-actions">
        <button type="button" class="ghost-button" aria-label="Return to chat mode" onclick={onReturnToChat}>Chat</button>
        <button
          type="button"
          class="ghost-button"
          aria-pressed={$visualNovelStore.fullImmersive}
          aria-label={$visualNovelStore.fullImmersive ? 'Exit full immersive visual novel mode' : 'Enter full immersive visual novel mode'}
          onclick={() => visualNovelStore.toggleFullImmersive()}
        >
          {$visualNovelStore.fullImmersive ? 'Exit immersion' : 'Full immersion'}
        </button>
      </div>
    </div>

    <div class="vn-character-layer" aria-label={`Reverie visual state: ${stateSummary}`}>
      {#if $visualNovelScene.sprite.kind === 'image' && $visualNovelScene.sprite.src}
        <img
          class="vn-character-sprite"
          src={$visualNovelScene.sprite.src}
          alt={$visualNovelScene.sprite.alt}
          loading="lazy"
          decoding="async"
          onerror={handleSpriteError}
        />
      {:else}
        <div
          class="vn-character-placeholder"
          role="img"
          aria-label={$visualNovelScene.sprite.alt}
          style={`--vn-character-tone: ${$visualNovelScene.sprite.dominantColor ?? '#f09a9f'}`}
        >
          <span aria-hidden="true">R</span>
        </div>
      {/if}
    </div>

    <div class="vn-dialogue-panel" aria-label="Visual novel dialogue">
      <div class="vn-speaker-row">
        <strong>{$visualNovelScene.manifest.characterName}</strong>
        <span>{stateSummary}</span>
      </div>
      <p>{latestAssistantLine}</p>
      {#if $visualNovelScene.usedFallback}
        <small>Using neutral fallback visuals until character assets are available.</small>
      {/if}
    </div>
  </div>
</section>
