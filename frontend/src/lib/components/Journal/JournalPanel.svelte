<script lang="ts">
  import { onMount } from 'svelte';
  import { chatStore } from '$lib/stores/chatStore';
  import { journalStore } from '$lib/stores/journalStore';
  import type { ChatMessage } from '$lib/types/chat';
  import type { JournalEntry, ReflectionInsight } from '$lib/types/journal';

  type JournalFilter = 'all' | 'favorites' | 'promoted' | 'needs_review';

  const PINNED_STORAGE_KEY = 'reverie.journal.pinnedEntryIds.v1';

  let searchTerm = $state('');
  let activeTheme = $state('all');
  let activeCharacter = $state('all');
  let activeFilter = $state<JournalFilter>('all');
  let openEntryId = $state<string | null>(null);
  let pinnedEntryIds = $state<string[]>([]);

  const selectedEntry = $derived(
    $journalStore.entries.find((entry) => entry.entry_id === $journalStore.selectedEntryId) ?? null
  );
  const modalEntry = $derived($journalStore.entries.find((entry) => entry.entry_id === openEntryId) ?? null);
  const isLoading = $derived($journalStore.loadState === 'loading');
  const isRefreshing = $derived($journalStore.loadState === 'refreshing');
  const isReflecting = $derived($journalStore.actionState === 'reflecting');
  const hasEntries = $derived($journalStore.entries.length > 0);

  const sortedEntries = $derived.by(() =>
    [...$journalStore.entries].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  );

  const themes = $derived.by(() => {
    const unique = new Set<string>();
    for (const entry of $journalStore.entries) {
      for (const theme of entry.themes ?? []) unique.add(theme);
      for (const insight of entry.insights ?? []) {
        for (const theme of insight.themes ?? []) unique.add(theme);
      }
    }
    return [...unique].sort((a, b) => labelFor(a).localeCompare(labelFor(b)));
  });

  const characters = $derived.by(() => {
    const unique = new Set<string>();
    for (const entry of $journalStore.entries) unique.add(characterFor(entry));
    return [...unique].sort();
  });

  const filteredEntries = $derived.by(() => {
    const query = searchTerm.trim().toLowerCase();
    return sortedEntries.filter((entry) => {
      if (activeFilter === 'favorites' && !isPinned(entry.entry_id)) return false;
      if (activeFilter === 'promoted' && !isPromoted(entry)) return false;
      if (activeFilter === 'needs_review' && entry.training_eligibility !== 'needs_review') return false;
      if (activeTheme !== 'all' && !entryThemes(entry).includes(activeTheme)) return false;
      if (activeCharacter !== 'all' && characterFor(entry) !== activeCharacter) return false;
      if (!query) return true;
      return searchableText(entry).includes(query);
    });
  });

  const pinnedCount = $derived(pinnedEntryIds.length);
  const growthLinkedCount = $derived(
    $journalStore.entries.filter((entry) => Boolean(entry.metadata?.memory_promotion?.should_promote || entry.linked_memory_ids?.length)).length
  );
  const reviewCount = $derived($journalStore.entries.filter((entry) => entry.training_eligibility === 'needs_review').length);

  onMount(() => {
    pinnedEntryIds = readPinnedEntryIds();
    void journalStore.loadEntries();
  });

  const refreshJournal = () => {
    void journalStore.refresh();
  };

  const triggerReflection = () => {
    const history = reflectionHistory($chatStore.messages);
    void journalStore.triggerReflection(history);
  };

  const selectEntry = (entryId: string) => {
    journalStore.selectEntry(entryId);
  };

  const openEntry = (entryId: string) => {
    openEntryId = entryId;
    selectEntry(entryId);
  };

  const closeEntry = () => {
    openEntryId = null;
  };

  const togglePinned = (entryId: string, event?: MouseEvent) => {
    event?.stopPropagation();
    pinnedEntryIds = isPinned(entryId)
      ? pinnedEntryIds.filter((id) => id !== entryId)
      : [entryId, ...pinnedEntryIds];
    writePinnedEntryIds(pinnedEntryIds);
  };

  const setFilter = (filter: JournalFilter) => {
    activeFilter = filter;
  };

  const resetFilters = () => {
    searchTerm = '';
    activeTheme = 'all';
    activeCharacter = 'all';
    activeFilter = 'all';
  };

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

  const percent = (value: number | undefined) => {
    const bounded = Math.min(Math.max(value ?? 0, 0), 1);
    return `${Math.round(bounded * 100)}%`;
  };

  const titleFor = (entry: JournalEntry) => {
    const themesForEntry = entryThemes(entry).slice(0, 2).map(labelFor).join(' + ');
    return themesForEntry ? `A note on ${themesForEntry}` : 'Private reflection';
  };

  const labelFor = (value: string | undefined) =>
    (value ?? 'unknown')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());

  const promotionLabel = (entry: JournalEntry) => {
    const decision = entry.metadata?.memory_promotion;
    if (decision?.should_promote) return 'Promoted to memory';
    if (entry.linked_memory_ids?.length) return 'Linked to memory';
    return 'Journal only';
  };

  const summaryFor = (entry: JournalEntry) =>
    entry.character_summary || entry.insights?.[0]?.summary || 'I left myself a quiet note to read again later.';

  const clearJournalError = () => {
    journalStore.clearError();
  };

  const insightKey = (insight: ReflectionInsight, index: number) => `${insight.kind ?? 'insight'}-${index}`;

  const readPinnedEntryIds = () => {
    if (typeof localStorage === 'undefined') return [];
    const raw = localStorage.getItem(PINNED_STORAGE_KEY);
    if (!raw) return [];
    try {
      const decoded = JSON.parse(raw);
      return Array.isArray(decoded) ? decoded.filter((value): value is string => typeof value === 'string') : [];
    } catch {
      return [];
    }
  };

  const writePinnedEntryIds = (entryIds: string[]) => {
    if (typeof localStorage === 'undefined') return;
    localStorage.setItem(PINNED_STORAGE_KEY, JSON.stringify(entryIds));
  };

  const isPinned = (entryId: string) => pinnedEntryIds.includes(entryId);

  const isPromoted = (entry: JournalEntry) => Boolean(entry.metadata?.memory_promotion?.should_promote || entry.linked_memory_ids?.length);

  const entryThemes = (entry: JournalEntry) => [
    ...new Set([...(entry.themes ?? []), ...(entry.insights ?? []).flatMap((insight) => insight.themes ?? [])])
  ];

  const characterFor = (entry: JournalEntry) =>
    String(entry.metadata?.character_name ?? entry.metadata?.character_id ?? entry.metadata?.user_id ?? 'Reverie');

  const searchableText = (entry: JournalEntry) =>
    [
      titleFor(entry),
      characterFor(entry),
      summaryFor(entry),
      ...(entry.themes ?? []),
      ...(entry.privacy_tags ?? []),
      ...(entry.sensitivity_tags ?? []),
      ...(entry.insights ?? []).map((insight) => `${insight.kind ?? ''} ${insight.summary ?? ''} ${(insight.themes ?? []).join(' ')}`),
      ...(entry.structured_summary?.facts ?? []),
      ...(entry.structured_summary?.interpretations ?? []),
      ...(entry.structured_summary?.growth_hypotheses ?? []),
      ...(entry.structured_summary?.unresolved_questions ?? [])
    ]
      .join(' ')
      .toLowerCase();

  const reflectionHistory = (messages: ChatMessage[]) =>
    messages
      .filter((message) => (message.role === 'user' || message.role === 'assistant') && message.status !== 'error')
      .filter((message) => message.content.trim().length > 0)
      .slice(-12)
      .map((message) => ({ role: message.role, content: message.content }));
