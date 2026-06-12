<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { memoryStore } from '$lib/stores/memoryStore';
  import type { MemoryRecord } from '$lib/types/memory';

  const selectedMemory = $derived($memoryStore.items.find((item) => item.id === $memoryStore.selectedMemoryId) ?? null);
  const totalPages = $derived(Math.max(1, Math.ceil($memoryStore.total / $memoryStore.pageSize)));
  const showingFrom = $derived($memoryStore.total === 0 ? 0 : ($memoryStore.page - 1) * $memoryStore.pageSize + 1);
  const showingTo = $derived(Math.min($memoryStore.total, $memoryStore.page * $memoryStore.pageSize));

  let search = $state('');
  let character = $state('');
  let theme = $state('');
  let source = $state('');
  let dateFrom = $state('');
  let dateTo = $state('');
  let detailMemory = $state<MemoryRecord | null>(null);
  let draftText = $state('');
  let draftTags = $state('');
  let draftImportance = $state(0.5);
  let pruneDate = $state('');
  let selectedIds = $state<string[]>([]);
  let deleteWarning = $state<string | null>(null);
  let modalElement = $state<HTMLElement>();

  onMount(() => {
    memoryStore.loadMemories();
  });

  const applyFilters = () => {
    memoryStore.setQuery({
      q: search,
      character,
      theme,
      source,
      dateFrom: dateFrom || undefined,
      dateTo: dateTo || undefined
    });
  };

  const resetFilters = () => {
    search = '';
    character = '';
    theme = '';
    source = '';
    dateFrom = '';
    dateTo = '';
    selectedIds = [];
    applyFilters();
  };

  const openMemory = (memory: MemoryRecord) => {
    detailMemory = memory;
    draftText = memory.text;
    draftTags = tagsFor(memory).join(', ');
    draftImportance = scoreFor(memory, 'importance') ?? 0.5;
    memoryStore.selectMemory(memory.id);
  };

  const closeModal = () => {
    detailMemory = null;
    deleteWarning = null;
  };

  const handleModalKeydown = (event: KeyboardEvent) => {
    if (event.key === 'Escape') closeModal();
  };

  const saveMemory = async () => {
    if (!detailMemory) return;
    await memoryStore.updateMemory(detailMemory.id, {
      text: draftText,
      tags: draftTags.split(',').map((tag) => tag.trim()).filter(Boolean),
      importance: draftImportance,
      metadata: { browser_reviewed: true }
    });
    const updated = $memoryStore.items.find((item) => item.id === detailMemory?.id);
    if (updated) openMemory(updated);
  };

  const deleteMemory = async (memoryId: string) => {
    await memoryStore.deleteMemory(memoryId);
    selectedIds = selectedIds.filter((id) => id !== memoryId);
    closeModal();
  };

  const bulkDeleteSelected = async () => {
    if (selectedIds.length === 0) return;
    await memoryStore.bulkDelete({ ids: selectedIds });
    selectedIds = [];
  };

  const pruneOldMemories = async () => {
    if (!pruneDate) return;
    await memoryStore.bulkDelete({ older_than: new Date(`${pruneDate}T00:00:00Z`).toISOString() });
    pruneDate = '';
    selectedIds = [];
  };

  const toggleSelected = (memoryId: string) => {
    selectedIds = selectedIds.includes(memoryId) ? selectedIds.filter((id) => id !== memoryId) : [...selectedIds, memoryId];
  };

  const tagsFor = (memory: MemoryRecord) => {
    const tags = memory.metadata?.tags;
    if (Array.isArray(tags)) return tags.filter((tag): tag is string => typeof tag === 'string');
    return [];
  };

  const themesFor = (memory: MemoryRecord) => {
    const themes = memory.metadata?.themes;
    if (Array.isArray(themes)) return themes.filter((item): item is string => typeof item === 'string');
    const themeValue = memory.metadata?.theme;
    return typeof themeValue === 'string' && themeValue ? [themeValue] : [];
  };

  const characterFor = (memory: MemoryRecord) => String(memory.metadata?.character ?? memory.metadata?.character_id ?? 'Reverie');
  const sourceFor = (memory: MemoryRecord) => String(memory.metadata?.source ?? memory.source ?? 'local memory');
  const typeFor = (memory: MemoryRecord) => String(memory.metadata?.memory_type ?? 'long-term');

  const scoreFor = (memory: MemoryRecord, key: 'importance' | 'confidence' | 'score') => {
    const value = key === 'score' ? memory.score : memory.metadata?.[key];
    return typeof value === 'number' && Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : null;
  };

  const percent = (value: number | null) => (value === null ? '—' : `${Math.round(value * 100)}%`);

  const formatDate = (value: string | undefined, style: 'short' | 'long' = 'short') => {
    if (!value) return 'Unknown date';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Unknown date';
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: style === 'long' ? 'medium' : 'short',
      timeStyle: style === 'long' ? 'short' : undefined
    }).format(date);
  };


  $effect(() => {
    if (!detailMemory) return;

    // Move keyboard focus into the editor whenever it opens so screen reader
    // and keyboard users do not remain stranded behind the modal backdrop.
    void tick().then(() => modalElement?.focus());
  });

  const provenanceRows = (memory: MemoryRecord) => [
    ['Created', formatDate(memory.created_at, 'long')],
    ['Updated', formatDate(memory.updated_at, 'long')],
    ['Source', sourceFor(memory)],
    ['Character', characterFor(memory)],
    ['Type', typeFor(memory)],
    ['Journal', String(memory.metadata?.journal_entry_id ?? 'Not linked')],
    ['Rollback', String(memory.metadata?.rollback_id ?? 'Not linked')]
  ];
