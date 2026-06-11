<script lang="ts">
  import { Markdown } from '$lib/components/Chat';
  import type { ChatMessage } from '$lib/types/chat';
  import type { GrowthVisualModifier, VisualState } from '$lib/types/visualNovel';

  interface Props {
    message?: ChatMessage;
    visualState: VisualState;
    growthModifier: GrowthVisualModifier | null;
    mediaStatusMessage: string | null;
    canGenerateScene: boolean;
    mediaCapabilityMessage?: string;
    onGenerateScene: () => void;
    onDismissMediaStatus: () => void;
  }

  let {
    message,
    visualState,
    growthModifier,
    mediaStatusMessage,
    canGenerateScene,
    mediaCapabilityMessage,
    onGenerateScene,
    onDismissMediaStatus
  }: Props = $props();

  const dialogueContent = $derived(
    message?.content?.trim() || "I'm here with you. Let the scene settle around us."
  );
</script>

<aside class="vn-dialogue-box" aria-label="Visual novel dialogue" aria-live="polite">
  <div class="vn-dialogue-topline">
    <div>
      <strong>Reverie</strong>
      <span>{visualState.expression} · {visualState.pose}</span>
    </div>
    <button
      type="button"
      class="vn-media-button"
      aria-label={canGenerateScene ? 'Generate current visual novel scene' : (mediaCapabilityMessage ?? 'Scene generation is unavailable')}
      aria-keyshortcuts="G"
      disabled={!canGenerateScene}
      onclick={onGenerateScene}
    >
      Generate Scene
    </button>
  </div>

  <div class="vn-dialogue-content" role="document" aria-label="Current assistant dialogue">
    <Markdown content={dialogueContent} />
  </div>

  <div class="vn-scene-state" aria-label="Current visual state">
    <span>{Math.round(visualState.confidence * 100)}% confidence</span>
    <span>{Math.round(visualState.intensity * 100)}% intensity</span>
    {#if growthModifier}
      <span>growth cue: {growthModifier.cue}</span>
    {/if}
  </div>

  {#if mediaStatusMessage}
    <div class="vn-media-status" role="status">
      <span>{mediaStatusMessage}</span>
      <button type="button" aria-label="Dismiss scene generation status" onclick={onDismissMediaStatus}>Close</button>
    </div>
  {/if}
</aside>