</script>

<section class="journal-panel" aria-label="Self-reflection journal">
  <header class="journal-header diary-hero">
    <div>
      <p class="eyebrow">Self-reflection journal</p>
      <h1>Pages she writes after the room goes quiet</h1>
      <p class="subtitle">
        A warm, local diary of Reverie’s reflections — personal prose first, evidence and growth links close enough to review.
      </p>
    </div>

    <div class="journal-actions">
      <button class="primary-diary-button" type="button" onclick={triggerReflection} disabled={isLoading || isReflecting}>
        {isReflecting ? 'Writing…' : 'New reflection'}
      </button>
      <button class="ghost-button" type="button" onclick={refreshJournal} disabled={isLoading || isRefreshing || isReflecting}>
        {isRefreshing ? 'Refreshing…' : 'Refresh'}
      </button>
    </div>
  </header>

  {#if $journalStore.error}
    <div class="journal-notice" role="status">
      <div>
        <strong>The journal stayed closed for a moment.</strong>
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
    <div class="journal-empty">
      <div class="journal-empty-mark">♡</div>
      <h2>No reflections yet</h2>
      <p>After meaningful conversations, Reverie will write gentle first-person reflections here. You can also ask for one now.</p>
      <button class="primary-diary-button" type="button" onclick={triggerReflection} disabled={isReflecting}>
        {isReflecting ? 'Writing…' : 'Write first reflection'}
      </button>
    </div>
  {:else}
    <div class="journal-toolbar" aria-label="Journal filters">
      <label class="journal-search">
        <span>Search diary</span>
        <input bind:value={searchTerm} type="search" placeholder="Theme, character, keyword…" />
      </label>

      <label>
        <span>Theme</span>
        <select bind:value={activeTheme}>
          <option value="all">All themes</option>
          {#each themes as theme}
            <option value={theme}>{labelFor(theme)}</option>
          {/each}
        </select>
      </label>

      <label>
        <span>Character</span>
        <select bind:value={activeCharacter}>
          <option value="all">All characters</option>
          {#each characters as character}
            <option value={character}>{labelFor(character)}</option>
          {/each}
        </select>
      </label>
    </div>

    <div class="journal-filter-chips" aria-label="Quick journal filters">
      <button class:active={activeFilter === 'all'} type="button" onclick={() => setFilter('all')}>All pages</button>
      <button class:active={activeFilter === 'favorites'} type="button" onclick={() => setFilter('favorites')}>Pinned · {pinnedCount}</button>
      <button class:active={activeFilter === 'promoted'} type="button" onclick={() => setFilter('promoted')}>Growth-linked · {growthLinkedCount}</button>
      <button class:active={activeFilter === 'needs_review'} type="button" onclick={() => setFilter('needs_review')}>Needs review · {reviewCount}</button>
      <button class="reset" type="button" onclick={resetFilters}>Clear</button>
    </div>

    <div class="journal-content diary-content">
      <aside class="journal-list timeline-list" aria-label="Journal entries">
        {#if filteredEntries.length === 0}
          <div class="journal-list-empty">
            <strong>No pages match that search.</strong>
            <span>Try a gentler keyword, another character, or clear the filters.</span>
          </div>
        {:else}
          {#each filteredEntries as entry (entry.entry_id)}
            <button
              class:active={entry.entry_id === $journalStore.selectedEntryId}
              class:pinned={isPinned(entry.entry_id)}
              class="journal-entry-card diary-page-tab"
              type="button"
              onclick={() => selectEntry(entry.entry_id)}
              ondblclick={() => openEntry(entry.entry_id)}
            >
              <span class="timeline-dot" aria-hidden="true"></span>
              <span class="journal-entry-date">{formatEntryDate(entry.created_at)}</span>
              <strong>{titleFor(entry)}</strong>
              <span>{summaryFor(entry)}</span>
              <small>{characterFor(entry)} · {entry.insights?.length ?? 0} insights · {percent(entry.confidence)}</small>
              <span class="card-actions">
                <span>{promotionLabel(entry)}</span>
                <span class="pin-indicator">{isPinned(entry.entry_id) ? 'Pinned' : 'Open'}</span>
              </span>
            </button>
          {/each}
        {/if}
      </aside>

      {#if selectedEntry}
        <article class="journal-viewer diary-page" aria-label="Selected reflection">
          <div class="journal-viewer-hero parchment-hero">
            <div class="viewer-topline">
              <span>{formatEntryDate(selectedEntry.created_at, 'long')}</span>
              <button type="button" class:pinned={isPinned(selectedEntry.entry_id)} onclick={(event) => togglePinned(selectedEntry.entry_id, event)}>
                {isPinned(selectedEntry.entry_id) ? 'Pinned ♥' : 'Pin page'}
              </button>
            </div>
            <h2>{titleFor(selectedEntry)}</h2>
            <p>{summaryFor(selectedEntry)}</p>
            <button class="read-more-button" type="button" onclick={() => openEntry(selectedEntry.entry_id)}>Read in quiet mode</button>
          </div>

          <div class="journal-meta-grid" aria-label="Reflection metadata">
            <div>
              <span>Confidence</span>
              <strong>{percent(selectedEntry.confidence)}</strong>
            </div>
            <div>
              <span>Feeling strength</span>
              <strong>{percent(selectedEntry.emotional_intensity)}</strong>
            </div>
            <div>
              <span>Growth link</span>
              <strong>{promotionLabel(selectedEntry)}</strong>
            </div>
            <div>
              <span>Training review</span>
              <strong>{labelFor(selectedEntry.training_eligibility)}</strong>
            </div>
          </div>

          {#if selectedEntry.themes?.length}
            <section class="journal-section" aria-labelledby="journal-themes-heading">
              <h3 id="journal-themes-heading">Themes tucked into the margin</h3>
              <div class="journal-tags">
                {#each selectedEntry.themes as theme}
                  <span>{labelFor(theme)}</span>
                {/each}
              </div>
            </section>
          {/if}

          {#if selectedEntry.insights?.length}
            <section class="journal-section" aria-labelledby="journal-insights-heading">
              <h3 id="journal-insights-heading">What she thinks she learned</h3>
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

            {#if selectedEntry.structured_summary?.growth_hypotheses?.length}
              <div>
                <h3>Growth visibility</h3>
                <ul>
                  {#each selectedEntry.structured_summary.growth_hypotheses as hypothesis}
                    <li>{hypothesis}</li>
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

{#if modalEntry}
  <div class="journal-modal-backdrop" role="presentation">
    <div class="journal-modal" role="dialog" aria-modal="true" aria-labelledby="journal-modal-title">
      <header>
        <div>
          <span>{formatEntryDate(modalEntry.created_at, 'long')}</span>
          <h2 id="journal-modal-title">{titleFor(modalEntry)}</h2>
        </div>
        <button type="button" aria-label="Close reflection" onclick={closeEntry}>×</button>
      </header>
      <div class="journal-modal-prose">
        <p>{summaryFor(modalEntry)}</p>
        {#if modalEntry.structured_summary?.interpretations?.length}
          {#each modalEntry.structured_summary.interpretations as interpretation}
            <p>{interpretation}</p>
          {/each}
        {/if}
      </div>
      <footer>
        <button class:pinned={isPinned(modalEntry.entry_id)} type="button" onclick={(event) => togglePinned(modalEntry.entry_id, event)}>
          {isPinned(modalEntry.entry_id) ? 'Unpin this page' : 'Pin this page'}
        </button>
        <span>{promotionLabel(modalEntry)} · {percent(modalEntry.confidence)} confidence</span>
      </footer>
    </div>
  </div>
{/if}
