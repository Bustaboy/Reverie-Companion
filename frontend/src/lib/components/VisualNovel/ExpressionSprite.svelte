<script lang="ts">
  import { visualNovelStore } from '$lib/stores/visualNovelStore';
  import type { ResolvedVisualAsset } from '$lib/types/visualNovel';

  interface Props {
    expression: ResolvedVisualAsset;
    pose: ResolvedVisualAsset;
    displayName: string;
  }

  let { expression, pose, displayName }: Props = $props();
  let expressionSrc = $state('');
  let poseSrc = $state('');

  $effect(() => {
    expressionSrc = expression.src;
  });

  $effect(() => {
    poseSrc = pose.src;
  });

  const useExpressionFallback = () => {
    expressionSrc = visualNovelStore.resolveEmergencyFallback('expression', expression.id).src;
  };

  const usePoseFallback = () => {
    poseSrc = visualNovelStore.resolveEmergencyFallback('pose', pose.id).src;
  };
</script>

<div class="vn-sprite" aria-label={`${displayName} visual sprite`}>
  <img
    class="vn-pose"
    src={poseSrc}
    alt={pose.alt}
    loading="lazy"
    decoding="async"
    onerror={usePoseFallback}
  />
  <img
    class="vn-expression"
    src={expressionSrc}
    alt={expression.alt}
    loading="lazy"
    decoding="async"
    onerror={useExpressionFallback}
  />
</div>
