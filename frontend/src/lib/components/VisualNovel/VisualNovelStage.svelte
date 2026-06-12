<script lang="ts">
  import { fade } from 'svelte/transition';
  import { chatStore } from '$lib/stores/chatStore';
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

  const growthModifier = $derived($visualNovelStore.growthModifier);
  const stateSummary = $derived(
    `${$visualNovelScene.expressionLabel} expression, ${$visualNovelScene.poseLabel.toLowerCase()} pose`
  );
  const prefersReducedMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const spriteTransitionMs = prefersReducedMotion ? 0 : 220;
  const growthCueLabel = $derived(growthModifier ? growthModifier.cue.replaceAll('_', ' ') : '');
  const growthCueClass = $derived(growthModifier ? growthModifier.cue.replace(/[^a-z0-9_-]/gi, '-') : 'none');
  const visualSignature = $derived(
    `${$visualNovelScene.compositionMode}:${$visualNovelScene.state.expression}:${$visualNovelScene.state.pose}:${$visualNovelScene.layers.map((layer) => `${layer.name}:${layer.asset.src ?? layer.asset.alt}`).join('|')}:${$visualNovelScene.sprite.src ?? $visualNovelScene.sprite.alt}`
  );
  const growthIntensityStyle = $derived(
    growthModifier ? `--vn-growth-intensity: ${growthModifier.intensity.toFixed(2)}` : '--vn-growth-intensity: 0'
  );
  const layerSummary = $derived(
    $visualNovelScene.compositionMode === 'layers'
      ? `Layered render using ${$visualNovelScene.layers.map((layer) => layer.label).join(', ')}`
      : 'Full-sprite fallback render'
  );

  const handleSpriteError = () => {
    visualNovelStore.markAssetFailed($visualNovelScene.sprite.src);
  };

  const handleLayerError = (layer: ResolvedVisualLayer) => {
    visualNovelStore.markAssetFailed(layer.asset.src);
  };

  const handleBackgroundError = () => {
    visualNovelStore.markAssetFailed($visualNovelScene.background.src);
  };

  const handleStageKeydown = (event: KeyboardEvent) => {
    if (event.defaultPrevented) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      onReturnToChat();
      return;
    }

    if (event.key.toLowerCase() === 'f') {
      event.preventDefault();
      visualNovelStore.toggleFullImmersive();
    }
  };

  const frameStyle = (asset: VisualAssetRef): string => {
    if (!asset.frame || !asset.src) return '';
    return [
      `--vn-frame-src: url("${asset.src.replaceAll('"', '%22')}")`,
      `--vn-frame-x: ${asset.frame.x}px`,
      `--vn-frame-y: ${asset.frame.y}px`,
      `--vn-frame-w: ${asset.frame.width}px`,
      `--vn-frame-h: ${asset.frame.height}px`
    ].join('; ');
  };

  const layerStyle = (layer: ResolvedVisualLayer): string =>
    [
      `--vn-layer-z: ${layer.zIndex}`,
      `--vn-layer-opacity: ${layer.opacity}`,
      layer.blendMode ? `--vn-layer-blend: ${layer.blendMode}` : '--vn-layer-blend: normal',
      frameStyle(layer.asset)
    ]
      .filter(Boolean)
      .join('; ');
</script>

<svelte:window onkeydown={handleStageKeydown} />

