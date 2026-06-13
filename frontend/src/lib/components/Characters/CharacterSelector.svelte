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

  const refreshCharacters = () => {
    void characterStore.loadCharacters();
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
    </div>
  </div>
</aside>
