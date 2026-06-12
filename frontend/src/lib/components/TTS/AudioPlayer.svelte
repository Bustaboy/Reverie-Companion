<script lang="ts">
  import { ttsStore } from '$lib/stores/ttsStore.svelte';

  interface Props {
    compact?: boolean;
    label?: string;
  }

  let { compact = false, label = 'Voice playback' }: Props = $props();

  const statusLabel = $derived.by(() => {
    if (!ttsStore.enabled) return 'TTS disabled';
    if (ttsStore.bufferHealth === 'prebuffering') return `Pre-buffering · ${ttsStore.bufferedSeconds.toFixed(1)}s`;
    if (ttsStore.bufferHealth === 'rebuffering') return `Smoothing stream · ${ttsStore.currentVoiceName}`;
    if (ttsStore.playbackState === 'loading') return 'Preparing voice';
    if (ttsStore.playbackState === 'playing') return `Speaking · ${ttsStore.currentVoiceName}`;
    if (ttsStore.playbackState === 'paused') return `Paused · ${ttsStore.currentVoiceName}`;
    if (ttsStore.queueCount > 0) return `${ttsStore.queueCount} queued`;
    return 'Voice ready';
  });

  const progressStyle = $derived(`--tts-progress: ${(ttsStore.progress * 100).toFixed(1)}%`);
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

<section class:compact class="audio-player" aria-label={label}>
  <div class:active={ttsStore.isSpeaking} class="voice-orb" aria-hidden="true">
    <span></span>
    <span></span>
    <span></span>
  </div>

  <div class="audio-player-copy">
    <p>{statusLabel}</p>
    <small aria-live="polite">{ttsStore.error ?? ttsStore.announcement}</small>
    <div class="tts-progress" aria-hidden="true" style={progressStyle}></div>
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
