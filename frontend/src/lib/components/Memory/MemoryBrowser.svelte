<script lang="ts">
  import { onMount } from 'svelte';
  import { memoryStore } from '$lib/stores/memoryStore';
  import type { MemoryRecord } from '$lib/types/memory';

  let query = $state('');
  let character = $state('');
  let theme = $state('');
  let memoryType = $state('');
  let startDate = $state('');
  let endDate = $state('');
  let selectedMemory = $state<MemoryRecord | null>(null);
  let editedText = $state('');
  let selectedIds = $state<string[]>([]);
  let pruneDate = $state('');
  let showPruneWarning = $state(false);

  const isBusy = $derived($memoryStore.loadState === 'loading' || $memoryStore.loadState === 'refreshing' || $memoryStore.actionState !== 'idle');
  const selectedCount = $derived(selectedIds.length);

  onMount(() => {
    void memoryStore.load();
  });

  const formatDate = (value: string | undefined, fallback = 'Unknown') => {
    if (!value) return fallback;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return fallback;
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }).format(date);
  };

  const percent = (value: unknown, fallback = '—') => {
    if (typeof value !== 'number') return fallback;
    return `${Math.round(Math.min(Math.max(value, 0), 1) * 100)}%`;
  };

  const tagsFor = (memory: MemoryRecord) => {
    const tags = memory.metadata.tags ?? memory.metadata.themes ?? memory.metadata.theme ?? [];
    return Array.isArray(tags) ? tags.map(String) : [String(tags)];
  };

  const applyFilters = () => {
    void memoryStore.setFilters({
      query,
      character,
      theme,
      memory_type: memoryType,
      start_date: startDate,
      end_date: endDate,
      page_size: $memoryStore.pageSize
    });
  };

  const clearFilters = () => {
    query = '';
    character = '';
    theme = '';
    memoryType = '';
    startDate = '';
    endDate = '';
    selectedIds = [];
    void memoryStore.setFilters({ page: 1, page_size: $memoryStore.pageSize });
  };

  const openMemory = (memory: MemoryRecord) => {
    selectedMemory = memory;
    editedText = memory.text;
  };

  const closeMemory = () => {
    selectedMemory = null;
    editedText = '';
  };

  const saveMemory = async () => {
    if (!selectedMemory) return;
    await memoryStore.updateMemory(selectedMemory.id, editedText, selectedMemory.metadata);
    const refreshed = $memoryStore.memories.find((memory) => memory.id === selectedMemory?.id);
    if (refreshed) openMemory(refreshed);
  };

  const deleteSelectedMemory = async () => {
    if (!selectedMemory) return;
    if (!confirm('Delete this long-term memory? This removes it from local retrieval and cannot be undone.')) return;
    await memoryStore.deleteMemory(selectedMemory.id);
    selectedIds = selectedIds.filter((id) => id !== selectedMemory?.id);
    closeMemory();
  };

  const toggleSelected = (memoryId: string) => {
    selectedIds = selectedIds.includes(memoryId) ? selectedIds.filter((id) => id !== memoryId) : [...selectedIds, memoryId];
  };

  const bulkDelete = async () => {
    if (selectedIds.length === 0) return;
    if (!confirm(`Delete ${selectedIds.length} selected memories? This cannot be undone.`)) return;
    await memoryStore.bulkDelete({ ids: selectedIds, max_delete: selectedIds.length });
    selectedIds = [];
  };

  const pruneOld = async () => {
    if (!pruneDate) return;
    await memoryStore.bulkDelete({
      older_than: pruneDate,
      query,
      character,
      theme,
      memory_type: memoryType,
      max_delete: 100
    });
    showPruneWarning = false;
  };
</script>

