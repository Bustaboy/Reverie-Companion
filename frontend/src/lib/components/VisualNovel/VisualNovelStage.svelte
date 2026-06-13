<script lang="ts">
  import { fade } from 'svelte/transition';
  import { ImageJobCard } from '$lib/components/ImageGeneration';
  import { AudioPlayer } from '$lib/components/TTS';
  import { chatStore } from '$lib/stores/chatStore';
  import { imageGenerationStore } from '$lib/stores/imageGenerationStore.svelte';
  import { ttsStore } from '$lib/stores/ttsStore.svelte';
  import { visualNovelScene, visualNovelStore } from '$lib/stores/visualNovelStore';
  import type { ResolvedVisualLayer, VisualAssetRef } from '$lib/types/visualNovel';

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

  const frameSignature = (asset: VisualAssetRef): string =>
    asset.frame
      ? `${asset.frame.x},${asset.frame.y},${asset.frame.width},${asset.frame.height},${asset.frame.sheetWidth},${asset.frame.sheetHeight}`
      : 'full';

  const layerFrameStyle = (asset: VisualAssetRef): string => {
    if (!asset.frame) return '';

    const { x, y, width, height, sheetWidth, sheetHeight } = asset.frame;
    return [
      `--vn-frame-x: ${x}px`,
      `--vn-frame-y: ${y}px`,
      `--vn-frame-width: ${width}px`,
      `--vn-frame-height: ${height}px`,
      `--vn-sheet-width: ${sheetWidth}px`,
      `--vn-sheet-height: ${sheetHeight}px`,
      `--vn-frame-aspect: ${width} / ${height}`,
      `--vn-frame-sheet-scale-x: ${(sheetWidth / width) * 100}%`,
      `--vn-frame-sheet-scale-y: ${(sheetHeight / height) * 100}%`,
      `--vn-frame-offset-x: ${-(x / sheetWidth) * 100}%`,
      `--vn-frame-offset-y: ${-(y / sheetHeight) * 100}%`
    ].join('; ');
  };

  const layerStyle = (layer: ResolvedVisualLayer): string =>
    [`--vn-layer-order: ${layer.order}`, layerFrameStyle(layer.asset)].filter(Boolean).join('; ');

  const growthModifier = $derived($visualNovelStore.growthModifier);
  const stateSummary = $derived(
    `${$visualNovelScene.expressionLabel} expression, ${$visualNovelScene.poseLabel.toLowerCase()} pose`
  );
  const prefersReducedMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const visualTransitionMs = prefersReducedMotion ? 0 : 220;
  const growthCueLabel = $derived(growthModifier ? growthModifier.cue.replaceAll('_', ' ') : '');
  const growthCueClass = $derived(growthModifier ? growthModifier.cue.replace(/[^a-z0-9_-]/gi, '-') : 'none');
  const layerAltSummary = $derived($visualNovelScene.characterLayers.map((layer) => layer.label).join(', '));
  const visualSignature = $derived(
    `${$visualNovelScene.state.expression}:${$visualNovelScene.state.pose}:${$visualNovelScene.characterLayers
      .map((layer) => `${layer.id}:${layer.asset.src ?? layer.asset.alt}:${frameSignature(layer.asset)}`)
      .join('|')}`
  );
  const growthIntensityStyle = $derived(
    growthModifier ? `--vn-growth-intensity: ${growthModifier.intensity.toFixed(2)}` : '--vn-growth-intensity: 0'
  );
  const visualNovelImageJob = $derived(imageGenerationStore.latestVisualNovelJob);
  const visualNovelImageUrl = $derived(visualNovelImageJob?.status === 'completed' ? visualNovelImageJob.imageUrls[0] : undefined);
  const visualNovelImageBusy = $derived(
    visualNovelImageJob?.status === 'queued' ||
      visualNovelImageJob?.status === 'waiting_for_resources' ||
      visualNovelImageJob?.status === 'paused' ||
      visualNovelImageJob?.status === 'running'
  );

  const handleAssetError = (src?: string) => {
    visualNovelStore.markAssetFailed(src);
  };

  const captureScene = () => {
    imageGenerationStore.captureScene($visualNovelScene, latestAssistantLine, $chatStore.messages);
  };

  const visualizeScene = () => {
    imageGenerationStore.visualizeScene($visualNovelScene, latestAssistantLine);
  };

  const cancelVisualizeScene = () => {
    if (visualNovelImageJob) void imageGenerationStore.cancel(visualNovelImageJob.job_id);
  };

  const handleStageKeydown = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && $visualNovelStore.fullImmersive) {
      visualNovelStore.setFullImmersive(false);
    }
  };
</script>

<svelte:window onkeydown={handleStageKeydown} />

<section
  class:full-immersive={$visualNovelStore.fullImmersive}
  class="visual-novel-stage"
  aria-label="Visual novel mode"
