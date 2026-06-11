<script lang="ts">
  import type { ResolvedVisualAsset, ResolvedVisualScene, VisualState } from '$lib/types/visualNovel';

  interface Props {
    scene: ResolvedVisualScene;
    visualState: VisualState;
    growthActive: boolean;
  }

  let { scene, visualState, growthActive }: Props = $props();

  const assetStyle = (asset: ResolvedVisualAsset): string => {
    if (asset.kind !== 'spritesheet' || !asset.src || !asset.frame) {
      return '';
    }

    return [
      `width: ${asset.frame.width}px`,
      `height: ${asset.frame.height}px`,
      `background-image: url("${asset.src}")`,
      `background-position: -${asset.frame.x}px -${asset.frame.y}px`
    ].join('; ');
  };

  const spriteLabel = $derived(
    `Reverie character sprite, ${visualState.expression} expression, ${visualState.pose} pose`
  );
</script>

<div class:growth-active={growthActive} class="vn-character-sprite" role="img" aria-label={spriteLabel}>
  {#if scene.pose.kind === 'image' && scene.pose.src}
    <img class="vn-sprite-layer vn-pose-layer" src={scene.pose.src} alt="" aria-hidden="true" loading="eager" />
  {:else if scene.pose.kind === 'spritesheet'}
    <div class="vn-sprite-layer vn-pose-layer vn-sprite-sheet" style={assetStyle(scene.pose)} aria-hidden="true"></div>
  {:else}
    <div class="vn-character-placeholder" aria-hidden="true">
      <span class="vn-placeholder-head"></span>
      <span class="vn-placeholder-body"></span>
    </div>
  {/if}

  {#if scene.expression.kind === 'image' && scene.expression.src}
    <img class="vn-sprite-layer vn-expression-layer" src={scene.expression.src} alt="" aria-hidden="true" loading="eager" />
  {:else if scene.expression.kind === 'spritesheet'}
    <div class="vn-sprite-layer vn-expression-layer vn-sprite-sheet" style={assetStyle(scene.expression)} aria-hidden="true"></div>
  {:else}
    <span class={`vn-expression-mark expression-${visualState.expression}`} aria-hidden="true"></span>
  {/if}
</div>
