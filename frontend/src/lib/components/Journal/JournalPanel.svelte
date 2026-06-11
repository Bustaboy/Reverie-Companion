<script lang="ts">
  import Markdown from '$lib/components/Chat/Markdown.svelte';
  import { journalStore } from '$lib/stores/journalStore';
  import type { JournalEntry, JournalInsight } from '$lib/types/journal';

  const selectedEntry = $derived(
    $journalStore.entries.find((entry) => entry.entry_id === $journalStore.selectedEntryId) ?? $journalStore.entries[0] ?? null
  );
  const isLoading = $derived($journalStore.loadState === 'loading');
  const isRefreshing = $derived($journalStore.loadState === 'refreshing');

  const formatEntryDate = (value?: string) => {
    if (!value) return 'Undated reflection';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Undated reflection';
    return new Intl.DateTimeFormat(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    }).format(date);
  };

  const formatShortDate = (value?: string) => {
    if (!value) return 'Undated';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Undated';
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(date);
  };

  const asPercent = (value?: number) => `${Math.round(clamp01(value ?? 0) * 100)}%`;
  const insightLabel = (insight: JournalInsight) => (insight.kind ?? 'insight').replaceAll('_', ' ');

  const entryTitle = (entry: JournalEntry) => {
    const themes = entry.themes?.filter(Boolean) ?? [];
    if (themes.length > 0) return themes.slice(0, 3).map(capitalize).join(' · ');
    return 'Quiet reflection';
  };

  const entryPreview = (entry: JournalEntry) =>
    entry.character_summary?.trim() || entry.insights?.find((insight) => insight.summary)?.summary || 'A private note is waiting here.';

  const promotionStatus = (entry: JournalEntry) => {
    const promotion = entry.metadata?.memory_promotion;
    if (promotion?.promoted === true || promotion?.promoted_memory_id || (entry.linked_memory_ids?.length ?? 0) > 0) {
      return 'Promoted to memory';
    }
    if (promotion?.should_promote === true) return 'Ready for memory review';
    return 'Kept as journal only';
  };

  const trainingLabel = (value?: string) => {
    if (value === 'eligible') return 'Eligible with consent';
    if (value === 'needs_review') return 'Needs review';
    return 'Not used for training';
  };

  const refresh = () => journalStore.refresh();
  const select = (entryId: string) => journalStore.selectEntry(entryId);

  function clamp01(value: number) {
    return Math.min(Math.max(value, 0), 1);
  }

  function capitalize(value: string) {
    return value.charAt(0).toUpperCase() + value.slice(1);
  }
</script>

<section class="journal-panel" aria-label="Self-Reflection Journal">
  <header class="journal-hero">
    <div>
      <p class="eyebrow">Self-reflection journal</p>
      <h1>Private thoughts, softly kept.</h1>
      <p class="subtitle">
        Recent reflections from the companion's local journal — tender continuity signals before they become lasting memory.
      </p>
    </div>

    <button class="refresh-button" type="button" onclick={refresh} disabled={isLoading || isRefreshing}>
      <span aria-hidden="true">↻</span>
      {isRefreshing ? 'Refreshing…' : 'Refresh'}
    </button>
  </header>

  {#if $journalStore.error}
    <div class="journal-error" role="status" aria-live="polite">
      <div>
        <strong>The journal stayed closed for a moment.</strong>
        <span>{$journalStore.error}</span>
      </div>
      <button type="button" onclick={refresh}>Try again</button>
    </div>
  {/if}

  {#if isLoading}
    <div class="journal-empty" role="status" aria-live="polite">
      <div class="journal-orb"></div>
      <strong>Opening the journal…</strong>
      <span>Reverie is reading the latest local reflections.</span>
    </div>
  {:else if $journalStore.entries.length === 0}
    <div class="journal-empty">
      <div class="journal-orb"></div>
      <strong>No reflections yet.</strong>
      <span>After meaningful conversations, the companion's thoughts will gather here as warm, inspectable journal entries.</span>
    </div>
  {:else}
    <div class="journal-layout">
      <aside class="journal-entry-list" aria-label="Journal entries">
        {#each $journalStore.entries as entry (entry.entry_id)}
          <button
            type="button"
            class:active={selectedEntry?.entry_id === entry.entry_id}
            onclick={() => select(entry.entry_id)}
          >
            <span class="entry-date">{formatShortDate(entry.created_at)}</span>
            <strong>{entryTitle(entry)}</strong>
            <small>{entryPreview(entry)}</small>
            <span class="entry-meta-row">
              <span>{asPercent(entry.confidence)} confidence</span>
              <span>{promotionStatus(entry)}</span>
            </span>
          </button>
        {/each}
      </aside>

      {#if selectedEntry}
        <article class="journal-viewer" aria-label="Selected journal reflection">
          <div class="journal-paper">
            <div class="journal-paper-header">
              <div>
                <p class="entry-date full">{formatEntryDate(selectedEntry.created_at)}</p>
                <h2>{entryTitle(selectedEntry)}</h2>
              </div>
              <div class="confidence-ring" aria-label={`Confidence ${asPercent(selectedEntry.confidence)}`}>
                <strong>{asPercent(selectedEntry.confidence)}</strong>
                <span>confidence</span>
              </div>
            </div>

            <div class="reflection-prose">
              <Markdown content={selectedEntry.character_summary || 'This reflection has no prose yet.'} />
            </div>

            {#if selectedEntry.insights?.length}
              <section class="insight-section" aria-labelledby="journal-insights-heading">
                <h3 id="journal-insights-heading">What she noticed</h3>
                <div class="insight-grid">
                  {#each selectedEntry.insights as insight}
                    <div class="insight-card">
                      <span>{insightLabel(insight)}</span>
                      <p>{insight.summary}</p>
                      <small>{asPercent(insight.confidence)} · {insight.evidence_count ?? 0} evidence points</small>
                    </div>
                  {/each}
                </div>
              </section>
            {/if}

            <section class="metadata-section" aria-labelledby="journal-metadata-heading">
              <h3 id="journal-metadata-heading">Quiet metadata</h3>
              <div class="metadata-grid">
                <div>
                  <span>Memory</span>
                  <strong>{promotionStatus(selectedEntry)}</strong>
                </div>
                <div>
                  <span>Training</span>
                  <strong>{trainingLabel(selectedEntry.training_eligibility)}</strong>
                </div>
                <div>
                  <span>Intensity</span>
                  <strong>{asPercent(selectedEntry.emotional_intensity)}</strong>
                </div>
                <div>
                  <span>Evidence</span>
                  <strong>{selectedEntry.evidence_count ?? 0} turns</strong>
                </div>
              </div>

              {#if selectedEntry.themes?.length || selectedEntry.privacy_tags?.length || selectedEntry.sensitivity_tags?.length}
                <div class="tag-cloud" aria-label="Journal tags">
                  {#each [...(selectedEntry.themes ?? []), ...(selectedEntry.privacy_tags ?? []), ...(selectedEntry.sensitivity_tags ?? [])] as tag}
                    <span>{tag.replaceAll('_', ' ')}</span>
                  {/each}
                </div>
              {/if}
            </section>
          </div>
        </article>
      {/if}
    </div>
  {/if}
</section>
