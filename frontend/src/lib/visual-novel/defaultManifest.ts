import type { CharacterVisualManifest, VisualAssetRef } from '$lib/types/visualNovel';

const placeholderSprite = (alt: string): VisualAssetRef => ({
  kind: 'placeholder',
  alt,
  dominantColor: '#f09a9f'
});

const placeholderBackground = (alt: string, dominantColor = '#1b1723'): VisualAssetRef => ({
  kind: 'placeholder',
  alt,
  dominantColor
});

export const DEFAULT_CHARACTER_VISUAL_MANIFEST: CharacterVisualManifest = {
  id: 'reverie-default',
  characterName: 'Reverie',
  version: 1,
  defaults: {
    expression: 'neutral',
    pose: 'idle',
    background: 'default'
  },
  expressions: {
    neutral: { label: 'Neutral' },
    happy: { label: 'Happy' },
    sad: { label: 'Sad' },
    thinking: { label: 'Thinking' },
    flirty: { label: 'Flirty' },
    surprised: { label: 'Surprised' },
    concerned: { label: 'Concerned' }
  },
  poses: {
    idle: { label: 'Idle' },
    listening: { label: 'Listening' },
    speaking: { label: 'Speaking' },
    leaning: { label: 'Leaning closer' }
  },
  backgrounds: {
    default: placeholderBackground('Warm default visual novel background'),
    bedroom: placeholderBackground('Soft bedroom background placeholder', '#211826'),
    cafe: placeholderBackground('Quiet cafe background placeholder', '#242019'),
    night: placeholderBackground('Night room background placeholder', '#151827')
  },
  sprites: {
    idle: {
      neutral: placeholderSprite('Reverie neutral idle placeholder'),
      happy: placeholderSprite('Reverie happy idle placeholder'),
      sad: placeholderSprite('Reverie sad idle placeholder'),
      thinking: placeholderSprite('Reverie thinking idle placeholder'),
      flirty: placeholderSprite('Reverie flirty idle placeholder'),
      surprised: placeholderSprite('Reverie surprised idle placeholder'),
      concerned: placeholderSprite('Reverie concerned idle placeholder')
    },
    listening: {
      neutral: placeholderSprite('Reverie neutral listening placeholder')
    },
    speaking: {
      neutral: placeholderSprite('Reverie neutral speaking placeholder'),
      happy: placeholderSprite('Reverie happy speaking placeholder')
    },
    leaning: {
      neutral: placeholderSprite('Reverie leaning closer placeholder'),
      flirty: placeholderSprite('Reverie flirty leaning closer placeholder')
    }
  }
};
