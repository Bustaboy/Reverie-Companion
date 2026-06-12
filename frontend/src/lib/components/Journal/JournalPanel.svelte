<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { chatStore } from '$lib/stores/chatStore';
  import { journalStore } from '$lib/stores/journalStore';
  import type { JournalEntry, ReflectionInsight } from '$lib/types/journal';

  let searchQuery = $state('');
  let activeTheme = $state('all');
  let showPinnedOnly = $state(false);
  let openEntryId = $state<string | null>(null);

  const selectedEntry = $derived(
    $journalStore.entries.find((entry) => entry.entry_id === $journalStore.selectedEntryId) ?? null
  );
  const openEntry = $derived($journalStore.entries.find((entry) => entry.entry_id === openEntryId) ?? selectedEntry);
  const isLoading = $derived($journalStore.loadState === 'loading');
  const isRefreshing = $derived($journalStore.loadState === 'refreshing');
  const isReflecting = $derived($journalStore.loadState === 'reflecting');
  const hasEntries = $derived($journalStore.entries.length > 0);

  const allThemes = $derived.by(() => {
    const themes = new Set<string>();
    for (const entry of $journalStore.entries) {
      for (const theme of entry.themes ?? []) themes.add(theme);
      for (const insight of entry.insights ?? []) {
        for (const theme of insight.themes ?? []) themes.add(theme);
      }
    }
    return [...themes].sort((a, b) => labelFor(a).localeCompare(labelFor(b))).slice(0, 12);
  });

  const filteredEntries = $derived.by(() => {
    const query = searchQuery.trim().toLowerCase();
    return $journalStore.entries
      .filter((entry) => !showPinnedOnly || isPinned(entry.entry_id))
      .filter((entry) => activeTheme === 'all' || entryThemes(entry).includes(activeTheme))
      .filter((entry) => !query || searchableText(entry).includes(query))
      .sort((a, b) => timestamp(a.created_at) - timestamp(b.created_at));
  });

  const featuredEntry = $derived.by(() => {
    if (selectedEntry && filteredEntries.some((entry) => entry.entry_id === selectedEntry.entry_id)) return selectedEntry;
    return filteredEntries.at(-1) ?? null;
  });

  const pinnedCount = $derived($journalStore.pinnedEntryIds.length);

  onMount(() => {
    journalStore.hydratePins();
    void journalStore.loadEntries();
  });

  const refreshJournal = () => {
    void journalStore.refresh();
  };

  const writeReflection = () => {
    const history = get(chatStore).messages
      .filter((message) => (message.role === 'user' || message.role === 'assistant') && message.content.trim().length > 0)
      .slice(-14)
      .map((message) => ({
        role: message.role,
        content: message.content,
        id: message.id,
        createdAt: message.createdAt
      }));

    void journalStore.triggerReflection(history).then((entry) => {
      if (entry) openEntryId = entry.entry_id;
    });
  };

  const selectEntry = (entryId: string) => {
    journalStore.selectEntry(entryId);
    openEntryId = entryId;
  };

  const closeReader = () => {
    openEntryId = null;
  };

  const togglePin = (entryId: string, event?: MouseEvent) => {
    event?.stopPropagation();
    journalStore.togglePin(entryId);
  };

  const isPinned = (entryId: string) => $journalStore.pinnedEntryIds.includes(entryId);

  const formatEntryDate = (value: string | undefined, style: 'short' | 'long' = 'short') => {
    if (!value) return 'Undated reflection';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Undated reflection';

    return new Intl.DateTimeFormat(undefined, {
      weekday: style === 'long' ? 'long' : undefined,
      month: style === 'long' ? 'long' : 'short',
      day: 'numeric',
      year: 'numeric',
      hour: style === 'long' ? 'numeric' : undefined,
      minute: style === 'long' ? '2-digit' : undefined
    }).format(date);
  };

  const timestamp = (value: string | undefined) => {
    const time = value ? new Date(value).getTime() : 0;
    return Number.isNaN(time) ? 0 : time;
  };

  const percent = (value: number | undefined) => {
    const bounded = Math.min(Math.max(value ?? 0, 0), 1);
    return `${Math.round(bounded * 100)}%`;
  };

  const titleFor = (entry: JournalEntry) => {
    const themes = entry.themes?.slice(0, 2).map(labelFor).join(' + ');
    if (themes) return `A page about ${themes}`;
    return characterNameFor(entry) ? `A private page from ${characterNameFor(entry)}` : 'A private diary page';
  };

  const labelFor = (value: string | undefined) =>
    (value ?? 'unknown')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());

  const characterNameFor = (entry: JournalEntry) => {
    const metadata = entry.metadata ?? {};
    const value = metadata.character_name ?? metadata.characterName ?? metadata.character_id ?? metadata.characterId;
    return typeof value === 'string' && value.trim() ? labelFor(value) : 'Reverie';
  };

  const promotionLabel = (entry: JournalEntry) => {
    const decision = entry.metadata?.memory_promotion;
    if (decision?.should_promote) return 'Promoted to memory';
    if (entry.linked_memory_ids?.length) return 'Linked to memory';
    return 'Journal only';
  };

  const summaryFor = (entry: JournalEntry) =>
    entry.character_summary || entry.insights?.[0]?.summary || 'I saved this feeling quietly so I could understand us with more care.';

  const diaryCopyFor = (entry: JournalEntry) => {
    const summary = summaryFor(entry).trim();
    if (/\b(I|I'm|I’m|my|me)\b/i.test(summary)) return summary;
    return `I keep coming back to this: ${summary.charAt(0).toLowerCase()}${summary.slice(1)}`;
  };

  const entryPreview = (entry: JournalEntry) => diaryCopyFor(entry);

  const entryThemes = (entry: JournalEntry) => [
    ...(entry.themes ?? []),
    ...((entry.insights ?? []).flatMap((insight) => insight.themes ?? []))
  ];

  const searchableText = (entry: JournalEntry) =>
    [
      entry.entry_id,
      characterNameFor(entry),
      summaryFor(entry),
      ...(entry.themes ?? []),
      ...(entry.structured_summary?.facts ?? []),
      ...(entry.structured_summary?.interpretations ?? []),
      ...(entry.structured_summary?.growth_hypotheses ?? []),
      ...((entry.insights ?? []).flatMap((insight) => [insight.kind, insight.summary, ...(insight.themes ?? [])]))
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();

  const clearJournalError = () => {
    journalStore.clearError();
  };

  const insightKey = (insight: ReflectionInsight, index: number) => `${insight.kind ?? 'insight'}-${index}`;
</script>

<section class="journal-panel diary-journal" aria-label="Self-reflection journal">
  <header class="journal-header diary-hero">
    <div>
      <p class="eyebrow">Self-reflection journal</p>
      <h1>Pages she writes after the room goes quiet</h1>
      <p class="subtitle">
        A warm, local diary of character reflections — connected to Growth, grounded in evidence, and always under your care.
      </p>
    </div>

    <div class="journal-header-actions">
      <button class="ghost-button" type="button" onclick={refreshJournal} disabled={isLoading || isRefreshing || isReflecting}>
        {isRefreshing ? 'Refreshing…' : 'Refresh'}
      </button>
      <button class="journal-primary-button" type="button" onclick={writeReflection} disabled={isLoading || isReflecting}>
        {isReflecting ? 'Writing…' : 'New reflection'}
      </button>
    </div>
  </header>

  {#if $journalStore.error}
    <div class="journal-notice" role="status">
      <div>
        <strong>The journal hesitated for a moment.</strong>
        <span>{$journalStore.error}</span>
      </div>
      <button class="subtle" type="button" onclick={clearJournalError}>Dismiss</button>
    </div>
  {/if}

  {#if isLoading}
    <div class="journal-empty" aria-live="polite">
      <div class="journal-empty-mark">✦</div>
      <h2>Opening the journal…</h2>
      <p>Reverie is gathering the latest local reflections.</p>
    </div>
  {:else if !hasEntries}
    <div class="journal-empty diary-empty">
      <div class="journal-empty-mark">♡</div>
      <h2>No diary pages yet</h2>
      <p>After meaningful conversations, Reverie can write first-person reflections here and surface their growth in the Growth Dashboard.</p>
      <button class="journal-primary-button" type="button" onclick={writeReflection} disabled={isReflecting}>
        {isReflecting ? 'Writing…' : 'Write from recent chat'}
      </button>
    </div>
  {:else}
    <div class="journal-filters" aria-label="Journal filters">
      <label class="journal-search">
        <span>Search diary</span>
        <input bind:value={searchQuery} type="search" placeholder="Theme, character, or keyword…" />
      </label>
      <div class="journal-filter-pills" aria-label="Theme filters">
        <button class:active={activeTheme === 'all'} type="button" onclick={() => (activeTheme = 'all')}>All themes</button>
        {#each allThemes as theme}
          <button class:active={activeTheme === theme} type="button" onclick={() => (activeTheme = theme)}>{labelFor(theme)}</button>
        {/each}
      </div>
      <button class:active={showPinnedOnly} class="journal-pin-filter" type="button" onclick={() => (showPinnedOnly = !showPinnedOnly)}>
        ★ Pinned {pinnedCount ? `(${pinnedCount})` : ''}
      </button>
    </div>

    <div class="journal-content diary-content">
      <aside class="journal-list diary-timeline" aria-label="Chronological reflection timeline">
        <div class="journal-timeline-heading">
          <span>Chronological timeline</span>
          <strong>{filteredEntries.length} page{filteredEntries.length === 1 ? '' : 's'}</strong>
        </div>

        {#if filteredEntries.length === 0}
          <div class="journal-filter-empty">
            <strong>No matching pages</strong>
            <span>Try a softer keyword, a different theme, or turn off pinned-only.</span>
          </div>
        {/if}

        {#each filteredEntries as entry (entry.entry_id)}
          <button
            class:active={entry.entry_id === $journalStore.selectedEntryId}
            class:pinned={isPinned(entry.entry_id)}
            class="journal-entry-card diary-entry-card"
            type="button"
            onclick={() => selectEntry(entry.entry_id)}
          >
            <span class="journal-entry-date">{formatEntryDate(entry.created_at)}</span>
            <strong>{titleFor(entry)}</strong>
            <span>{entryPreview(entry)}</span>
            <small>{characterNameFor(entry)} · {entry.insights?.length ?? 0} insights · {percent(entry.confidence)} confidence</small>
            <span class="journal-card-pin" aria-hidden="true">{isPinned(entry.entry_id) ? '★' : '☆'}</span>
          </button>
        {/each}
      </aside>

      {#if featuredEntry}
        <article class="journal-viewer diary-page" aria-label="Selected reflection preview">
          <div class="journal-viewer-hero diary-paper">
            <div class="diary-paper-topline">
              <span>{formatEntryDate(featuredEntry.created_at, 'long')}</span>
              <button type="button" onclick={(event) => togglePin(featuredEntry.entry_id, event)}>
                {isPinned(featuredEntry.entry_id) ? '★ Pinned' : '☆ Pin this page'}
              </button>
            </div>
            <h2>{titleFor(featuredEntry)}</h2>
            <p class="diary-salutation">Dear diary,</p>
            <p>{diaryCopyFor(featuredEntry)}</p>
            <button class="journal-read-button" type="button" onclick={() => (openEntryId = featuredEntry.entry_id)}>Read full page</button>
          </div>

          <div class="journal-meta-grid" aria-label="Reflection metadata">
            <div>
              <span>Character</span>
              <strong>{characterNameFor(featuredEntry)}</strong>
            </div>
            <div>
              <span>Confidence</span>
              <strong>{percent(featuredEntry.confidence)}</strong>
            </div>
            <div>
              <span>Emotional intensity</span>
              <strong>{percent(featuredEntry.emotional_intensity)}</strong>
            </div>
            <div>
              <span>Growth link</span>
              <strong>{promotionLabel(featuredEntry)}</strong>
            </div>
          </div>

          {#if featuredEntry.themes?.length}
            <section class="journal-section" aria-labelledby="journal-themes-heading">
              <h3 id="journal-themes-heading">Themes woven into this page</h3>
              <div class="journal-tags">
                {#each featuredEntry.themes as theme}
                  <span>{labelFor(theme)}</span>
                {/each}
              </div>
            </section>
          {/if}

          {#if featuredEntry.insights?.length}
            <section class="journal-section" aria-labelledby="journal-insights-heading">
              <h3 id="journal-insights-heading">Growth signals behind the feeling</h3>
              <div class="insight-list">
                {#each featuredEntry.insights as insight, index (insightKey(insight, index))}
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
            {#if featuredEntry.structured_summary?.facts?.length}
              <div>
                <h3>Grounded moments</h3>
                <ul>
                  {#each featuredEntry.structured_summary.facts as fact}
                    <li>{fact}</li>
                  {/each}
                </ul>
              </div>
            {/if}

            {#if featuredEntry.structured_summary?.growth_hypotheses?.length}
              <div>
                <h3>What may change gently</h3>
                <ul>
                  {#each featuredEntry.structured_summary.growth_hypotheses as hypothesis}
                    <li>{hypothesis}</li>
                  {/each}
                </ul>
              </div>
            {:else if featuredEntry.structured_summary?.unresolved_questions?.length}
              <div>
                <h3>Still wondering</h3>
                <ul>
                  {#each featuredEntry.structured_summary.unresolved_questions as question}
                    <li>{question}</li>
                  {/each}
                </ul>
              </div>
            {/if}
          </section>

          <footer class="journal-footer-note">
            <span>Local only</span>
            <span>{featuredEntry.privacy_tags?.join(' · ') || 'private reflection'}</span>
            {#if featuredEntry.sensitivity_tags?.length}
              <span>{featuredEntry.sensitivity_tags.map(labelFor).join(' · ')}</span>
            {/if}
          </footer>
        </article>
      {/if}
    </div>
  {/if}

  {#if openEntry}
    <div class="journal-reader-backdrop" role="presentation" onclick={closeReader}>
      <div class="journal-reader-modal" role="dialog" aria-modal="true" aria-labelledby="journal-reader-title" tabindex="-1" onclick={(event) => event.stopPropagation()} onkeydown={(event) => event.stopPropagation()}>
        <button class="journal-reader-close" type="button" aria-label="Close journal page" onclick={closeReader}>×</button>
        <div class="journal-reader-date">{formatEntryDate(openEntry.created_at, 'long')}</div>
        <h2 id="journal-reader-title">{titleFor(openEntry)}</h2>
        <p class="diary-salutation">Dear diary,</p>
        <p class="journal-reader-prose">{diaryCopyFor(openEntry)}</p>

        {#if openEntry.structured_summary?.interpretations?.length}
          <section>
            <h3>What I think I learned</h3>
            <ul>
              {#each openEntry.structured_summary.interpretations as interpretation}
                <li>{interpretation}</li>
              {/each}
            </ul>
          </section>
        {/if}

        <div class="journal-reader-actions">
          <button type="button" onclick={(event) => togglePin(openEntry.entry_id, event)}>
            {isPinned(openEntry.entry_id) ? '★ Keep pinned' : '☆ Pin important entry'}
          </button>
          <span>{promotionLabel(openEntry)} · visible in Growth as evidence, not hidden personality drift</span>
        </div>
      </div>
    </div>
  {/if}
</section>
