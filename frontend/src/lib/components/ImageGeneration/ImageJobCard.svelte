<script lang="ts">
  import type { ImageGenerationJob } from '$lib/stores/imageGenerationStore.svelte';

  interface Props {
    job: ImageGenerationJob;
    compact?: boolean;
    showPreview?: boolean;
    previewOpen?: boolean;
    onCancel?: (job: ImageGenerationJob) => void;
    onRetry?: (job: ImageGenerationJob) => void;
  }

  let { job, compact = false, showPreview = true, previewOpen = true, onCancel, onRetry }: Props = $props();

  const isActive = $derived(job.status === 'queued' || job.status === 'waiting_for_resources' || job.status === 'paused' || job.status === 'running');
  const isPausedForTTS = $derived(job.status === 'paused' || job.resource_mode === 'paused_for_tts');
  const isLowVram = $derived(job.phase === 'low_vram' || job.resource_mode === 'waiting_for_vram');
  const isDegraded = $derived(Boolean(job.fallback_used) || job.resource_mode === 'degraded' || job.phase === 'oom_fallback');
  const progressPercent = $derived(Math.round(job.progress * 100));
  const progressStyle = $derived(`--image-progress: ${(job.progress * 100).toFixed(1)}%`);
  const previewUrl = $derived(job.status === 'completed' ? job.imageUrls[0] : undefined);

  const statusLabel = $derived.by(() => {
    if (job.status === 'completed') return job.fallback_used ? 'Image ready · lighter 8GB preset used' : 'Image ready';
    if (job.status === 'failed') return job.error?.message ?? 'Image generation failed';
    if (job.status === 'cancelled') return 'Image generation cancelled';
    if (isPausedForTTS) return 'Paused for voice playback';
    if (isLowVram) return 'Waiting for VRAM headroom';
    if (job.status === 'waiting_for_resources') return 'Checking local resources';
    if (job.status === 'running') return 'Composing image locally';
    return 'Queued behind chat and voice';
  });

  const resourceNote = $derived.by(() => {
    if (isPausedForTTS) return 'Voice has priority; the image worker will resume automatically.';
    if (isLowVram) return 'Reverie is waiting rather than risking an 8GB VRAM spike.';
    if (job.phase === 'resource_check' && job.resource_mode === 'unknown_vram_preview') {
      return 'VRAM telemetry is unavailable, so Reverie is using the preview preset.';
    }
    if (isDegraded && job.status !== 'completed') return 'Using a lighter 8GB-safe preset to avoid memory pressure.';
    if (job.vram_free_mb !== null && job.vram_free_mb !== undefined && job.vram_required_mb) {
      return `${job.vram_free_mb} MiB free · ${job.vram_required_mb} MiB target.`;
    }
    return job.message;
  });

  const stateClass = $derived(
    isPausedForTTS
      ? 'paused-for-tts'
      : isLowVram
        ? 'low-vram'
        : isDegraded
          ? 'degraded'
          : job.status
  );
</script>

<article
  class:compact
  class:active={isActive}
  class:terminal={job.status === 'completed'}
  class:failed={job.status === 'failed'}
  class={`image-job-card image-job-${stateClass}`}
  aria-live={isActive ? 'polite' : undefined}
>
  <div class="image-job-topline">
    <div>
      <strong>{job.sourceLabel}</strong>
      <span>{statusLabel}</span>
    </div>

    {#if isActive && onCancel}
      <button type="button" class="image-job-action" onclick={() => onCancel?.(job)}>Cancel</button>
    {:else if job.status === 'failed' && onRetry}
      <button type="button" class="image-job-action" onclick={() => onRetry?.(job)}>Try again</button>
    {/if}
  </div>

  {#if isActive}
    <div class="image-job-progress-row">
      <div class="image-job-progress" aria-label={`Image generation progress ${progressPercent} percent`} style={progressStyle}>
        <span></span>
      </div>
      <small>{progressPercent}%</small>
    </div>
  {/if}

  {#if job.status === 'failed'}
    <p class="image-job-error">{job.error?.message ?? 'Image generation failed. Chat and voice were not interrupted.'}</p>
  {:else if job.status !== 'cancelled'}
    <small class="image-job-note">{resourceNote}</small>
  {/if}

  {#if showPreview && previewUrl}
    <details class="image-job-preview" open={previewOpen}>
      <summary>View generated image</summary>
      <img src={previewUrl} alt={`Generated image for ${job.sourceLabel}: ${job.displayPrompt}`} loading="lazy" decoding="async" />
    </details>
  {/if}
</article>
