<script lang="ts">
  import { onMount } from 'svelte';
  import { journalStore } from '$lib/stores/journalStore';
  import type { JournalEntry, ReflectionInsight } from '$lib/types/journal';

  const selectedEntry = $derived(
    $journalStore.entries.find((entry) => entry.entry_id === $journalStore.selectedEntryId) ?? null
  );
  const isLoading = $derived($journalStore.loadState === 'loading');
  const isRefreshing = $derived($journalStore.loadState === 'refreshing');
  const hasEntries = $derived($journalStore.entries.length > 0);

  onMount(() => {
    void journalStore.loadEntries();
  });

  const refreshJournal = () => {
    void journalStore.refresh();
  };

  const selectEntry = (entryId: string) => {
    journalStore.selectEntry(entryId);
  };

  const formatEntryDate = (value: string | undefined, style: 'short' | 'long' = 'short') => {
    if (!value) return 'Undated reflection';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Undated reflection';

    return new Intl.DateTimeFormat(undefined, {
      month: style === 'long' ? 'long' : 'short',
      day: 'numeric',
      year: 'numeric',
      hour: style === 'long' ? 'numeric' : undefined,
      minute: style === 'long' ? '2-digit' : undefined
    }).format(date);
  };

  const percent = (value: number | undefined) => `${Math.round((value ?? 0) * 100)}%`;

  const titleFor = (entry: JournalEntry) => {
    const themes = entry.themes?.slice(0, 2).map(labelFor).join(' + ');
    return themes ? `A note on ${themes}` : 'Private reflection';
  };

  const labelFor = (value: string | undefined) =>
    (value ?? 'unknown')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());

  const promotionLabel = (entry: JournalEntry) => {
    const decision = entry.metadata?.memory_promotion;
    if (decision?.should_promote) return 'Promoted to memory';
    if (entry.linked_memory_ids?.length) return 'Linked to memory';
    return 'Kept as journal only';
  };

  const entryPreview = (entry: JournalEntry) =>
    entry.character_summary || entry.insights?.[0]?.summary || 'A quiet reflection is waiting to be read.';

  const insightKey = (insight: ReflectionInsight, index: number) => `${insight.kind ?? 'insight'}-${index}`;
</script>

<section class="journal-panel" aria-label="Self-reflection journal">
  <header class="journal-header">
    <div>
      <p class="eyebrow">Self-reflection journal</p>
      <h1>Private thoughts, kept gently</h1>
      <p class="subtitle">
        Recent reflections from the character’s local growth loop — readable, inspectable, and still under your care.
      </p>
    </div>

    <button class="ghost-button" type="button" onclick={refreshJournal} disabled={isLoading || isRefreshing}>
      {isRefreshing ? 'Refreshing…' : 'Refresh'}
    </button>
  </header>

  {#if $journalStore.error}
    <div class="journal-notice" role="status">
      <strong>The journal stayed closed for a moment.</strong>
      <span>{$journalStore.error}</span>
    </div>
  {/if}

  {#if isLoading}
    <div class="journal-empty" aria-live="polite">
      <div class="journal-empty-mark">✦</div>
      <h2>Opening the journal…</h2>
      <p>Reverie is gathering the latest local reflections.</p>
    </div>
  {:else if !hasEntries}
    <div class="journal-empty">
      <div class="journal-empty-mark">♡</div>
      <h2>No reflections yet</h2>
      <p>After meaningful conversations, Reverie will write gentle first-person reflections here.</p>
      <button class="ghost-button" type="button" onclick={refreshJournal}>Check again</button>
    </div>
  {:else}
    <div class="journal-content">
      <aside class="journal-list" aria-label="Journal entries">
        {#each $journalStore.entries as entry (entry.entry_id)}
          <button
            class:active={entry.entry_id === $journalStore.selectedEntryId}
            class="journal-entry-card"
            type="button"
            onclick={() => selectEntry(entry.entry_id)}
          >
            <span class="journal-entry-date">{formatEntryDate(entry.created_at)}</span>
            <strong>{titleFor(entry)}</strong>
            <span>{entryPreview(entry)}</span>
            <small>{entry.insights?.length ?? 0} insights · {percent(entry.confidence)} confidence</small>
          </button>
        {/each}
      </aside>

      {#if selectedEntry}
        <article class="journal-viewer" aria-label="Selected reflection">
          <div class="journal-viewer-hero">
            <span>{formatEntryDate(selectedEntry.created_at, 'long')}</span>
            <h2>{titleFor(selectedEntry)}</h2>
            <p>{selectedEntry.character_summary}</p>
          </div>

          <div class="journal-meta-grid" aria-label="Reflection metadata">
            <div>
              <span>Confidence</span>
              <strong>{percent(selectedEntry.confidence)}</strong>
            </div>
            <div>
              <span>Emotional intensity</span>
              <strong>{percent(selectedEntry.emotional_intensity)}</strong>
            </div>
            <div>
              <span>Memory status</span>
              <strong>{promotionLabel(selectedEntry)}</strong>
            </div>
            <div>
              <span>Training review</span>
              <strong>{labelFor(selectedEntry.training_eligibility)}</strong>
            </div>
          </div>

          {#if selectedEntry.themes?.length}
            <section class="journal-section" aria-labelledby="journal-themes-heading">
              <h3 id="journal-themes-heading">Themes she noticed</h3>
              <div class="journal-tags">
                {#each selectedEntry.themes as theme}
                  <span>{labelFor(theme)}</span>
                {/each}
              </div>
            </section>
          {/if}

          {#if selectedEntry.insights?.length}
            <section class="journal-section" aria-labelledby="journal-insights-heading">
              <h3 id="journal-insights-heading">Key insights</h3>
              <div class="insight-list">
                {#each selectedEntry.insights as insight, index (insightKey(insight, index))}
                  <div class="insight-card">
                    <div>
                      <strong>{labelFor(insight.kind)}</strong>
                      <span>{percent(insight.confidence)} · {insight.evidence_count ?? 0} pieces of evidence</span>
                    </div>
                    <p>{insight.summary}</p>
                    {#if insight.themes?.length}
                      <div class="mini-tags">
                        {#each insight.themes as theme}
                          <span>{labelFor(theme)}</span>
                        {/each}
                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            </section>
          {/if}

          <section class="journal-section two-column" aria-label="Structured reflection details">
            {#if selectedEntry.structured_summary?.facts?.length}
              <div>
                <h3>Grounded moments</h3>
                <ul>
                  {#each selectedEntry.structured_summary.facts as fact}
                    <li>{fact}</li>
                  {/each}
                </ul>
              </div>
            {/if}

            {#if selectedEntry.structured_summary?.unresolved_questions?.length}
              <div>
                <h3>Still wondering</h3>
                <ul>
                  {#each selectedEntry.structured_summary.unresolved_questions as question}
                    <li>{question}</li>
                  {/each}
                </ul>
              </div>
            {/if}
          </section>

          <footer class="journal-footer-note">
            <span>Local only</span>
            <span>{selectedEntry.privacy_tags?.join(' · ') || 'private reflection'}</span>
            {#if selectedEntry.sensitivity_tags?.length}
              <span>{selectedEntry.sensitivity_tags.map(labelFor).join(' · ')}</span>
            {/if}
          </footer>
        </article>
      {/if}
    </div>
  {/if}
</section>
