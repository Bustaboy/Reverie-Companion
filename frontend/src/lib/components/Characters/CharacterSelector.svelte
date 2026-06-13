<script lang="ts">
  import { onMount } from 'svelte';
  import { characterStore } from '$lib/stores/characterStore';

  onMount(() => {
    if (!$characterStore.hasLoaded) void characterStore.loadCharacters();
  });

  const selectCharacter = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement;
    void characterStore.selectCharacter(target.value || null);
  };

  let showCreateForm = $state(false);
  let newDisplayName = $state('');
  let newPronouns = $state('');

  const refreshCharacters = () => {
    void characterStore.loadCharacters();
  };

  const openCreateForm = () => {
    characterStore.clearError();
    newDisplayName = '';
    newPronouns = '';
    showCreateForm = true;
  };

  const closeCreateForm = () => {
    showCreateForm = false;
  };

  const createCharacter = async () => {
    const character = await characterStore.createBasicCharacter({
      display_name: newDisplayName.trim() || 'New Companion',
      pronouns: newPronouns.trim() || 'she/her'
    });

    if (character) closeCreateForm();
  };

  const selectedSummary = $derived.by(() => {
    const character = $characterStore.selectedCharacter;
    if (!character) return 'Using Reverie’s default local companion until you choose a saved character.';

    const relationship = character.relationship?.relationship_dynamic;
    const traits = character.personality?.core_traits?.slice(0, 3).join(', ');
    return [relationship, traits ? `Traits: ${traits}` : null].filter(Boolean).join(' · ') || 'Saved character runtime is active for this chat.';
  });

  const selectedName = $derived($characterStore.selectedCharacter?.identity.display_name ?? 'Default Reverie');
  const selectedPronouns = $derived($characterStore.selectedCharacter?.identity.pronouns ?? 'local fallback');
</script>

<aside class="character-runtime-card" aria-label="Character runtime selector">
  <div class="character-runtime-copy">
    <p class="eyebrow">Active companion</p>
    <h2>{selectedName}</h2>
    <p class="character-pronouns">{selectedPronouns}</p>
    <p>{selectedSummary}</p>
    {#if $characterStore.error}
      <span class="character-error">{$characterStore.error}</span>
    {/if}
  </div>

  <div class="character-runtime-controls">
    <label for="character-select">Saved character</label>
    <div class="character-select-row">
      <select id="character-select" value={$characterStore.selectedCharacterId ?? ''} disabled={$characterStore.loading} onchange={selectCharacter}>
        <option value="">Default local companion</option>
        {#each $characterStore.characters as character (character.character_id)}
          <option value={character.character_id}>{character.display_name} · {character.pronouns}</option>
        {/each}
      </select>
      <button type="button" class="ghost-button" disabled={$characterStore.loading} onclick={openCreateForm}>+ New</button>
      <button type="button" class="ghost-button" disabled={$characterStore.loading} onclick={refreshCharacters}>
        {$characterStore.loading ? 'Loading…' : 'Refresh'}
      </button>
    </div>
  </div>
</aside>

{#if showCreateForm}
  <div class="character-create-backdrop" role="presentation" onclick={closeCreateForm}></div>
  <div class="character-create-modal" role="dialog" aria-modal="true" aria-labelledby="character-create-title">
    <form onsubmit={(event) => { event.preventDefault(); void createCharacter(); }}>
      <header>
        <div>
          <p class="eyebrow">Quick character</p>
          <h2 id="character-create-title">Create new character</h2>
        </div>
        <button type="button" class="ghost-button" onclick={closeCreateForm} aria-label="Close character creator">Close</button>
      </header>

      <label>
        Display name
        <input bind:value={newDisplayName} name="display-name" type="text" placeholder="Reverie" autocomplete="off" />
      </label>

      <label>
        Pronouns
        <input bind:value={newPronouns} name="pronouns" type="text" placeholder="she/her" autocomplete="off" />
      </label>

      <p class="character-create-note">This only creates a basic local character shell. Deeper identity, visual, and relationship setup can come later.</p>

      <footer>
        <button type="button" class="ghost-button" onclick={closeCreateForm} disabled={$characterStore.loading}>Cancel</button>
        <button type="submit" class="ghost-button primary" disabled={$characterStore.loading}>
          {$characterStore.loading ? 'Creating…' : 'Create and select'}
        </button>
      </footer>
    </form>
  </div>
{/if}
