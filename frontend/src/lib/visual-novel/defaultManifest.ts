import type { CharacterVisualManifest, VisualExpression, VisualPose } from '$lib/types/visualNovel';
import { createSvgPlaceholderAsset } from './placeholderAssets';

const placeholderSprite = (expression: VisualExpression, pose: VisualPose) =>
  createSvgPlaceholderAsset({
    kind: 'sprite',
    alt: `Reverie ${expression} ${pose} fallback sprite`,
    label: `Reverie ${expression} ${pose}`,
    primary: expression === 'sad' || expression === 'concerned' ? '#b995d7' : '#f09a9f',
    secondary: pose === 'leaning' ? '#9f5f8f' : '#7a4a84',
    expression,
    pose
  });

const placeholderBaseLayer = (pose: VisualPose) =>
  createSvgPlaceholderAsset({
    kind: 'base',
    alt: `Reverie ${pose} base layer`,
    label: `Reverie ${pose} base`,
    primary: '#f09a9f',
    secondary: pose === 'leaning' ? '#9f5f8f' : '#7a4a84',
    pose
  });

const placeholderExpressionLayer = (expression: VisualExpression) =>
  createSvgPlaceholderAsset({
    kind: 'expression',
    alt: `Reverie ${expression} expression layer`,
    label: `Reverie ${expression} expression`,
    expression
  });

const placeholderClothingLayer = (pose: VisualPose) =>
  createSvgPlaceholderAsset({
    kind: 'clothing',
    alt: `Reverie ${pose} clothing layer`,
    label: `Reverie ${pose} clothing`,
    primary: '#2b2032',
    pose
  });

const placeholderBackground = (label: string, primary = '#211826') =>
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
  version: 2,
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
  layerOrder: ['base', 'expression', 'clothing'],
  layers: {
    base: {
      label: 'Base body',
      required: true,
      zIndex: 0,
      assets: {
        byPose: {
          idle: placeholderBaseLayer('idle'),
          listening: placeholderBaseLayer('listening'),
          speaking: placeholderBaseLayer('speaking'),
          leaning: placeholderBaseLayer('leaning')
        }
      }
    },
    expression: {
      label: 'Expression overlay',
      required: true,
      zIndex: 10,
      assets: {
        byExpression: {
          neutral: placeholderExpressionLayer('neutral'),
          happy: placeholderExpressionLayer('happy'),
          sad: placeholderExpressionLayer('sad'),
          thinking: placeholderExpressionLayer('thinking'),
          flirty: placeholderExpressionLayer('flirty'),
          surprised: placeholderExpressionLayer('surprised'),
          concerned: placeholderExpressionLayer('concerned')
        }
      }
    },
    clothing: {
      label: 'Soft lounge clothing',
      zIndex: 20,
      assets: {
        byPose: {
          idle: placeholderClothingLayer('idle'),
          listening: placeholderClothingLayer('listening'),
          speaking: placeholderClothingLayer('speaking'),
          leaning: placeholderClothingLayer('leaning')
        }
      }
    }
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
