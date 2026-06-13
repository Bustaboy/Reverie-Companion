<script lang="ts">
  import { onMount } from 'svelte';
  import { imageGenerationStore, type ImageGalleryItem } from '$lib/stores/imageGenerationStore.svelte';

  interface Props {
    compact?: boolean;
  }

  let { compact = false }: Props = $props();
  let selected: ImageGalleryItem | null = $state(null);
  let unavailableImages = $state<string[]>([]);
  let expandedTraitFeedbackFor = $state<string | null>(null);
  let traitFeedback = $state<Record<string, { name: string; value: string; note: string }>>({});

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

  const characterLabel = (item: ImageGalleryItem): string | null => {
    const name = typeof item.metadata?.character_name === 'string' ? item.metadata.character_name : null;
    return name ?? item.character_id ?? null;
  };

  const reviewClass = (status?: string): string => {
    if (status === 'canonized' || status === 'accepted' || status === 'looks_right') return 'approved';
    if (status === 'rejected' || status === 'wrong_appearance') return 'rejected';
    if (status === 'canon_requested' || status === 'proposed') return 'pending';
    return 'neutral';
  };

  const askTrait = (fallback: string): string | null => {
    const value = globalThis.prompt?.('Which appearance/style trait should Reverie remember?', fallback);
    const trimmed = value?.trim();
    return trimmed ? trimmed : null;
  };

  const traitDraft = (jobId: string) => traitFeedback[jobId] ?? { name: '', value: '', note: '' };

  const updateTraitDraft = (jobId: string, patch: Partial<{ name: string; value: string; note: string }>) => {
    traitFeedback = { ...traitFeedback, [jobId]: { ...traitDraft(jobId), ...patch } };
  };

  const toggleTraitFeedback = (jobId: string) => {
    expandedTraitFeedbackFor = expandedTraitFeedbackFor === jobId ? null : jobId;
  };

  const sendDetailedTraitFeedback = (item: ImageGalleryItem, action: 'wrong_appearance' | 'reject_style_trait') => {
    const draft = traitDraft(item.job_id);
    const traitName = draft.name.trim();
    const traitValue = draft.value.trim();
    const note = draft.note.trim();
    const fallback = action === 'wrong_appearance' ? 'appearance mismatch' : 'style trait to avoid';
    const usableTrait = traitValue || traitName;
    if (!usableTrait) return;
    void imageGenerationStore.submitGalleryFeedback(item, action, {
      traitName: traitName || fallback,
      traitValue: usableTrait,
      note: note || undefined
    });
  };

  const sendFeedback = (item: ImageGalleryItem, action: Parameters<typeof imageGenerationStore.submitGalleryFeedback>[1]) => {
    if (action === 'wrong_appearance' || action === 'reject_style_trait') {
      const trait = askTrait(action === 'wrong_appearance' ? 'appearance mismatch' : 'style trait to avoid');
      if (!trait) return;
      void imageGenerationStore.submitGalleryFeedback(item, action, { traitName: trait, traitValue: trait });
      return;
    }
    void imageGenerationStore.submitGalleryFeedback(item, action);
  };

  const statusChips = (item: ImageGalleryItem): string[] => {
    const chips: string[] = [];
    if (item.moment_capture_id) chips.push('Moment Capture');
    if (item.feedback_status && item.feedback_status !== 'pending') chips.push(`Feedback: ${item.feedback_status.replaceAll('_', ' ')}`);
    if (item.review_status && item.review_status !== 'unreviewed') chips.push(`Review: ${item.review_status.replaceAll('_', ' ')}`);
    if (item.canon_status && item.canon_status !== 'not_requested') chips.push(`Canon: ${item.canon_status.replaceAll('_', ' ')}`);
    if (item.saved_to_assets) chips.push('Saved asset');
    return chips;
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
        <article class:output-missing={imageUnavailable(item)} class={`gallery-card review-${reviewClass(item.review_status ?? item.canon_status ?? item.feedback_status)}`}>
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
            {#if characterLabel(item)}
              <small>Character: {characterLabel(item)}</small>
            {/if}
            <small>Source: {item.source ?? 'generated'}{item.source_message_id ? ` · message ${item.source_message_id}` : ''}{item.session_id ? ` · session ${item.session_id}` : ''}</small>
            {#if item.scene_summary}
              <small>Scene: {item.scene_summary}</small>
            {/if}
            {#if item.prompt_hash}
              <small>Prompt hash: {item.prompt_hash}</small>
            {/if}
            {#if statusChips(item).length}
              <small class="gallery-status-chips">{statusChips(item).join(' · ')}</small>
            {:else}
              <small class="gallery-status-chips">Review: unreviewed · Canon: not requested</small>
            {/if}
            {#if imageUnavailable(item)}
              <small>Output file is not available from the local image service. Regenerate or reopen ComfyUI, then retry.</small>
            {/if}
          </div>
          <div class="gallery-feedback-actions" aria-label="Visual continuity feedback">
            <button type="button" onclick={() => sendFeedback(item, 'looks_right')} disabled={!item.moment_capture_id || imageGenerationStore.feedbackSubmitting[item.job_id]}>Looks Right</button>
            <button type="button" onclick={() => sendFeedback(item, 'use_outfit_again')} disabled={!item.moment_capture_id || imageGenerationStore.feedbackSubmitting[item.job_id]}>Use Outfit Again</button>
            <button type="button" onclick={() => sendFeedback(item, 'wrong_appearance')} disabled={!item.moment_capture_id || imageGenerationStore.feedbackSubmitting[item.job_id]}>Wrong Appearance</button>
            <button type="button" onclick={() => sendFeedback(item, 'make_canon')} disabled={!item.moment_capture_id || imageGenerationStore.feedbackSubmitting[item.job_id]}>Make Canon</button>
            <button type="button" onclick={() => sendFeedback(item, 'just_this_scene')} disabled={!item.moment_capture_id || imageGenerationStore.feedbackSubmitting[item.job_id]}>Just This Scene</button>
            <button type="button" onclick={() => sendFeedback(item, 'reject_style_trait')} disabled={!item.moment_capture_id || imageGenerationStore.feedbackSubmitting[item.job_id]}>Reject Style Trait</button>
            <button type="button" class="secondary" onclick={() => toggleTraitFeedback(item.job_id)} disabled={!item.moment_capture_id}>{expandedTraitFeedbackFor === item.job_id ? 'Hide Details' : 'Trait Details'}</button>
          </div>
          {#if expandedTraitFeedbackFor === item.job_id}
            <div class="gallery-trait-feedback" aria-label="Detailed trait feedback">
              <label>
                <span>Trait</span>
                <input type="text" value={traitDraft(item.job_id).name} placeholder="Hair color, eye color, outfit, style…" oninput={(event) => updateTraitDraft(item.job_id, { name: event.currentTarget.value })} />
              </label>
              <label>
                <span>Correction</span>
                <input type="text" value={traitDraft(item.job_id).value} placeholder="What should Reverie remember or avoid?" oninput={(event) => updateTraitDraft(item.job_id, { value: event.currentTarget.value })} />
              </label>
              <label>
                <span>Optional note</span>
                <textarea rows="2" value={traitDraft(item.job_id).note} placeholder="Add context for review…" oninput={(event) => updateTraitDraft(item.job_id, { note: event.currentTarget.value })}></textarea>
              </label>
              <div class="gallery-actions">
                <button type="button" onclick={() => sendDetailedTraitFeedback(item, 'wrong_appearance')} disabled={!traitDraft(item.job_id).name.trim() && !traitDraft(item.job_id).value.trim()}>Submit Wrong Appearance</button>
                <button type="button" onclick={() => sendDetailedTraitFeedback(item, 'reject_style_trait')} disabled={!traitDraft(item.job_id).name.trim() && !traitDraft(item.job_id).value.trim()}>Submit Reject Trait</button>
              </div>
            </div>
          {/if}
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

  <aside class="visual-review-panel" aria-label="Pending visual canon changes">
    <div class="review-panel-header">
      <div>
        <p class="eyebrow">Visual review</p>
        <strong>Pending canon changes</strong>
      </div>
      <button type="button" class="ghost-button" onclick={() => imageGenerationStore.loadVisualChanges()} disabled={imageGenerationStore.visualChangesLoading}>
        {imageGenerationStore.visualChangesLoading ? 'Checking…' : 'Refresh review'}
      </button>
    </div>
    {#if imageGenerationStore.visualChanges.length === 0}
      <p>No pending visual changes. Make Canon or Use Outfit Again from a Moment Capture to review one here.</p>
    {:else}
      <div class="visual-review-list">
        {#each imageGenerationStore.visualChanges as event (event.event_id)}
          <article class={`visual-review-card review-${reviewClass(event.canon_status)}`}>
            <strong>{event.changed_trait.replaceAll('_', ' ')}</strong>
            <span>{event.new_value}</span>
            <small>Status: {event.canon_status.replaceAll('_', ' ')} · Character: {event.character_id}</small>
            <small>{event.reason}</small>
            <div class="gallery-actions">
              {#if event.canon_status === 'proposed'}
                <button type="button" onclick={() => imageGenerationStore.reviewVisualChange(event, 'approve')}>Approve</button>
                <button type="button" onclick={() => imageGenerationStore.reviewVisualChange(event, 'reject')}>Reject</button>
              {/if}
              {#if event.canon_status === 'canonized' && event.rollback_available}
                <button type="button" onclick={() => imageGenerationStore.reviewVisualChange(event, 'rollback')}>Rollback</button>
              {/if}
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </aside>
</section>

{#if selected}
  <div class="image-lightbox" role="presentation">
    <button type="button" class="lightbox-backdrop" aria-label="Close image preview" onclick={closeLightbox}></button>
    <div class="lightbox-dialog" role="dialog" aria-modal="true" tabindex="-1" aria-label="Generated image preview" onkeydown={handleLightboxKeydown}>
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
        <strong>{selected.prompt_summary}</strong>
        <p>{selected.prompt}</p>
        {#if characterLabel(selected)}<p>Character: {characterLabel(selected)}</p>{/if}
        {#if selected.scene_summary}<p>Scene: {selected.scene_summary}</p>{/if}
        <p>Source: {selected.source ?? 'generated'}{selected.source_message_id ? ` · message ${selected.source_message_id}` : ''}{selected.moment_capture_id ? ` · capture ${selected.moment_capture_id}` : ''}</p>
        {#if statusChips(selected).length}<p>{statusChips(selected).join(' · ')}</p>{/if}
        <div class="gallery-actions">
          <button type="button" onclick={() => imageGenerationStore.regenerate(selected!)}>Regenerate</button>
          <button type="button" onclick={() => imageGenerationStore.vary(selected!)}>Create variation</button>
          <button type="button" onclick={() => imageGenerationStore.saveToCharacterAssets(selected!)} disabled={imageUnavailable(selected)}>Save to assets</button>
        </div>
      </div>
    </div>
  </div>
{/if}
