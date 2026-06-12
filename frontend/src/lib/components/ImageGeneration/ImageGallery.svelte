<script lang="ts">
  import ImageJobCard from './ImageJobCard.svelte';
  import { imageGenerationStore, type ImageGenerationJob } from '$lib/stores/imageGenerationStore.svelte';

  const closeGallery = () => imageGenerationStore.setGalleryOpen(false);
  const regenerate = (job: ImageGenerationJob) => imageGenerationStore.regenerate(job);
  const vary = (job: ImageGenerationJob) => imageGenerationStore.vary(job);
  const save = (job: ImageGenerationJob) => imageGenerationStore.saveToCharacterAssets(job);
  const remove = (job: ImageGenerationJob) => void imageGenerationStore.deleteJob(job.job_id);
  const retry = (job: ImageGenerationJob) => imageGenerationStore.regenerate(job);
</script>

{#if imageGenerationStore.galleryOpen}
  <div class="image-gallery-backdrop" role="presentation" onclick={closeGallery}></div>
  <div class="image-gallery-panel" role="dialog" aria-modal="true" aria-labelledby="image-gallery-title">
    <header class="image-gallery-header">
      <div>
        <p class="eyebrow">Conversation image history</p>
        <h2 id="image-gallery-title">Gallery</h2>
        <p>Generated images are stored with prompt, source, preset, and status metadata for this local conversation.</p>
      </div>
      <button type="button" class="ghost-button" onclick={closeGallery}>Close</button>
    </header>

    {#if imageGenerationStore.galleryJobs.length === 0}
      <div class="image-gallery-empty">
        <strong>No images yet</strong>
        <p>Generate from chat or Visual Novel mode and completed results will appear here.</p>
      </div>
    {:else}
      <div class="image-gallery-grid" aria-live="polite">
        {#each imageGenerationStore.galleryJobs as job (job.job_id)}
          <article class="image-gallery-item">
            <ImageJobCard {job} previewOpen={false} onRetry={retry} />
            <div class="image-gallery-actions" aria-label="Image controls">
              <button type="button" onclick={() => regenerate(job)}>Regenerate</button>
              <button type="button" onclick={() => vary(job)}>Vary</button>
              <button type="button" disabled={job.status !== 'completed' || job.savedToCharacterAssets} onclick={() => save(job)}>
                {job.savedToCharacterAssets ? 'Saved' : 'Save to assets'}
              </button>
              <button type="button" class="danger" onclick={() => remove(job)}>Delete</button>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </div>
{/if}
