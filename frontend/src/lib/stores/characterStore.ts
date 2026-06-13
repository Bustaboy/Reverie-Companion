import { derived, get, writable } from 'svelte/store';
import { characterService, CharacterServiceError } from '$lib/api/characterService';
import type { CharacterBlueprint, CharacterSummary } from '$lib/types/character';

export const DEFAULT_CHARACTER_ID = 'default';

export interface CharacterRuntimeFallback {
  character_id: typeof DEFAULT_CHARACTER_ID;
  display_name: 'Reverie';
  pronouns: 'she/her';
  relationship_dynamic: 'warm, emotionally attentive companion';
  core_traits: string[];
  isFallback: true;
}

export type SelectedCharacterView = CharacterRuntimeFallback | (CharacterSummary & { isFallback?: false });

export interface CharacterState {
  characters: CharacterSummary[];
  selectedCharacterId: string | null;
  selectedCharacter: CharacterBlueprint | null;
  loading: boolean;
  error: string | null;
}

export const defaultCharacter: CharacterRuntimeFallback = {
  character_id: DEFAULT_CHARACTER_ID,
  display_name: 'Reverie',
  pronouns: 'she/her',
  relationship_dynamic: 'warm, emotionally attentive companion',
  core_traits: ['warm', 'curious', 'emotionally attentive'],
  isFallback: true
};

const INITIAL_STATE: CharacterState = {
  characters: [],
  selectedCharacterId: null,
  selectedCharacter: null,
  loading: false,
  error: null
};

const toFriendlyError = (error: unknown): string =>
  error instanceof CharacterServiceError ? error.message : 'Characters could not be loaded from the local library.';

function createCharacterStore() {
  const store = writable<CharacterState>(INITIAL_STATE);

  return {
    subscribe: store.subscribe,
    async loadCharacters() {
      store.update((state) => ({ ...state, loading: true, error: null }));
      try {
        const characters = await characterService.listCharacters();
        const selectedCharacterId = get(store).selectedCharacterId;
        store.update((state) => ({
          ...state,
          characters,
          selectedCharacterId: selectedCharacterId && characters.some((item) => item.character_id === selectedCharacterId) ? selectedCharacterId : null,
          selectedCharacter: selectedCharacterId ? state.selectedCharacter : null,
          loading: false
        }));
      } catch (error) {
        store.update((state) => ({ ...state, loading: false, error: toFriendlyError(error) }));
      }
    },
    async selectCharacter(characterId: string | null) {
      if (!characterId || characterId === DEFAULT_CHARACTER_ID) {
        store.update((state) => ({ ...state, selectedCharacterId: null, selectedCharacter: null, error: null }));
        return;
      }

      store.update((state) => ({ ...state, selectedCharacterId: characterId, loading: true, error: null }));
      try {
        const selectedCharacter = await characterService.getCharacter(characterId);
        store.update((state) => ({ ...state, selectedCharacter, loading: false }));
      } catch (error) {
        store.update((state) => ({
          ...state,
          selectedCharacterId: null,
          selectedCharacter: null,
          loading: false,
          error: toFriendlyError(error)
        }));
      }
    },
    clearError() {
      store.update((state) => ({ ...state, error: null }));
    }
  };
}

export const characterStore = createCharacterStore();

export const activeCharacter = derived<typeof characterStore, SelectedCharacterView>(characterStore, ($characterStore) => {
  if (!$characterStore.selectedCharacterId) return defaultCharacter;
  return $characterStore.characters.find((character) => character.character_id === $characterStore.selectedCharacterId) ?? defaultCharacter;
});

export const selectedCharacterIdForChat = derived(characterStore, ($characterStore) => $characterStore.selectedCharacterId);
