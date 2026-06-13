<script lang="ts">
  import { onMount } from 'svelte';
  import { activeCharacter, characterStore, DEFAULT_CHARACTER_ID } from '$lib/stores/characterStore';

  onMount(() => {
    void characterStore.loadCharacters();
  });

  const handleSelection = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement;
    void characterStore.selectCharacter(target.value === DEFAULT_CHARACTER_ID ? null : target.value);
  };

  const dismissError = () => {
    characterStore.clearError();
  };
</script>

<section class="character-selector" aria-label="Character runtime selection">
  <div class="character-selector-control">
    <label for="character-select">Companion</label>
    <select id="character-select" value={$characterStore.selectedCharacterId ?? DEFAULT_CHARACTER_ID} onchange={handleSelection} disabled={$characterStore.loading}>
      <option value={DEFAULT_CHARACTER_ID}>Default Reverie</option>
      {#each $characterStore.characters as character (character.character_id)}
        <option value={character.character_id}>{character.display_name}</option>
      {/each}
    </select>
  </div>

  <div class="character-identity-card" class:fallback={$activeCharacter.isFallback}>
    <div class="character-avatar" aria-hidden="true">{$activeCharacter.display_name.slice(0, 1).toUpperCase()}</div>
    <div>
      <strong>{$activeCharacter.display_name}</strong>
      <span>{$activeCharacter.pronouns}</span>
      <p>{$activeCharacter.relationship_dynamic}</p>
      {#if $activeCharacter.core_traits.length}
        <small>{$activeCharacter.core_traits.slice(0, 3).join(' · ')}</small>
      {/if}
    </div>
  </div>

  {#if $characterStore.error}
    <div class="character-selector-error" role="status" aria-live="polite">
      <span>{$characterStore.error}</span>
      <button type="button" onclick={dismissError}>Dismiss</button>
    </div>
  {/if}
</section>
