import type { CharacterVisualManifest, VisualAssetRef } from '$lib/types/visualNovel';
import { createSvgPlaceholderAsset } from './placeholderAssets';

const placeholderSprite = (expression: string, pose: string): VisualAssetRef =>
  createSvgPlaceholderAsset({
    kind: 'sprite',
    alt: `Reverie ${expression} ${pose} placeholder`,
    label: `Reverie ${expression} ${pose}`,
    primary: expression === 'sad' || expression === 'concerned' ? '#b995d7' : '#f09a9f',
    secondary: pose === 'leaning' ? '#9f5f8f' : '#7a4a84'
  });

const placeholderBackground = (label: string, primary = '#211826'): VisualAssetRef =>
  createSvgPlaceholderAsset({
    kind: 'background',
    alt: `${label} background placeholder`,
    label,
    primary,
    secondary: '#100d14'
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
    default: placeholderBackground('Warm default visual novel room'),
    bedroom: placeholderBackground('Soft bedroom', '#241824'),
    cafe: placeholderBackground('Quiet cafe', '#242019'),
    night: placeholderBackground('Night room', '#151827')
  },
  sprites: {
    idle: {
      neutral: placeholderSprite('neutral', 'idle'),
      happy: placeholderSprite('happy', 'idle'),
      sad: placeholderSprite('sad', 'idle'),
      thinking: placeholderSprite('thinking', 'idle'),
      flirty: placeholderSprite('flirty', 'idle'),
      surprised: placeholderSprite('surprised', 'idle'),
      concerned: placeholderSprite('concerned', 'idle')
    },
    listening: {
      neutral: placeholderSprite('neutral', 'listening')
    },
    speaking: {
      neutral: placeholderSprite('neutral', 'speaking'),
      happy: placeholderSprite('happy', 'speaking')
    },
    leaning: {
      neutral: placeholderSprite('neutral', 'leaning'),
      flirty: placeholderSprite('flirty', 'leaning')
    }
  }
};
