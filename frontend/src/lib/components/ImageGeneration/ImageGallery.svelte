<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { imageGenerationStore, type ImageGalleryItem } from '$lib/stores/imageGenerationStore.svelte';

  interface Props {
    compact?: boolean;
  }

  let { compact = false }: Props = $props();
  let selected: ImageGalleryItem | null = $state(null);
  let unavailableImages = $state<string[]>([]);
  let lightboxElement = $state<HTMLElement>();

  onMount(() => {
    void imageGenerationStore.loadGallery();
  });

  const firstImageUrl = (item: ImageGalleryItem): string | undefined => item.thumbnailUrls[0] ?? item.imageUrls[0];

  const imageUnavailable = (item: ImageGalleryItem): boolean =>
    !firstImageUrl(item) || unavailableImages.includes(item.job_id);

  const markImageUnavailable = (item: ImageGalleryItem) => {
    if (!unavailableImages.includes(item.job_id)) unavailableImages = [...unavailableImages, item.job_id];
  };

  const openItem = (item: ImageGalleryItem) => {
    selected = item;
  };

  const closeLightbox = () => {
    selected = null;
  };

  const handleLightboxKeydown = (event: KeyboardEvent) => {
    if (event.key === 'Escape') closeLightbox();
  };

  $effect(() => {
    if (!selected) return;

    // Keep lightbox focus inside the surfaced preview for predictable keyboard
    // dismissal and immediate screen reader context.
    void tick().then(() => lightboxElement?.focus());
  });
</script>

<section class:compact class="image-gallery-panel" aria-label="Image history gallery">
  <div class="gallery-header">
    <div>
      <p class="eyebrow">Image history</p>
      <h2>Conversation gallery</h2>
      <span>{imageGenerationStore.resourceAwarenessLabel}</span>
    </div>
    <button type="button" class="ghost-button" onclick={() => imageGenerationStore.loadGallery()} disabled={imageGenerationStore.galleryLoading}>
      {imageGenerationStore.galleryLoading ? 'Refreshing…' : 'Refresh'}
    </button>
  </div>

  {#if imageGenerationStore.error}
    <div class="gallery-error" role="status">
      <div>
        <strong>Image gallery needs attention</strong>
        <p>{imageGenerationStore.error}</p>
      </div>
      <div class="gallery-actions">
        <button type="button" onclick={() => imageGenerationStore.loadGallery()}>Retry</button>
        <button type="button" onclick={() => imageGenerationStore.dismissError()}>Dismiss</button>
      </div>
    </div>
  {/if}

  {#if imageGenerationStore.galleryLoading}
    <div class="gallery-empty" aria-live="polite">Loading saved image metadata without preloading full images…</div>
  {:else if imageGenerationStore.gallery.length === 0}
    <div class="gallery-empty">
      <strong>No images yet.</strong>
      <span>Generate from chat or Visual Novel mode and completed results will appear here per conversation.</span>
    </div>
  {:else}
    <div class="gallery-grid">
      {#each imageGenerationStore.gallery as item (item.job_id)}
        <article class:output-missing={imageUnavailable(item)} class="gallery-card">
          <button type="button" class="gallery-thumb" onclick={() => openItem(item)} aria-label={`Open generated image: ${item.prompt_summary}`}>
            {#if imageUnavailable(item)}
              <span class="gallery-thumb-fallback" aria-hidden="true">✦</span>
            {:else}
              <img src={firstImageUrl(item)} alt={item.prompt_summary} loading="lazy" decoding="async" onerror={() => markImageUnavailable(item)} />
            {/if}
          </button>
          <div class="gallery-card-copy">
            <strong>{item.prompt_summary}</strong>
            <span>{item.active_preset.replace('_', ' ')}{item.fallback_used ? ' · 8GB fallback' : ''}{item.saved_to_assets ? ' · saved' : ''}</span>
            {#if imageUnavailable(item)}
              <small>Output file is not available from the local image service. Regenerate or reopen ComfyUI, then retry.</small>
            {/if}
          </div>
          <div class="gallery-actions" aria-label="Image controls">
            <button type="button" onclick={() => imageGenerationStore.regenerate(item)}>Regenerate</button>
            <button type="button" onclick={() => imageGenerationStore.vary(item)}>Vary</button>
            <button type="button" onclick={() => imageGenerationStore.saveToCharacterAssets(item)} disabled={imageUnavailable(item)}>{item.saved_to_assets ? 'Saved' : 'Save asset'}</button>
            <button type="button" class="danger" onclick={() => imageGenerationStore.deleteImage(item.job_id)}>Delete</button>
          </div>
        </article>
      {/each}
    </div>
  {/if}
</section>

{#if selected}
  <div class="image-lightbox" role="presentation">
    <button type="button" class="lightbox-backdrop" aria-label="Close image preview" onclick={closeLightbox}></button>
    <div bind:this={lightboxElement} class="lightbox-dialog" role="dialog" aria-modal="true" tabindex="-1" aria-labelledby="lightbox-title" aria-describedby="lightbox-description" onkeydown={handleLightboxKeydown}>
      <button type="button" class="lightbox-close" onclick={closeLightbox} aria-label="Close image preview">×</button>
      {#if imageUnavailable(selected)}
        <div class="lightbox-missing" role="status">
          <strong>Image file unavailable</strong>
          <p>The gallery still has the prompt and metadata, but the generated file is not reachable locally. Regenerate or reopen ComfyUI, then refresh.</p>
        </div>
      {:else}
        <img src={selected.imageUrls[0]} alt={selected.prompt_summary} loading="lazy" decoding="async" onerror={() => markImageUnavailable(selected!)} />
      {/if}
      <div>
        <strong id="lightbox-title">{selected.prompt_summary}</strong>
        <p id="lightbox-description">{selected.prompt}</p>
        <div class="gallery-actions">
          <button type="button" onclick={() => imageGenerationStore.regenerate(selected!)}>Regenerate</button>
          <button type="button" onclick={() => imageGenerationStore.vary(selected!)}>Create variation</button>
          <button type="button" onclick={() => imageGenerationStore.saveToCharacterAssets(selected!)} disabled={imageUnavailable(selected)}>Save to assets</button>
        </div>
      </div>
    </div>
  </div>
{/if}
