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

const placeholderLayer = (slot: 'base-layer' | 'expression-layer' | 'clothing-layer', label: string, primary = '#f09a9f'): VisualAssetRef =>
  createSvgPlaceholderAsset({
    kind: slot,
    alt: `Reverie ${label} layer placeholder`,
    label: `Reverie ${label}`,
    primary,
    secondary: slot === 'clothing-layer' ? '#7a4a84' : '#9f5f8f'
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
  layers: [
    {
      id: 'reverie-base',
      slot: 'base',
      label: 'Body base',
      order: 0,
      required: true,
      assets: {
        idle: { default: placeholderLayer('base-layer', 'base idle') },
        listening: { default: placeholderLayer('base-layer', 'base listening', '#f2a7ad') },
        speaking: { default: placeholderLayer('base-layer', 'base speaking', '#ffaaa8') },
        leaning: { default: placeholderLayer('base-layer', 'base leaning closer', '#f09a9f') }
      }
    },
    {
      id: 'reverie-expression',
      slot: 'expression',
      label: 'Expression overlay',
      order: 10,
      required: true,
      assets: {
        idle: {
          neutral: placeholderLayer('expression-layer', 'neutral expression'),
          happy: placeholderLayer('expression-layer', 'happy expression', '#ffb0a6'),
          sad: placeholderLayer('expression-layer', 'sad expression', '#b995d7'),
          thinking: placeholderLayer('expression-layer', 'thinking expression', '#c9a4e0'),
          flirty: placeholderLayer('expression-layer', 'flirty expression', '#f09a9f'),
          surprised: placeholderLayer('expression-layer', 'surprised expression', '#ffd0bd'),
          concerned: placeholderLayer('expression-layer', 'concerned expression', '#b995d7')
        },
        speaking: { happy: placeholderLayer('expression-layer', 'happy speaking expression', '#ffb0a6') }
      }
    },
    {
      id: 'reverie-clothing',
      slot: 'clothing',
      label: 'Soft lounge outfit',
      order: 20,
      assets: {
        idle: { default: placeholderLayer('clothing-layer', 'soft lounge outfit', '#7a4a84') },
        leaning: { default: placeholderLayer('clothing-layer', 'soft lounge outfit leaning', '#8b568f') }
      }
    }
  ],
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
