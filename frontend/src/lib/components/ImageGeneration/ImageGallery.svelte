<script lang="ts">
  import { onMount } from 'svelte';
  import { imageGenerationStore, type ImageGalleryItem } from '$lib/stores/imageGenerationStore.svelte';

  interface Props {
    compact?: boolean;
  }

  let { compact = false }: Props = $props();
  let selected: ImageGalleryItem | null = $state(null);

  onMount(() => {
    void imageGenerationStore.loadGallery();
  });

  const openItem = (item: ImageGalleryItem) => {
    selected = item;
  };

  const handleLightboxKeydown = (event: KeyboardEvent) => {
    if (event.key === 'Escape') selected = null;
  };
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
      <p>{imageGenerationStore.error}</p>
      <button type="button" onclick={() => imageGenerationStore.dismissError()}>Dismiss</button>
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
        <article class="gallery-card">
          <button type="button" class="gallery-thumb" onclick={() => openItem(item)} aria-label={`Open generated image: ${item.prompt_summary}`}>
            <img src={item.thumbnailUrls[0] ?? item.imageUrls[0]} alt={item.prompt_summary} loading="lazy" decoding="async" />
          </button>
          <div class="gallery-card-copy">
            <strong>{item.prompt_summary}</strong>
            <span>{item.active_preset.replace('_', ' ')}{item.fallback_used ? ' · 8GB fallback' : ''}{item.saved_to_assets ? ' · saved' : ''}</span>
          </div>
          <div class="gallery-actions" aria-label="Image controls">
            <button type="button" onclick={() => imageGenerationStore.regenerate(item)}>Regenerate</button>
            <button type="button" onclick={() => imageGenerationStore.vary(item)}>Vary</button>
            <button type="button" onclick={() => imageGenerationStore.saveToCharacterAssets(item)}>Save asset</button>
            <button type="button" class="danger" onclick={() => imageGenerationStore.deleteImage(item.job_id)}>Delete</button>
          </div>
        </article>
      {/each}
    </div>
  {/if}
</section>

{#if selected}
  <div class="image-lightbox" role="presentation">
    <button type="button" class="lightbox-backdrop" aria-label="Close image preview" onclick={() => (selected = null)}></button>
    <div class="lightbox-dialog" role="dialog" aria-modal="true" tabindex="-1" aria-label="Generated image preview" onkeydown={handleLightboxKeydown}>
      <button type="button" class="lightbox-close" onclick={() => (selected = null)} aria-label="Close image preview">×</button>
      <img src={selected.imageUrls[0]} alt={selected.prompt_summary} loading="lazy" decoding="async" />
      <div>
        <strong>{selected.prompt_summary}</strong>
        <p>{selected.prompt}</p>
        <div class="gallery-actions">
          <button type="button" onclick={() => imageGenerationStore.regenerate(selected!)}>Regenerate</button>
          <button type="button" onclick={() => imageGenerationStore.vary(selected!)}>Create variation</button>
          <button type="button" onclick={() => imageGenerationStore.saveToCharacterAssets(selected!)}>Save to assets</button>
        </div>
      </div>
    </div>
  </div>
{/if}
