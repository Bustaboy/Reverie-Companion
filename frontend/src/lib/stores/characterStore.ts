import { derived, get, writable } from 'svelte/store';
import {
  CharacterServiceError,
  characterService,
  type CharacterBlueprint,
  type CharacterCreateInput,
  type CharacterSummary
} from '$lib/api/characterService';

export interface CharacterState {
  characters: CharacterSummary[];
  selectedCharacter: CharacterBlueprint | null;
  selectedCharacterId: string | null;
  loading: boolean;
  error: string | null;
  hasLoaded: boolean;
}

const STORAGE_KEY = 'reverie.selectedCharacterId';

const INITIAL_STATE: CharacterState = {
  characters: [],
  selectedCharacter: null,
  selectedCharacterId: null,
  loading: false,
  error: null,
  hasLoaded: false
};

const getStoredCharacterId = (): string | null => {
  if (typeof localStorage === 'undefined') return null;
  return localStorage.getItem(STORAGE_KEY);
};

const storeCharacterId = (characterId: string | null) => {
  if (typeof localStorage === 'undefined') return;
  if (characterId) localStorage.setItem(STORAGE_KEY, characterId);
  else localStorage.removeItem(STORAGE_KEY);
};

const toFriendlyError = (error: unknown): string =>
  error instanceof CharacterServiceError ? error.message : 'Reverie could not load saved characters right now.';

function createCharacterStore() {
  const store = writable<CharacterState>(INITIAL_STATE);

  const selectCharacter = async (characterId: string | null) => {
    storeCharacterId(characterId);

    if (!characterId) {
      store.update((state) => ({ ...state, selectedCharacterId: null, selectedCharacter: null, error: null }));
      return;
    }

    store.update((state) => ({ ...state, loading: true, error: null, selectedCharacterId: characterId }));

    try {
      const selectedCharacter = await characterService.getCharacter(characterId);
      store.update((state) => ({ ...state, selectedCharacter, selectedCharacterId: characterId, loading: false }));
    } catch (error) {
      store.update((state) => ({ ...state, loading: false, error: toFriendlyError(error) }));
    }
  };

  const loadCharacters = async () => {
    store.update((state) => ({ ...state, loading: true, error: null }));

    try {
      const characters = await characterService.listCharacters();
      const storedId = getStoredCharacterId();
      const currentId = get(store).selectedCharacterId;
      const selectedCharacterId = [currentId, storedId].find((id) => id && characters.some((character) => character.character_id === id)) ?? null;
      let selectedCharacter: CharacterBlueprint | null = null;

      if (selectedCharacterId) {
        selectedCharacter = await characterService.getCharacter(selectedCharacterId);
      }

      store.update((state) => ({
        ...state,
        characters,
        selectedCharacter,
        selectedCharacterId,
        loading: false,
        hasLoaded: true
      }));
      storeCharacterId(selectedCharacterId);
    } catch (error) {
      store.update((state) => ({ ...state, loading: false, hasLoaded: true, error: toFriendlyError(error) }));
    }
  };

  return {
    subscribe: store.subscribe,
    loadCharacters,
    selectCharacter,
    async createBasicCharacter(input: CharacterCreateInput): Promise<CharacterBlueprint | null> {
      store.update((state) => ({ ...state, loading: true, error: null }));

      try {
        const character = await characterService.createBasicCharacter(input);
        await loadCharacters();
        await selectCharacter(character.character_id);
        return character;
      } catch (error) {
        store.update((state) => ({ ...state, loading: false, error: toFriendlyError(error) }));
        return null;
      }
    },
    clearError() {
      store.update((state) => ({ ...state, error: null }));
    }
  };
}

export const characterStore = createCharacterStore();

export const selectedCharacterId = derived(characterStore, ($characterStore) => $characterStore.selectedCharacterId);
export const selectedCharacterIdentity = derived(characterStore, ($characterStore) => $characterStore.selectedCharacter?.identity ?? null);
