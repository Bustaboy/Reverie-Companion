<script lang="ts">
  import type { ChatMessage } from '$lib/types/chat';
  import type { ResolvedVisualAsset } from '$lib/types/visualNovel';
  import type { VisualNovelView } from '$lib/stores/visualNovelStore';
  import CharacterSprite from './CharacterSprite.svelte';
  import DialogueBox from './DialogueBox.svelte';

  interface Props {
    view: VisualNovelView;
    latestMessage?: ChatMessage;
    onGenerateScene: () => void;
    onDismissMediaStatus: () => void;
  }

  let { view, latestMessage, onGenerateScene, onDismissMediaStatus }: Props = $props();

  const backgroundStyle = (asset: ResolvedVisualAsset): string => {
    if (asset.kind !== 'spritesheet' || !asset.src || !asset.frame) {
      return '';
    }

    return [
      `background-image: url("${asset.src}")`,
      `background-position: -${asset.frame.x}px -${asset.frame.y}px`
    ].join('; ');
  };

  const sceneLabel = $derived(
    `Visual novel scene, ${view.visualState.background} background, ${view.visualState.expression} expression`
  );
</script>

<section class="vn-scene" aria-label={sceneLabel}>
  <div class="vn-background-layer" aria-hidden="true">
    {#if view.scene.background.kind === 'image' && view.scene.background.src}
      <img src={view.scene.background.src} alt="" loading="eager" />
    {:else if view.scene.background.kind === 'spritesheet'}
      <div class="vn-background-sheet" style={backgroundStyle(view.scene.background)}></div>
    {:else}
      <div class={`vn-background-placeholder background-${view.visualState.background}`}></div>
    {/if}
  </div>

  <CharacterSprite
    scene={view.scene}
    visualState={view.visualState}
    growthActive={Boolean(view.growthModifier)}
  />

  <DialogueBox
    message={latestMessage}
    visualState={view.visualState}
    growthModifier={view.growthModifier}
    mediaStatusMessage={view.mediaStatusMessage}
    {onGenerateScene}
    {onDismissMediaStatus}
  />
</section>
