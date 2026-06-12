<script lang="ts">
  import { ttsStore } from '$lib/stores/ttsStore.svelte';

  interface Props {
    compact?: boolean;
    label?: string;
  }

  let { compact = false, label = 'Voice playback' }: Props = $props();

  const statusLabel = $derived.by(() => {
    if (ttsStore.bufferHealth === 'prebuffering') return `Pre-buffering · ${ttsStore.bufferedSeconds.toFixed(1)}s ready`;
    if (ttsStore.bufferHealth === 'rebuffering') return `Smoothing stream · ${ttsStore.currentVoiceName}`;
    return ttsStore.presenceLabel;
  });

  const detailLabel = $derived.by(() => {
    if (ttsStore.error) return ttsStore.error;
    if (ttsStore.bufferHealth === 'buffered-fallback') return 'Using safe buffered playback for this backend.';
    if (ttsStore.bufferHealth === 'low') return 'Keeping the voice smooth while chunks arrive.';
    if (ttsStore.queueCount > 0 && ttsStore.isBusy) return `${ttsStore.queueCount} more line${ttsStore.queueCount === 1 ? '' : 's'} waiting.`;
    return ttsStore.announcement;
  });

  const progressPercent = $derived(Math.round(ttsStore.progress * 100));
  const progressStyle = $derived(`--tts-progress: ${progressPercent}%`);
  const buttonLabel = $derived(ttsStore.playbackState === 'playing' ? 'Pause speech' : 'Play speech');

  const togglePlay = () => {
    if (ttsStore.playbackState === 'playing') {
      ttsStore.pause();
      return;
    }

    void ttsStore.play();
  };

  const handleAutoPlayChange = (event: Event) => {
    ttsStore.setAutoPlay((event.currentTarget as HTMLInputElement).checked);
  };
</script>

<section
  class:compact
  class:voice-active={ttsStore.presenceState === 'speaking' || ttsStore.presenceState === 'preparing'}
  class:voice-error={ttsStore.presenceState === 'error'}
  class={`audio-player voice-state-${ttsStore.presenceState}`}
  aria-label={label}
>
  <div class:active={ttsStore.isSpeaking} class="voice-orb" aria-hidden="true">
    <span></span>
    <span></span>
    <span></span>
  </div>

  <div class:error={Boolean(ttsStore.error)} class="audio-player-copy">
    <p>{statusLabel}</p>
    <small aria-live="polite">{detailLabel}</small>
    <div
      class="tts-progress"
      role="progressbar"
      aria-label="Speech playback progress"
      aria-valuemin="0"
      aria-valuemax="100"
      aria-valuenow={progressPercent}
      style={progressStyle}
    ></div>
    {#if ttsStore.error}
      <button type="button" class="tts-error-action" onclick={() => ttsStore.clearError()}>Dismiss</button>
    {/if}
  </div>

  <div class="audio-controls">
    <button
      type="button"
      class="round-control"
      disabled={!ttsStore.enabled || (ttsStore.queueCount === 0 && !ttsStore.isBusy)}
      aria-label={buttonLabel}
      onclick={togglePlay}
    >
      {#if ttsStore.playbackState === 'playing'}
        ❚❚
      {:else if ttsStore.playbackState === 'loading'}
        ◌
      {:else}
        ▶
      {/if}
    </button>
    <button
      type="button"
      class="round-control subtle"
      disabled={!ttsStore.isBusy && ttsStore.queueCount === 0}
      aria-label="Stop speech playback"
      onclick={() => ttsStore.stop()}
    >
      ■
    </button>
    <label class="tts-auto-toggle">
      <input type="checkbox" checked={ttsStore.autoPlay} disabled={!ttsStore.enabled} onchange={handleAutoPlayChange} />
      <span>Auto-play</span>
    </label>
  </div>

  <span class="sr-only" aria-live="polite" aria-atomic="true">{ttsStore.announcement}</span>
</section>
