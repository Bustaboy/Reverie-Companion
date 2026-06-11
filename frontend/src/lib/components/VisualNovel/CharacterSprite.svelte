<script lang="ts">
  import type { ResolvedCharacterLayer, ResolvedVisualAsset, ResolvedVisualScene, VisualState } from '$lib/types/visualNovel';

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

  const layerClass = (layer: ResolvedCharacterLayer): string =>
    `vn-layer-${layer.layer.replace(/[^a-z0-9_-]/gi, '-').toLowerCase()}`;
</script>

<div class:growth-active={growthActive} class="vn-character-sprite" role="img" aria-label={spriteLabel}>
  {#each scene.characterLayers as layer (`${layer.layer}:${layer.asset.slot}`)}
    {#if layer.asset.kind === 'image' && layer.asset.src}
      <img
        class={`vn-sprite-layer ${layerClass(layer)}`}
        src={layer.asset.src}
        alt=""
        aria-hidden="true"
        loading="eager"
        decoding="async"
      />
    {:else if layer.asset.kind === 'spritesheet'}
      <div
        class={`vn-sprite-layer vn-sprite-sheet ${layerClass(layer)}`}
        style={assetStyle(layer.asset)}
        aria-hidden="true"
      ></div>
    {:else if layer.layer === 'base'}
      <div class="vn-character-placeholder" aria-hidden="true">
        <span class="vn-placeholder-head"></span>
        <span class="vn-placeholder-body"></span>
      </div>
    {:else if layer.layer === 'expression'}
      <span class={`vn-expression-mark expression-${visualState.expression}`} aria-hidden="true"></span>
    {/if}
  {/each}
</div>