<svelte:head>
  {#each $visualNovelScene.layers as layer (layer.name)}
    {#if layer.asset.kind === 'image' && layer.asset.src && !layer.asset.src.startsWith('data:')}
      <link rel="preload" as="image" href={layer.asset.src} />
    {/if}
  {/each}
</svelte:head>

<section
  class:full-immersive={$visualNovelStore.fullImmersive}
  class="visual-novel-stage"
  aria-label="Visual novel mode"
  aria-describedby="vn-keyboard-help vn-state-live"
>
  <p id="vn-keyboard-help" class="sr-only">Visual novel mode. Press Escape to return to chat, or F to toggle full immersion.</p>
  <div id="vn-state-live" class="sr-only" aria-live="polite">
    {$visualNovelScene.manifest.characterName} is showing {stateSummary}. {layerSummary}.
    {growthModifier ? `Growth cue ${growthCueLabel}.` : ''}
  </div>

  <div class="vn-scene" aria-label="Visual novel scene canvas">
    {#key $visualNovelScene.state.background}
      {#if $visualNovelScene.background.kind === 'image' && $visualNovelScene.background.src}
        <img
          class="vn-background-image"
          src={$visualNovelScene.background.src}
          alt={$visualNovelScene.background.alt}
          loading="lazy"
          decoding="async"
          onerror={handleBackgroundError}
          transition:fade={{ duration: spriteTransitionMs }}
        />
      {:else}
        <div
          class="vn-background-placeholder"
          aria-label={$visualNovelScene.background.alt}
          style={`--vn-bg-tone: ${$visualNovelScene.background.dominantColor ?? '#1b1723'}`}
          transition:fade={{ duration: spriteTransitionMs }}
        ></div>
      {/if}
    {/key}

    <div class="vn-topbar" aria-label="Visual novel controls">
      <div>
        <p class="eyebrow">Visual novel foundation</p>
        <h1>{$visualNovelScene.manifest.characterName}</h1>
      </div>

      <div class="vn-actions" role="toolbar" aria-label="Visual novel actions">
        <button type="button" class="ghost-button" aria-keyshortcuts="Escape" aria-label="Return to chat mode" onclick={onReturnToChat}>Chat</button>
        <button
          type="button"
          class="ghost-button"
          aria-keyshortcuts="F"
          aria-pressed={$visualNovelStore.fullImmersive}
          aria-label={$visualNovelStore.fullImmersive ? 'Exit full immersive visual novel mode' : 'Enter full immersive visual novel mode'}
          onclick={() => visualNovelStore.toggleFullImmersive()}
        >
          {$visualNovelStore.fullImmersive ? 'Exit immersion' : 'Full immersion'}
        </button>
      </div>
    </div>

    <div
      class:growth-reactive={Boolean(growthModifier)}
      class={`vn-character-layer growth-cue-${growthCueClass}`}
      aria-label={`Reverie visual state: ${stateSummary}${growthModifier ? `, growth cue ${growthCueLabel}` : ''}`}
      role="img"
      style={growthIntensityStyle}
    >
      {#key visualSignature}
        {#if $visualNovelScene.compositionMode === 'layers'}
          <div class="vn-layer-stack" aria-hidden="true" transition:fade={{ duration: spriteTransitionMs }}>
            {#each $visualNovelScene.layers as layer (layer.name)}
              {#if layer.asset.kind === 'image' && layer.asset.src && layer.asset.frame}
                <div
                  class="vn-character-sprite vn-character-frame vn-composited-layer"
                  style={layerStyle(layer)}
                  title={layer.asset.alt}
                ></div>
                <img class="sr-only" src={layer.asset.src} alt="" loading="lazy" decoding="async" onerror={() => handleLayerError(layer)} />
              {:else if layer.asset.kind === 'image' && layer.asset.src}
                <img
                  class="vn-character-sprite vn-composited-layer"
                  src={layer.asset.src}
                  alt=""
                  loading="lazy"
                  decoding="async"
                  onerror={() => handleLayerError(layer)}
                  style={layerStyle(layer)}
                />
              {:else}
                <div
                  class="vn-character-placeholder vn-composited-layer"
                  style={`${layerStyle(layer)}; --vn-character-tone: ${layer.asset.dominantColor ?? '#f09a9f'}`}
                >
                  <span aria-hidden="true">R</span>
                </div>
              {/if}
            {/each}
          </div>
        {:else if $visualNovelScene.sprite.kind === 'image' && $visualNovelScene.sprite.src && $visualNovelScene.sprite.frame}
          <div
            class="vn-character-sprite vn-character-frame"
            role="presentation"
            aria-hidden="true"
            style={frameStyle($visualNovelScene.sprite)}
            transition:fade={{ duration: spriteTransitionMs }}
          ></div>
          <img class="sr-only" src={$visualNovelScene.sprite.src} alt="" loading="lazy" decoding="async" onerror={handleSpriteError} />
        {:else if $visualNovelScene.sprite.kind === 'image' && $visualNovelScene.sprite.src}
          <img
            class="vn-character-sprite"
            src={$visualNovelScene.sprite.src}
            alt={$visualNovelScene.sprite.alt}
            loading="lazy"
            decoding="async"
            onerror={handleSpriteError}
            transition:fade={{ duration: spriteTransitionMs }}
          />
        {:else}
          <div
            class="vn-character-placeholder"
            role="presentation"
            aria-hidden="true"
            style={`--vn-character-tone: ${$visualNovelScene.sprite.dominantColor ?? '#f09a9f'}`}
            transition:fade={{ duration: spriteTransitionMs }}
          >
            <span aria-hidden="true">R</span>
          </div>
        {/if}
      {/key}
    </div>

    <div class="vn-dialogue-panel" aria-label="Visual novel dialogue" aria-live="polite">
      <div class="vn-speaker-row">
        <strong>{$visualNovelScene.manifest.characterName}</strong>
        <span>{growthModifier ? `${stateSummary} · ${growthCueLabel}` : stateSummary}</span>
      </div>
      <p>{latestAssistantLine}</p>
      {#if $visualNovelScene.usedFallback}
        <small>Using safe fallback visuals for one or more missing layers until character assets are available.</small>
      {/if}
    </div>
  </div>
</section>
