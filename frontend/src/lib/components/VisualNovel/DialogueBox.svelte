<script lang="ts">
  import type { ChatMessage } from '$lib/types/chat';

  interface Props {
    message?: ChatMessage;
    displayName: string;
    expressionId: string;
    poseId: string;
  }

  let { message, displayName, expressionId, poseId }: Props = $props();

  const dialogueText = $derived(
    message?.content?.trim() || 'The room settles into a quiet pause while Reverie waits with you.'
  );
</script>

<aside class="vn-dialogue" aria-label="Visual novel dialogue panel" aria-live="polite">
  <div class="vn-dialogue-meta">
    <strong>{displayName}</strong>
    <span aria-label={`Current expression ${expressionId}, current pose ${poseId}`}>{expressionId} · {poseId}</span>
  </div>
  <p>{dialogueText}</p>
</aside>
