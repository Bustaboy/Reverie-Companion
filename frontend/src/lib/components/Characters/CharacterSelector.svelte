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

  let showCreateModal = $state(false);
  let newDisplayName = $state('');
  let newPronouns = $state('she/her');

  const refreshCharacters = () => {
    void characterStore.loadCharacters();
  };

  const openCreateModal = () => {
    characterStore.clearError();
    newDisplayName = '';
    newPronouns = 'she/her';
    showCreateModal = true;
  };

  const closeCreateModal = () => {
    if ($characterStore.loading) return;
    showCreateModal = false;
  };

  const createCharacter = async (event: Event) => {
    event.preventDefault();

    const displayName = newDisplayName.trim();
    const pronouns = newPronouns.trim();
    if (!displayName) return;

    await characterStore.createBasicCharacter({
      display_name: displayName,
      pronouns: pronouns || undefined
    });

    if (!$characterStore.error) showCreateModal = false;
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
      <button type="button" class="ghost-button" disabled={$characterStore.loading} onclick={refreshCharacters}>
        {$characterStore.loading ? 'Loading…' : 'Refresh'}
      </button>
      <button type="button" class="ghost-button new-character-button" disabled={$characterStore.loading} onclick={openCreateModal}>
        + New
      </button>
    </div>
  </div>
</aside>


{#if showCreateModal}
  <div class="character-create-backdrop" role="presentation" onclick={closeCreateModal}></div>
  <div class="character-create-modal" role="dialog" aria-modal="true" aria-labelledby="character-create-title">
    <form onsubmit={createCharacter}>
      <header>
        <div>
          <p class="eyebrow">Quick character</p>
          <h2 id="character-create-title">Create new character</h2>
        </div>
        <button type="button" class="ghost-button" disabled={$characterStore.loading} onclick={closeCreateModal}>Close</button>
      </header>

      <p class="character-create-note">A minimal local companion shell for chatting now. You can expand their identity later.</p>

      <label>
        Display name
        <input bind:value={newDisplayName} placeholder="Mira" autocomplete="off" disabled={$characterStore.loading} />
      </label>

      <label>
        Pronouns
        <input bind:value={newPronouns} placeholder="she/her" autocomplete="off" disabled={$characterStore.loading} />
      </label>

      <footer>
        <button type="button" class="ghost-button" disabled={$characterStore.loading} onclick={closeCreateModal}>Cancel</button>
        <button type="submit" class="create-character-submit" disabled={$characterStore.loading || !newDisplayName.trim()}>
          {$characterStore.loading ? 'Creating…' : 'Create and select'}
        </button>
      </footer>
    </form>
  </div>
{/if}
