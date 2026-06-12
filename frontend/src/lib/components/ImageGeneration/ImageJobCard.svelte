<script lang="ts">
  import { imageGenerationStore, type ImageGenerationJob } from '$lib/stores/imageGenerationStore.svelte';

  interface Props {
    job: ImageGenerationJob;
    compact?: boolean;
  }

  let { job, compact = false }: Props = $props();

  const isTerminal = $derived(job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled');
  const isExpandable = $derived(job.status === 'completed' && job.outputUrls.length > 0);
  const expanded = $derived(imageGenerationStore.expandedJobId === job.id || (compact && isExpandable));
  const progressPercent = $derived(`${Math.round(job.progress * 100)}%`);
  const resourceCopy = $derived.by(() => {
    if (job.resourceMode === 'paused_for_tts') return 'Paused for voice';
    if (job.resourceMode === 'waiting_for_vram') return 'Waiting for VRAM';
    if (job.fallbackUsed) return `Using ${job.activePreset.replace('_', ' ')}`;
    return job.activePreset.replace('_', ' ');
  });
</script>

<article class:compact class:error={job.status === 'failed'} class:complete={job.status === 'completed'} class="image-job-card">
  <div class="image-job-header">
    <div>
      <strong>{job.title}</strong>
      <span>{job.message}</span>
    </div>

    {#if !isTerminal}
      <button type="button" class="image-cancel-button" onclick={() => imageGenerationStore.cancel(job.id)}>Cancel</button>
    {:else if isExpandable && !compact}
      <button type="button" class="image-cancel-button" aria-expanded={expanded} onclick={() => imageGenerationStore.toggleExpanded(job.id)}>
        {expanded ? 'Collapse' : 'Expand'}
      </button>
    {/if}
  </div>

  {#if job.status !== 'completed'}
    <div class="image-progress" aria-label={`Image generation progress ${progressPercent}`}>
      <span style={`width: ${progressPercent}`}></span>
    </div>
  {/if}

  <div class="image-job-meta">
    <span>{resourceCopy}</span>
    {#if job.vramFreeMb !== null && job.vramFreeMb !== undefined && job.vramRequiredMb}
      <span>{job.vramFreeMb} MB free / {job.vramRequiredMb} MB needed</span>
    {/if}
  </div>

  {#if job.error}
    <p class="image-job-error">{job.error}</p>
  {/if}

  {#if expanded && job.outputUrls[0]}
    <figure class="generated-image-frame">
      <img src={job.outputUrls[0]} alt={`Generated visualization: ${job.prompt}`} loading="lazy" decoding="async" />
      <figcaption>{job.prompt}</figcaption>
    </figure>
  {/if}
</article>
