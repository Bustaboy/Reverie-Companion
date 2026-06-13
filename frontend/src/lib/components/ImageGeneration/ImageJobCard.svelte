<script lang="ts">
  import type { ImageGenerationJob } from '$lib/stores/imageGenerationStore.svelte';

  interface Props {
    job: ImageGenerationJob;
    compact?: boolean;
    showPreview?: boolean;
    previewOpen?: boolean;
    onCancel?: (job: ImageGenerationJob) => void;
    onRetry?: (job: ImageGenerationJob) => void;
    onVary?: (job: ImageGenerationJob) => void;
    onDelete?: (job: ImageGenerationJob) => void;
    onSave?: (job: ImageGenerationJob) => void;
  }

  let { job, compact = false, showPreview = true, previewOpen = true, onCancel, onRetry, onVary, onDelete, onSave }: Props = $props();

  const isActive = $derived(job.status === 'queued' || job.status === 'waiting_for_resources' || job.status === 'paused' || job.status === 'running');
  const isCapture = $derived(Boolean(job.moment_capture_id) || job.source === 'moment_capture');
  const isPausedForTTS = $derived(job.status === 'paused' || job.resource_mode === 'paused_for_tts');
  const isLowVram = $derived(job.phase === 'low_vram' || job.resource_mode === 'waiting_for_vram');
  const isDegraded = $derived(Boolean(job.fallback_used) || job.resource_mode === 'degraded' || job.phase === 'oom_fallback');
  const progressPercent = $derived(Math.round(job.progress * 100));
  const progressStyle = $derived(`--image-progress: ${(job.progress * 100).toFixed(1)}%`);
  let previewFailed = $state(false);
  const previewUrl = $derived(job.status === 'completed' && !previewFailed ? job.imageUrls[0] : undefined);
  const completedWithoutPreview = $derived(job.status === 'completed' && (!job.imageUrls[0] || previewFailed));

  const statusLabel = $derived.by(() => {
    if (completedWithoutPreview) return isCapture ? 'Capture metadata saved · output unavailable' : 'Image metadata saved · output unavailable';
    if (job.status === 'completed') return job.fallback_used ? (isCapture ? 'Capture ready · preview preset used' : 'Image ready · lighter 8GB preset used') : (isCapture ? 'Capture ready' : 'Image ready');
    if (job.status === 'failed') return job.error?.message ?? (isCapture ? 'Moment Capture failed — chat and voice were not interrupted' : 'Image generation failed — chat and voice were not interrupted');
    if (job.status === 'cancelled') return isCapture ? 'Moment Capture cancelled' : 'Image generation cancelled';
    if (isPausedForTTS) return isCapture ? 'Capture paused for voice playback' : 'Paused for voice playback';
    if (isLowVram) return isCapture ? 'Capture waiting for VRAM headroom' : 'Waiting for VRAM headroom';
    if (job.status === 'waiting_for_resources') return isCapture ? 'Checking capture resources' : 'Checking local resources';
    if (job.status === 'running') return isCapture ? 'Rendering capture locally' : 'Composing image locally';
    return isCapture ? 'Capture queued behind chat and voice' : 'Queued behind chat and voice';
  });

  const resourceNote = $derived.by(() => {
    if (isPausedForTTS) return 'Voice has priority; capture/image work will resume automatically.';
    if (isLowVram) return isCapture ? 'Reverie is keeping this capture queued rather than risking an 8GB VRAM spike.' : 'Reverie is waiting rather than risking an 8GB VRAM spike.';
    if (job.phase === 'resource_check' && job.resource_mode === 'unknown_vram_preview') {
      return isCapture ? 'VRAM telemetry is unavailable, so Moment Capture is using the preview preset.' : 'VRAM telemetry is unavailable, so Reverie is using the preview preset.';
    }
    if (completedWithoutPreview) return 'The gallery kept the prompt and metadata, but the local output file is not reachable. Regenerate or reopen ComfyUI and retry.';
    if (isDegraded && job.status !== 'completed') return isCapture ? 'Downgraded to preview capture quality to avoid memory pressure.' : 'Using a lighter 8GB-safe preset to avoid memory pressure.';
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
    {:else if job.status === 'completed'}
      <div class="image-job-actions">
        {#if onRetry}<button type="button" class="image-job-action" onclick={() => onRetry?.(job)}>Regenerate</button>{/if}
        {#if onVary}<button type="button" class="image-job-action" onclick={() => onVary?.(job)}>Vary</button>{/if}
        {#if onSave}<button type="button" class="image-job-action" disabled={completedWithoutPreview} onclick={() => onSave?.(job)}>{job.saved_to_assets ? 'Saved' : 'Save asset'}</button>{/if}
        {#if onDelete}<button type="button" class="image-job-action danger" onclick={() => onDelete?.(job)}>Delete</button>{/if}
      </div>
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
    <p class="image-job-error">{job.error?.message ?? (isCapture ? 'Moment Capture failed. Chat and voice were not interrupted.' : 'Image generation failed. Chat and voice were not interrupted.')}</p>
    {#if job.error?.retryable}<small class="image-job-note">Retryable: you can try again; capture metadata stays attached.</small>{/if}
  {:else if job.status === 'cancelled'}
    <small class="image-job-note">{isCapture ? 'Cancelled safely. Capture ID, character ID, and retry context are preserved.' : 'Cancelled safely.'}</small>
  {:else}
    <small class="image-job-note">{resourceNote}</small>
  {/if}

  {#if showPreview && previewUrl}
    <details class="image-job-preview" open={previewOpen}>
      <summary>{job.displayPrompt}</summary>
      <img src={previewUrl} alt={`Generated image for ${job.sourceLabel}: ${job.displayPrompt}`} loading="lazy" decoding="async" onerror={() => (previewFailed = true)} />
    </details>
    <p class="image-job-caption">{job.displayPrompt}</p>
  {:else if completedWithoutPreview}
    <div class="image-job-missing-preview" role="status">
      <strong>Preview unavailable</strong>
      <span>The image metadata is safe, but the generated file cannot be loaded locally.</span>
    </div>
  {/if}
</article>
