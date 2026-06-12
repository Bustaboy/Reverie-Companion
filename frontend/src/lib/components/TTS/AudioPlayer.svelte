<script lang="ts">
  import { ttsStore } from '$lib/stores/ttsStore.svelte';

  interface Props {
    compact?: boolean;
    label?: string;
  }

  let { compact = false, label = 'Voice playback' }: Props = $props();

  const statusLabel = $derived.by(() => {
    if (!ttsStore.enabled) return 'Voice is disabled';
    if (ttsStore.bufferHealth === 'prebuffering') return `Warming voice · ${ttsStore.bufferedSeconds.toFixed(1)}s ready`;
    if (ttsStore.bufferHealth === 'rebuffering') return `Smoothing stream · ${ttsStore.currentVoiceName}`;
    if (ttsStore.playbackState === 'loading') return `Preparing · ${ttsStore.currentVoiceName}`;
    if (ttsStore.playbackState === 'playing') return `Speaking · ${ttsStore.currentVoiceName}`;
    if (ttsStore.playbackState === 'paused') return `Paused · ${ttsStore.currentVoiceName}`;
    if (ttsStore.queueCount > 0) return `${ttsStore.queueCount} voice line${ttsStore.queueCount === 1 ? '' : 's'} waiting`;
    return 'Voice ready';
  });

  const detailLabel = $derived.by(() => {
    if (ttsStore.error) return ttsStore.error;
    if (ttsStore.currentLineWasShortened && (ttsStore.playbackState === 'loading' || ttsStore.playbackState === 'playing')) {
      return 'Long reply: speaking a natural first segment to stay responsive.';
    }
    if (ttsStore.playbackState === 'playing' || ttsStore.playbackState === 'loading') {
      return `${ttsStore.activeSourceLabel} · ${ttsStore.announcement}`;
    }
    return ttsStore.announcement;
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

<section
  class:compact
  class:is-loading={ttsStore.playbackState === 'loading'}
  class:is-playing={ttsStore.playbackState === 'playing'}
  class:has-error={Boolean(ttsStore.error)}
  class="audio-player"
  aria-label={label}
>
  <div class:active={ttsStore.isSpeaking} class="voice-orb" aria-hidden="true">
    <span></span>
    <span></span>
    <span></span>
  </div>

  <div class:error={Boolean(ttsStore.error)} class="audio-player-copy">
    <div class="audio-status-row">
      <p>{statusLabel}</p>
      {#if ttsStore.queueCount > 0 && ttsStore.isBusy}
        <span class="tts-queue-chip">+{ttsStore.queueCount}</span>
      {/if}
    </div>
    <small aria-live="polite">{detailLabel}</small>
    <div class="tts-progress" aria-hidden="true" style={progressStyle}></div>
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