>
  <div class="vn-scene" aria-label="Visual novel scene canvas">
    {#key $visualNovelScene.background.src ?? $visualNovelScene.background.alt}
      {#if $visualNovelScene.background.kind === 'image' && $visualNovelScene.background.src}
        <img
          class="vn-background-image"
          src={$visualNovelScene.background.src}
          alt={$visualNovelScene.background.alt}
          loading="lazy"
          decoding="async"
          onerror={() => handleAssetError($visualNovelScene.background.src)}
          transition:fade={{ duration: visualTransitionMs }}
        />
      {:else}
        <div
          class="vn-background-placeholder"
          aria-label={$visualNovelScene.background.alt}
          style={`--vn-bg-tone: ${$visualNovelScene.background.dominantColor ?? '#1b1723'}`}
          transition:fade={{ duration: visualTransitionMs }}
        ></div>
      {/if}
    {/key}

    <div class="vn-topbar" aria-label="Visual novel controls">
      <div>
        <p class="eyebrow">Visual novel foundation</p>
        <h1>{$visualNovelScene.manifest.characterName}</h1>
      </div>

      <div class="vn-actions">
        <button
          type="button"
          class="ghost-button"
          aria-label="Capture the current scene as a character-linked Moment Capture"
          disabled={visualNovelImageBusy}
          onclick={captureScene}
        >
          {visualNovelImageBusy ? 'Capturing scene' : 'Capture this scene'}
        </button>
        <button type="button" class="ghost-button legacy" aria-label="Visualize the current scene with legacy local image generation" disabled={visualNovelImageBusy} onclick={visualizeScene}>Legacy visualize</button>
        <button type="button" class="ghost-button" aria-label="Return to chat mode" onclick={onReturnToChat}>Chat</button>
        <button
          type="button"
          class="ghost-button"
          aria-pressed={$visualNovelStore.fullImmersive}
          aria-keyshortcuts="Escape"
          aria-label={$visualNovelStore.fullImmersive ? 'Exit full immersive visual novel mode' : 'Enter full immersive visual novel mode'}
          onclick={() => visualNovelStore.toggleFullImmersive()}
        >
          {$visualNovelStore.fullImmersive ? 'Exit immersion' : 'Full immersion'}
        </button>
      </div>
    </div>

    {#if visualNovelImageUrl}
      <img
        class="vn-generated-scene-image"
        src={visualNovelImageUrl}
        alt="Generated visualization of the current visual novel scene"
        loading="lazy"
        decoding="async"
        transition:fade={{ duration: visualTransitionMs }}
      />
    {/if}

    <div
      class:growth-reactive={Boolean(growthModifier)}
      class:is-speaking={ttsStore.isSpeaking}
      class={`vn-character-layer growth-cue-${growthCueClass}`}
      aria-label={`Reverie layered visual state: ${stateSummary}; layers ${layerAltSummary}${growthModifier ? `; growth cue ${growthCueLabel}` : ''}`}
      aria-live="polite"
      aria-atomic="true"
      role="img"
      style={growthIntensityStyle}
    >
      {#key visualSignature}
        <div class="vn-layer-stack" transition:fade={{ duration: visualTransitionMs }}>
          {#each $visualNovelScene.characterLayers as layer (layer.id)}
            {#if layer.asset.kind === 'image' && layer.asset.src && layer.asset.frame}
              <div
                class="vn-character-sprite vn-character-frame"
                aria-label={layer.asset.alt}
                title={layer.label}
                style={layerStyle(layer)}
              >
                <img
                  src={layer.asset.src}
                  alt=""
                  loading="lazy"
                  decoding="async"
                  onerror={() => handleAssetError(layer.asset.src)}
                />
              </div>
            {:else if layer.asset.kind === 'image' && layer.asset.src}
              <img
                class="vn-character-sprite vn-character-layer-image"
                src={layer.asset.src}
                alt={layer.asset.alt}
                title={layer.label}
                loading="lazy"
                decoding="async"
                onerror={() => handleAssetError(layer.asset.src)}
                style={layerStyle(layer)}
              />
            {:else}
              <div
                class="vn-character-placeholder"
                aria-label={layer.asset.alt}
                title={layer.label}
                style={`${layerStyle(layer)}; --vn-character-tone: ${layer.asset.dominantColor ?? '#f09a9f'}`}
              >
                <span aria-hidden="true">R</span>
              </div>
            {/if}
          {/each}
        </div>
      {/key}
    </div>

    <div class="vn-dialogue-panel" aria-label="Visual novel dialogue" aria-live="polite" aria-atomic="false">
      <div class="vn-speaker-row">
        <strong>{$visualNovelScene.manifest.characterName}</strong>
        <span>{growthModifier ? `${stateSummary} · ${growthCueLabel}` : stateSummary}</span>
        {#if ttsStore.presenceState === 'speaking' || ttsStore.presenceState === 'preparing'}
          <em class="vn-voice-cue">{ttsStore.presenceLabel}</em>
        {/if}
      </div>
      <p>{latestAssistantLine}</p>
      {#if $visualNovelScene.usedFallback}
        <small>Using safe fallback visuals until every authored layer is available.</small>
      {/if}
      {#if visualNovelImageJob}
        <ImageJobCard
          job={visualNovelImageJob}
          compact
          showPreview={false}
          onCancel={cancelVisualizeScene}
          onRetry={() => imageGenerationStore.regenerate(visualNovelImageJob)}
          onVary={() => imageGenerationStore.vary(visualNovelImageJob)}
          onSave={() => imageGenerationStore.saveToCharacterAssets(visualNovelImageJob)}
          onDelete={() => imageGenerationStore.deleteImage(visualNovelImageJob.job_id)}
        />
      {/if}
      <AudioPlayer compact label="Visual novel voice playback" />
    </div>
  </div>
</section>