</script>

<svelte:window onkeydown={handleModalKeydown} />

<section class="memory-browser" aria-label="Memory Browser">
  <header class="memory-hero">
    <div>
      <p class="eyebrow">Memory Browser</p>
      <h1>Long-term recall, fully in your hands.</h1>
      <p class="subtitle">Search, review, edit, tag, and prune the memories that shape Reverie's continuity and growth.</p>
    </div>
    <button class="soft-button" type="button" onclick={() => memoryStore.refresh()} disabled={$memoryStore.loadState === 'loading'}>Refresh</button>
  </header>

  <div class="memory-filters" aria-label="Memory filters">
    <label>
      <span>Search memories</span>
      <input bind:value={search} placeholder="Keyword, theme, date, journal id…" onkeydown={(event) => event.key === 'Enter' && applyFilters()} />
    </label>
    <label>
      <span>Character</span>
      <input bind:value={character} placeholder="Reverie" />
    </label>
    <label>
      <span>Theme</span>
      <input bind:value={theme} placeholder="trust, intimacy, routine" />
    </label>
    <label>
      <span>Source</span>
      <input bind:value={source} placeholder="reflection_journal" />
    </label>
    <label>
      <span>From</span>
      <input type="date" bind:value={dateFrom} />
    </label>
    <label>
      <span>To</span>
      <input type="date" bind:value={dateTo} />
    </label>
    <div class="filter-actions">
      <button class="primary-button" type="button" onclick={applyFilters}>Search</button>
      <button class="ghost-button" type="button" onclick={resetFilters}>Clear</button>
    </div>
  </div>

  {#if $memoryStore.error}
    <div class="memory-error" role="alert">
      <strong>Memory needs attention.</strong>
      <span>{$memoryStore.error}</span>
      <button type="button" onclick={() => memoryStore.clearError()}>Dismiss</button>
    </div>
  {/if}

  <div class="memory-toolbar">
    <div>
      <strong>{showingFrom}-{showingTo}</strong>
      <span>of {$memoryStore.total} memories · page {$memoryStore.page} / {totalPages}</span>
    </div>
    <div class="bulk-controls">
      <button class="danger-button" type="button" disabled={selectedIds.length === 0 || $memoryStore.actionState !== 'idle'} onclick={bulkDeleteSelected}>
        Delete selected ({selectedIds.length})
      </button>
      <label class="prune-control">
        <span>Prune before</span>
        <input type="date" bind:value={pruneDate} />
      </label>
      <button class="danger-button" type="button" disabled={!pruneDate || $memoryStore.actionState !== 'idle'} onclick={pruneOldMemories}>Prune old</button>
    </div>
  </div>

  <div class="memory-layout">
    <div class="memory-list" aria-label="Long-term memories">
      {#if $memoryStore.loadState === 'loading'}
        <div class="empty-card"><strong>Opening memory…</strong><span>Loading a small page at a time to keep the app responsive.</span></div>
      {:else if $memoryStore.items.length === 0}
        <div class="empty-card"><strong>No memories match.</strong><span>Try a broader keyword, another theme, or clear the filters.</span></div>
      {:else}
        {#each $memoryStore.items as memory (memory.id)}
          <article class:active={memory.id === $memoryStore.selectedMemoryId} class="memory-card">
            <div class="card-topline">
              <label class="check-label" aria-label={`Select ${memory.id}`}>
                <input type="checkbox" checked={selectedIds.includes(memory.id)} onchange={() => toggleSelected(memory.id)} />
              </label>
              <span>{formatDate(memory.created_at)}</span>
              <span>{characterFor(memory)}</span>
            </div>
            <button type="button" onclick={() => openMemory(memory)}>
              <strong>{memory.text}</strong>
              <span>{sourceFor(memory)} · {typeFor(memory)}</span>
            </button>
            <div class="chip-row">
              {#each themesFor(memory).slice(0, 3) as item}
                <span class="chip">{item}</span>
              {/each}
              {#each tagsFor(memory).slice(0, 3) as item}
                <span class="chip soft">#{item}</span>
              {/each}
            </div>
            <div class="score-row">
              <span>Importance {percent(scoreFor(memory, 'importance'))}</span>
              <span>Confidence {percent(scoreFor(memory, 'confidence'))}</span>
              <span>Relevance {percent(scoreFor(memory, 'score'))}</span>
            </div>
          </article>
        {/each}
      {/if}
    </div>

    <aside class="memory-preview" aria-label="Selected memory preview">
      {#if selectedMemory}
        <p class="eyebrow">Selected memory</p>
        <h2>{characterFor(selectedMemory)}</h2>
        <p>{selectedMemory.text}</p>
        <dl>
          <div><dt>Created</dt><dd>{formatDate(selectedMemory.created_at, 'long')}</dd></div>
          <div><dt>Source</dt><dd>{sourceFor(selectedMemory)}</dd></div>
          <div><dt>Importance</dt><dd>{percent(scoreFor(selectedMemory, 'importance'))}</dd></div>
        </dl>
        <button class="primary-button" type="button" onclick={() => openMemory(selectedMemory)}>View & edit</button>
      {:else}
        <p class="eyebrow">Quiet library</p>
        <h2>Select a memory</h2>
        <p>Full provenance and editing controls will open here without sending anything to a cloud service.</p>
      {/if}
    </aside>
  </div>

  <footer class="pagination-controls" aria-label="Memory pagination">
    <button type="button" disabled={$memoryStore.page <= 1} onclick={() => memoryStore.setPage($memoryStore.page - 1)}>Previous</button>
    <span>Page {$memoryStore.page} of {totalPages}</span>
    <button type="button" disabled={$memoryStore.page >= totalPages} onclick={() => memoryStore.setPage($memoryStore.page + 1)}>Next</button>
  </footer>
</section>

{#if detailMemory}
  <div class="modal-backdrop" role="presentation" onclick={closeModal}></div>
  <div bind:this={modalElement} class="memory-modal" role="dialog" aria-modal="true" tabindex="-1" aria-labelledby="memory-editor-title" aria-describedby="memory-editor-description">
    <header>
      <div>
        <p class="eyebrow">Learned from {sourceFor(detailMemory)}</p>
        <h2 id="memory-editor-title">Review and edit memory</h2>
        <p id="memory-editor-description" class="sr-only">Edit the memory text, tags, importance, and provenance review state. Press Escape to close.</p>
      </div>
      <button class="ghost-button" type="button" onclick={closeModal}>Close</button>
    </header>

    <div class="modal-grid">
      <label class="editor-field">
        <span>Memory content</span>
        <textarea bind:value={draftText} rows="9"></textarea>
      </label>

      <aside class="provenance-card">
        <h3>Provenance</h3>
        <dl>
          {#each provenanceRows(detailMemory) as [label, value]}
            <div><dt>{label}</dt><dd>{value}</dd></div>
          {/each}
        </dl>
        <h3>Signals</h3>
        <div class="signal-stack">
          <span>Importance {percent(draftImportance)}</span>
          <input type="range" min="0" max="1" step="0.01" bind:value={draftImportance} aria-label="Memory importance score" />
          <span>Confidence {percent(scoreFor(detailMemory, 'confidence'))}</span>
        </div>
      </aside>
    </div>

    <label class="editor-field">
      <span>Tags</span>
      <input bind:value={draftTags} placeholder="comma-separated tags" />
    </label>

    <details class="raw-metadata">
      <summary>Advanced metadata</summary>
      <pre>{JSON.stringify(detailMemory.metadata, null, 2)}</pre>
    </details>

    {#if deleteWarning === detailMemory.id}
      <div class="delete-warning" role="alert">
        <strong>Delete this memory permanently?</strong>
        <span>Deleted memories are removed from retrieval, prompts, and growth evidence. This cannot be undone yet.</span>
        <button class="danger-button" type="button" onclick={() => deleteMemory(detailMemory!.id)}>Yes, delete it</button>
      </div>
    {/if}

    <footer>
      <button class="danger-button" type="button" onclick={() => (deleteWarning = detailMemory?.id ?? null)}>Delete memory</button>
      <button class="primary-button" type="button" disabled={$memoryStore.actionState !== 'idle' || !draftText.trim()} onclick={saveMemory}>Save changes</button>
    </footer>
  </div>
{/if}

<style>
  .memory-browser {
    display: grid;
    grid-template-rows: auto auto auto auto minmax(0, 1fr) auto;
    gap: 1rem;
    height: 100%;
    overflow: hidden;
    color: var(--text);
  }

  .memory-hero,
  .memory-filters,
  .memory-toolbar,
  .memory-card,
  .memory-preview,
  .empty-card,
  .memory-modal,
  .memory-error {
    border: 1px solid var(--line);
    background: var(--panel);
    box-shadow: var(--shadow);
    backdrop-filter: blur(22px);
  }

  .memory-hero {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 1.35rem;
    border-radius: 1.6rem;
    background: linear-gradient(135deg, rgba(240, 154, 159, 0.13), rgba(255, 255, 255, 0.05));
  }

  .memory-filters {
    display: grid;
    grid-template-columns: minmax(14rem, 2fr) repeat(5, minmax(8rem, 1fr)) auto;
    gap: 0.75rem;
    align-items: end;
    padding: 1rem;
    border-radius: 1.35rem;
  }

  label span,
  .prune-control span {
    display: block;
    margin-bottom: 0.35rem;
    color: var(--muted);
    font-size: 0.78rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  input,
  textarea {
    width: 100%;
    color: var(--text);
    border: 1px solid var(--line);
    border-radius: 0.9rem;
    background: rgba(255, 255, 255, 0.055);
    padding: 0.75rem 0.85rem;
    outline: none;
  }

  textarea {
    resize: vertical;
    min-height: 12rem;
    line-height: 1.5;
  }

  input:focus,
  textarea:focus {
    border-color: rgba(255, 176, 166, 0.45);
    box-shadow: 0 0 0 3px rgba(240, 154, 159, 0.12);
  }

  .filter-actions,
  .bulk-controls,
  .pagination-controls,
  .memory-modal footer {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }

  button {
    cursor: pointer;
  }

  button:disabled {
    cursor: default;
    opacity: 0.48;
  }

  .primary-button,
  .soft-button,
  .ghost-button,
  .danger-button {
    border-radius: 999px;
    padding: 0.72rem 1rem;
    color: var(--text);
    font-weight: 800;
  }

  .primary-button {
    background: linear-gradient(135deg, var(--accent), #b76575);
  }

  .soft-button,
  .ghost-button {
    border: 1px solid var(--line);
    background: rgba(255, 255, 255, 0.065);
  }

  .danger-button {
    border: 1px solid rgba(255, 121, 121, 0.35);
    background: rgba(169, 59, 68, 0.28);
  }

  .memory-error {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    padding: 0.85rem 1rem;
    border-color: rgba(255, 121, 121, 0.35);
    border-radius: 1rem;
    color: #ffd9d9;
  }

  .memory-error button {
    margin-left: auto;
    color: #ffd9d9;
    background: transparent;
  }

  .memory-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.8rem 1rem;
    border-radius: 1.2rem;
  }

  .memory-toolbar span,
  .score-row,
  .card-topline,
  .memory-card button span,
  dd,
  .empty-card span {
    color: var(--muted);
  }

  .prune-control {
    min-width: 11rem;
  }

  .memory-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 22rem;
    gap: 1rem;
    min-height: 0;
  }

  .memory-list {
    display: grid;
    align-content: start;
    gap: 0.85rem;
    min-height: 0;
    overflow: auto;
    padding-right: 0.25rem;
  }

  .memory-card {
    padding: 1rem;
    border-radius: 1.35rem;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.075), rgba(255, 255, 255, 0.035));
  }

  .memory-card.active {
    border-color: rgba(255, 176, 166, 0.42);
    box-shadow: 0 18px 48px rgba(240, 154, 159, 0.12);
  }

  .memory-card button {
    width: 100%;
    margin: 0.6rem 0;
    padding: 0;
    color: inherit;
    text-align: left;
    background: transparent;
  }

  .memory-card strong {
    display: -webkit-box;
    overflow: hidden;
    line-clamp: 2;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    line-height: 1.35;
  }

  .card-topline,
  .score-row,
  .chip-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.82rem;
  }

  .check-label input {
    width: auto;
  }

  .chip {
    padding: 0.35rem 0.55rem;
    border: 1px solid rgba(240, 154, 159, 0.24);
    border-radius: 999px;
    background: rgba(240, 154, 159, 0.09);
    color: #ffd6d8;
    font-size: 0.78rem;
    font-weight: 800;
  }

  .chip.soft {
    border-color: var(--line);
    background: rgba(255, 255, 255, 0.055);
    color: var(--muted);
  }

  .memory-preview,
  .empty-card {
    padding: 1.2rem;
    border-radius: 1.4rem;
  }

  .memory-preview {
    overflow: auto;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.035));
  }

  .memory-preview p {
    line-height: 1.55;
  }

  dl {
    display: grid;
    gap: 0.65rem;
    margin: 1rem 0;
  }

  dl div {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding-bottom: 0.55rem;
    border-bottom: 1px solid var(--line);
  }

  dt {
    color: var(--dim);
    font-size: 0.78rem;
    font-weight: 800;
    text-transform: uppercase;
  }

  dd {
    margin: 0;
    text-align: right;
  }

  .pagination-controls {
    justify-content: center;
  }

  .pagination-controls button {
    padding: 0.6rem 0.9rem;
    color: var(--text);
    border: 1px solid var(--line);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.06);
  }

  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 20;
    background: rgba(8, 6, 10, 0.66);
    backdrop-filter: blur(10px);
  }

  .memory-modal {
    position: fixed;
    inset: 4vh 5vw;
    z-index: 21;
    display: grid;
    grid-template-rows: auto minmax(0, 1fr) auto auto auto;
    gap: 1rem;
    overflow: auto;
    padding: 1.2rem;
    border-radius: 1.6rem;
  }

  .memory-modal header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
  }

  .modal-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 22rem;
    gap: 1rem;
    min-height: 0;
  }

  .provenance-card,
  .delete-warning,
  .raw-metadata {
    border: 1px solid var(--line);
    border-radius: 1.2rem;
    background: rgba(255, 255, 255, 0.045);
    padding: 1rem;
  }

  .signal-stack {
    display: grid;
    gap: 0.5rem;
    color: var(--muted);
  }

  .raw-metadata pre {
    overflow: auto;
    max-height: 14rem;
    color: var(--muted);
    white-space: pre-wrap;
  }

  .delete-warning {
    display: grid;
    gap: 0.5rem;
    border-color: rgba(255, 121, 121, 0.38);
    color: #ffd9d9;
  }

  .memory-modal footer {
    justify-content: flex-end;
  }

  @media (max-width: 1180px) {
    .memory-filters,
    .memory-layout,
    .modal-grid {
      grid-template-columns: 1fr;
    }

    .bulk-controls,
    .memory-toolbar,
    .memory-hero {
      align-items: stretch;
      flex-direction: column;
    }
  }
</style>
