<script lang="ts">
  import { chatStore } from '$lib/stores/chatStore';
  import { visualNovelStore } from '$lib/stores/visualNovelStore';
  import VNScene from './VNScene.svelte';

  const visualNovelScene = visualNovelStore.scene;

  const latestAssistantMessage = $derived(
    [...$chatStore.messages].reverse().find((message) => message.role === 'assistant' && message.content.trim())
  );

  const expressionOptions = ['neutral', 'happy', 'soft', 'teasing'];
  const poseOptions = ['idle', 'speaking', 'thinking'];

  const setExpression = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement;
    visualNovelStore.setExpression(target.value);
  };

  const setPose = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement;
    visualNovelStore.setPose(target.value);
  };
</script>

<section class="visual-novel-panel" aria-label="Reverie visual novel mode">
  <header class="vn-header">
    <div>
      <p class="eyebrow">Visual Novel Mode</p>
      <h1>Immersive companion scene</h1>
      <p class="subtitle">Lightweight sprites react to chat visual_state metadata with safe neutral/idle fallbacks.</p>
    </div>
    <div class="vn-header-actions" aria-label="Visual novel view controls">
      <button type="button" class="ghost-button" onclick={() => visualNovelStore.setImmersive(!$visualNovelStore.immersive)}>
        {$visualNovelStore.immersive ? 'Exit full scene' : 'Full scene'}
      </button>
      <button type="button" class="ghost-button" onclick={() => visualNovelStore.resetVisuals()}>Reset visuals</button>
    </div>
  </header>

  <VNScene scene={$visualNovelScene} message={latestAssistantMessage} />

  <footer class="vn-controls" aria-label="Basic expression and pose controls">
    <label>
      <span>Expression</span>
      <select value={$visualNovelStore.visualState.expression ?? 'neutral'} onchange={setExpression} aria-label="Choose sprite expression">
        {#each expressionOptions as expression}
          <option value={expression}>{expression}</option>
        {/each}
      </select>
    </label>
    <label>
      <span>Pose</span>
      <select value={$visualNovelStore.visualState.pose ?? 'idle'} onchange={setPose} aria-label="Choose sprite pose">
        {#each poseOptions as pose}
          <option value={pose}>{pose}</option>
        {/each}
      </select>
    </label>
    <p role="status" aria-live="polite">
      Showing {$visualNovelScene.displayName}: {$visualNovelScene.expression.id} / {$visualNovelScene.pose.id}
    </p>
  </footer>
</section>
