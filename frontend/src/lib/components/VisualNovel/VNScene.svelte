<script lang="ts">
  import { visualNovelStore } from '$lib/stores/visualNovelStore';
  import type { ChatMessage } from '$lib/types/chat';
  import type { ResolvedVisualScene } from '$lib/types/visualNovel';
  import DialogueBox from './DialogueBox.svelte';
  import ExpressionSprite from './ExpressionSprite.svelte';

  interface Props {
    scene: ResolvedVisualScene;
    message?: ChatMessage;
  }

  let { scene, message }: Props = $props();
  let backgroundSrc = $state('');

  $effect(() => {
    backgroundSrc = scene.background.src;
  });

  const useBackgroundFallback = () => {
    backgroundSrc = visualNovelStore.resolveEmergencyFallback('background', scene.background.id).src;
  };
</script>

<section class="vn-scene" aria-label="Visual novel scene">
  <img
    class="vn-background"
    src={backgroundSrc}
    alt={scene.background.alt}
    loading="lazy"
    decoding="async"
    onerror={useBackgroundFallback}
  />
  <div class="vn-vignette" aria-hidden="true"></div>
  <ExpressionSprite expression={scene.expression} pose={scene.pose} displayName={scene.displayName} />
  <DialogueBox
    message={message}
    displayName={scene.displayName}
    expressionId={scene.expression.id}
    poseId={scene.pose.id}
  />
</section>