<section class="memory-browser" aria-labelledby="memory-title">
  <header class="memory-hero">
    <div>
      <p class="eyebrow">Memory browser</p>
      <h1 id="memory-title">Long-term recall you can inspect and shape</h1>
      <p class="subtitle">Search, edit, and prune durable memories with provenance visible before they influence future conversations.</p>
    </div>
    <button class="ghost-button" type="button" onclick={() => memoryStore.refresh()} disabled={isBusy}>Refresh</button>
  </header>

  {#if $memoryStore.error}
    <div class="memory-notice" role="status">
      <strong>Memory controls need attention.</strong>
      <span>{$memoryStore.error}</span>
      <button type="button" onclick={() => memoryStore.clearError()}>Dismiss</button>
    </div>
  {/if}

  <form class="filter-card" onsubmit={(event) => { event.preventDefault(); applyFilters(); }}>
    <label>
      <span>Search keyword</span>
      <input bind:value={query} placeholder="nickname, promise, theme, source…" />
    </label>
    <label>
      <span>Character</span>
      <input bind:value={character} placeholder="Reverie, Luna…" />
    </label>
    <label>
      <span>Theme / tag</span>
      <input bind:value={theme} placeholder="trust, intimacy, routine…" />
    </label>
    <label>
      <span>Type</span>
      <select bind:value={memoryType}>
        <option value="">Any type</option>
        <option value="semantic">Semantic</option>
        <option value="episodic">Episodic</option>
        <option value="relationship">Relationship</option>
        <option value="journal">Journal</option>
      </select>
    </label>
    <label>
      <span>From</span>
      <input type="date" bind:value={startDate} />
    </label>
    <label>
      <span>To</span>
      <input type="date" bind:value={endDate} />
    </label>
    <div class="filter-actions">
      <button class="primary-button" type="submit" disabled={isBusy}>Search</button>
      <button class="ghost-button" type="button" onclick={clearFilters} disabled={isBusy}>Clear</button>
    </div>
  </form>

  <div class="memory-toolbar">
    <div>
      <strong>{$memoryStore.total}</strong>
      <span>memories found · page {$memoryStore.page} of {Math.max($memoryStore.pages, 1)}</span>
    </div>
    <div class="toolbar-actions">
      <button class="danger-soft" type="button" onclick={bulkDelete} disabled={selectedCount === 0 || isBusy}>Delete selected ({selectedCount})</button>
      <button class="danger-soft" type="button" onclick={() => (showPruneWarning = true)} disabled={isBusy}>Prune old…</button>
    </div>
  </div>

  {#if $memoryStore.loadState === 'loading'}
    <div class="empty-card">Opening the local memory store…</div>
  {:else if $memoryStore.memories.length === 0}
    <div class="empty-card">
      <strong>No memories match yet.</strong>
      <span>Try clearing filters, or continue chatting until reflection and memory promotion have durable evidence.</span>
    </div>
  {:else}
    <div class="memory-grid">
      {#each $memoryStore.memories as memory (memory.id)}
        <article class="memory-card">
          <div class="card-topline">
            <label class="select-row" aria-label="Select memory">
              <input type="checkbox" checked={selectedIds.includes(memory.id)} onchange={() => toggleSelected(memory.id)} />
              <span>{memory.metadata.memory_type ?? 'memory'}</span>
            </label>
            <span class="score-pill">Importance {percent(memory.metadata.importance, 'n/a')}</span>
          </div>
          <button class="memory-open" type="button" onclick={() => openMemory(memory)}>
            <span>{memory.text}</span>
          </button>
          <div class="tag-row">
            {#each tagsFor(memory).slice(0, 4) as tag}
              <small>{tag}</small>
            {/each}
            {#if tagsFor(memory).length === 0}<small>untagged</small>{/if}
          </div>
          <footer>
            <span>Created {formatDate(memory.created_at)}</span>
            <span>{memory.source}</span>
          </footer>
        </article>
      {/each}
    </div>
  {/if}

  <div class="pagination-card">
    <button type="button" onclick={() => memoryStore.setPage(Math.max($memoryStore.page - 1, 1))} disabled={$memoryStore.page <= 1 || isBusy}>Previous</button>
    <span>{$memoryStore.page} / {Math.max($memoryStore.pages, 1)}</span>
    <button type="button" onclick={() => memoryStore.setPage(Math.min($memoryStore.page + 1, Math.max($memoryStore.pages, 1)))} disabled={$memoryStore.page >= $memoryStore.pages || isBusy}>Next</button>
  </div>
</section>

{#if selectedMemory}
  <div class="modal-backdrop" role="presentation" onclick={closeMemory}>
    <div class="memory-modal" role="dialog" aria-modal="true" aria-labelledby="memory-detail-title" tabindex="-1" onclick={(event) => event.stopPropagation()} onkeydown={(event) => event.stopPropagation()}>
      <header>
        <div>
          <p class="eyebrow">Memory detail</p>
          <h2 id="memory-detail-title">Edit recall capsule</h2>
        </div>
        <button class="icon-button" type="button" onclick={closeMemory} aria-label="Close memory detail">×</button>
      </header>
      <div class="provenance-grid">
        <div><span>Created</span><strong>{formatDate(selectedMemory.created_at)}</strong></div>
        <div><span>Updated</span><strong>{formatDate(selectedMemory.updated_at)}</strong></div>
        <div><span>Source</span><strong>{selectedMemory.source}</strong></div>
        <div><span>Confidence</span><strong>{percent(selectedMemory.metadata.confidence)}</strong></div>
        <div><span>Importance</span><strong>{percent(selectedMemory.metadata.importance, 'n/a')}</strong></div>
        <div><span>Session</span><strong>{selectedMemory.metadata.session_id ?? 'default'}</strong></div>
      </div>
      <label class="editor-label">
        <span>Memory content</span>
        <textarea bind:value={editedText} rows="8"></textarea>
      </label>
      <div class="metadata-card">
        <strong>Tags and provenance</strong>
        <pre>{JSON.stringify(selectedMemory.metadata, null, 2)}</pre>
      </div>
      <div class="modal-actions">
        <button class="danger-button" type="button" onclick={deleteSelectedMemory} disabled={isBusy}>Delete memory</button>
        <button class="ghost-button" type="button" onclick={closeMemory}>Cancel</button>
        <button class="primary-button" type="button" onclick={saveMemory} disabled={isBusy || editedText.trim().length === 0}>Save changes</button>
      </div>
    </div>
  </div>
{/if}

{#if showPruneWarning}
  <div class="modal-backdrop" role="presentation" onclick={() => (showPruneWarning = false)}>
    <div class="prune-modal" role="dialog" aria-modal="true" aria-labelledby="prune-title" tabindex="-1" onclick={(event) => event.stopPropagation()} onkeydown={(event) => event.stopPropagation()}>
      <p class="eyebrow">Deletion warning</p>
      <h2 id="prune-title">Prune old matching memories</h2>
      <p>Reverie will delete up to 100 memories created on or before the date below, using the current keyword, character, theme, and type filters. This cannot be undone.</p>
      <label>
        <span>Delete memories older than</span>
        <input type="date" bind:value={pruneDate} />
      </label>
      <div class="modal-actions">
        <button class="ghost-button" type="button" onclick={() => (showPruneWarning = false)}>Cancel</button>
        <button class="danger-button" type="button" onclick={pruneOld} disabled={!pruneDate || isBusy}>Prune memories</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .memory-browser {
    height: 100%;
    overflow: auto;
    padding: 1.25rem;
    border: 1px solid var(--line);
    border-radius: 1.8rem;
    background: linear-gradient(145deg, rgba(30, 24, 38, 0.92), rgba(20, 16, 25, 0.88));
    box-shadow: var(--shadow);
  }

  .memory-hero,
  .filter-card,
  .memory-toolbar,
  .memory-card,
  .empty-card,
  .pagination-card,
  .memory-modal,
  .prune-modal,
  .memory-notice {
    border: 1px solid var(--line);
    background: rgba(255, 255, 255, 0.055);
    backdrop-filter: blur(20px);
  }

  .memory-hero,
  .memory-toolbar {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
  }

  .memory-hero {
    padding: 1.45rem;
    border-radius: 1.5rem;
    background: radial-gradient(circle at 15% 20%, rgba(240, 154, 159, 0.18), transparent 28rem), rgba(255, 255, 255, 0.055);
  }

  .filter-card {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 0.85rem;
    margin-top: 1rem;
    padding: 1rem;
    border-radius: 1.35rem;
  }

  label,
  .editor-label {
    display: grid;
    gap: 0.35rem;
    color: var(--muted);
    font-size: 0.82rem;
    font-weight: 700;
  }

  input,
  select,
  textarea {
    width: 100%;
    border: 1px solid var(--line);
    border-radius: 0.9rem;
    background: rgba(10, 8, 13, 0.55);
    color: var(--text);
    font: inherit;
  }

  input,
  select { padding: 0.72rem 0.8rem; }
  textarea { min-height: 12rem; padding: 0.9rem; resize: vertical; line-height: 1.55; }

  .filter-actions,
  .toolbar-actions,
  .modal-actions,
  .pagination-card {
    display: flex;
    align-items: center;
    gap: 0.65rem;
  }

  .filter-actions { align-self: end; }

  button { cursor: pointer; }
  button:disabled { cursor: default; opacity: 0.56; }

  .primary-button,
  .ghost-button,
  .danger-soft,
  .danger-button,
  .icon-button,
  .pagination-card button,
  .memory-notice button {
    padding: 0.72rem 0.9rem;
    border-radius: 999px;
    color: var(--text);
  }

  .primary-button { background: linear-gradient(135deg, #b95f69, #f09a9f); font-weight: 800; }
  .ghost-button, .pagination-card button, .memory-notice button { border: 1px solid var(--line); background: rgba(255, 255, 255, 0.075); }
  .danger-soft { border: 1px solid rgba(255, 125, 125, 0.25); background: rgba(255, 125, 125, 0.09); color: #ffd2d2; }
  .danger-button { background: linear-gradient(135deg, #78313b, #c55358); font-weight: 800; }
  .icon-button { width: 2.4rem; height: 2.4rem; padding: 0; border: 1px solid var(--line); background: rgba(255, 255, 255, 0.08); font-size: 1.4rem; }

  .memory-notice {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-top: 1rem;
    padding: 0.9rem 1rem;
    border-radius: 1.1rem;
  }
  .memory-notice span { color: var(--muted); }

  .memory-toolbar {
    margin-top: 1rem;
    padding: 0.95rem 1rem;
    border-radius: 1.2rem;
  }
  .memory-toolbar strong { font-size: 1.35rem; }
  .memory-toolbar span { color: var(--muted); margin-left: 0.4rem; }

  .memory-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
    gap: 0.9rem;
    margin-top: 1rem;
  }

  .memory-card {
    display: grid;
    gap: 0.8rem;
    min-height: 13rem;
    padding: 1rem;
    border-radius: 1.25rem;
  }

  .card-topline,
  .memory-card footer,
  .tag-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.55rem;
  }

  .select-row {
    display: flex;
    grid-template-columns: none;
    align-items: center;
    flex-direction: row;
    gap: 0.45rem;
    color: var(--accent-strong);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  .select-row input { width: auto; }

  .score-pill,
  .tag-row small {
    padding: 0.32rem 0.55rem;
    border: 1px solid var(--line);
    border-radius: 999px;
    color: var(--muted);
    background: rgba(255, 255, 255, 0.05);
    font-size: 0.75rem;
  }

  .memory-open {
    min-height: 5.4rem;
    padding: 0;
    color: var(--text);
    background: transparent;
    text-align: left;
    line-height: 1.5;
  }
  .memory-open span {
    display: -webkit-box;
    overflow: hidden;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 4;
    line-clamp: 4;
  }

  .tag-row { justify-content: flex-start; flex-wrap: wrap; }
  .memory-card footer { color: var(--dim); font-size: 0.78rem; }

  .empty-card,
  .pagination-card {
    margin-top: 1rem;
    padding: 1.2rem;
    border-radius: 1.2rem;
    color: var(--muted);
  }
  .empty-card strong,
  .empty-card span { display: block; }
  .empty-card strong { color: var(--text); margin-bottom: 0.3rem; }
  .pagination-card { justify-content: center; }

  .modal-backdrop {
    position: fixed;
    inset: 0;
    display: grid;
    place-items: center;
    padding: 1rem;
    background: rgba(5, 4, 8, 0.72);
    z-index: 20;
  }

  .memory-modal,
  .prune-modal {
    width: min(48rem, 100%);
    max-height: min(90vh, 56rem);
    overflow: auto;
    padding: 1.2rem;
    border-radius: 1.5rem;
    background: linear-gradient(145deg, rgba(35, 28, 43, 0.98), rgba(20, 16, 25, 0.98));
    box-shadow: var(--shadow);
  }
  .memory-modal header { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; }
  .memory-modal h2, .prune-modal h2 { margin: 0.15rem 0 0; }

  .provenance-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
    gap: 0.7rem;
    margin: 1rem 0;
  }
  .provenance-grid div,
  .metadata-card {
    padding: 0.8rem;
    border: 1px solid var(--line);
    border-radius: 1rem;
    background: rgba(255, 255, 255, 0.045);
  }
  .provenance-grid span { display: block; color: var(--dim); font-size: 0.76rem; }
  .provenance-grid strong { display: block; margin-top: 0.25rem; font-size: 0.88rem; }
  .metadata-card { margin-top: 1rem; }
  pre { overflow: auto; color: var(--muted); white-space: pre-wrap; }
  .modal-actions { justify-content: flex-end; margin-top: 1rem; }
  .prune-modal p { color: var(--muted); line-height: 1.55; }

  @media (max-width: 980px) {
    .filter-card { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .memory-hero, .memory-toolbar { flex-direction: column; }
  }
</style>
