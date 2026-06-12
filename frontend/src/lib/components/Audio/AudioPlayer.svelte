<script lang="ts">
  import { settingsStore } from '$lib/stores/settingsStore';
  import { ttsStore } from '$lib/stores/ttsStore.svelte';

  const statusLabel = $derived.by(() => {
    if (ttsStore.status === 'synthesizing') return 'Preparing voice';
    if (ttsStore.status === 'playing') return 'Speaking now';
    if (ttsStore.status === 'paused') return 'Voice paused';
    if (ttsStore.status === 'queued') return 'Voice queued';
    if (ttsStore.status === 'error') return 'Voice paused';
    return 'Voice ready';
  });

  const progressPercent = $derived(Math.round(ttsStore.progress * 100));
  const playPauseLabel = $derived(ttsStore.canPause ? 'Pause voice playback' : 'Resume voice playback');

  const togglePlayPause = () => {
    if (ttsStore.canPause) {
      ttsStore.pause();
      return;
    }

    if (ttsStore.canResume) {
      ttsStore.resume();
    }
  };

  const handleAutoPlayChange = (event: Event) => {
    ttsStore.setAutoPlay((event.currentTarget as HTMLInputElement).checked);
  };
</script>

<aside
  class:speaking={ttsStore.status === 'playing'}
  class:preparing={ttsStore.status === 'synthesizing' || ttsStore.status === 'queued'}
  class="audio-player"
  aria-label="Text-to-speech playback"
>
  <div class="sr-only" aria-live="polite" aria-atomic="true">{ttsStore.liveAnnouncement}</div>

  <div class="voice-orb" aria-hidden="true">
    <span></span><span></span><span></span>
  </div>

  <div class="voice-copy">
    <strong>{statusLabel}</strong>
    <span>{ttsStore.currentItem ? ttsStore.currentVoiceName : 'TTS follows finished companion lines'}</span>
    {#if ttsStore.error}
      <small class="voice-error">{ttsStore.error}</small>
    {/if}
  </div>

  <div class="voice-progress" aria-label={`Voice playback progress ${progressPercent}%`} role="progressbar" aria-valuenow={progressPercent} aria-valuemin="0" aria-valuemax="100">
    <span style={`width: ${progressPercent}%`}></span>
  </div>

  <div class="voice-actions">
    {#if ttsStore.canPause || ttsStore.canResume}
      <button type="button" onclick={togglePlayPause} aria-label={playPauseLabel}>
        {ttsStore.canPause ? 'Pause' : 'Resume'}
      </button>
    {/if}
    {#if ttsStore.isBusy}
      <button type="button" class="subtle" onclick={() => ttsStore.cancel()} aria-label="Stop voice playback">Stop</button>
    {/if}
    {#if ttsStore.error}
      <button type="button" class="subtle" onclick={() => ttsStore.clearError()} aria-label="Dismiss voice playback error">Dismiss</button>
    {/if}
  </div>

  <label class="tts-autoplay-toggle">
    <input type="checkbox" checked={$settingsStore.ttsAutoPlay} disabled={!$settingsStore.ttsEnabled} onchange={handleAutoPlayChange} />
    <span>Auto-play TTS</span>
  </label>
</aside>
