import { describe, expect, it } from 'vitest';
import { expressionManager } from './ExpressionManager';
import { DEFAULT_CHARACTER_VISUAL_MANIFEST } from './defaultManifest';
import type { CharacterVisualManifest } from '$lib/types/visualNovel';

describe('ExpressionManager layered rendering', () => {
  it('composes manifest layers in base to expression to clothing order', () => {
    const scene = expressionManager.resolveScene(DEFAULT_CHARACTER_VISUAL_MANIFEST, {
      expression: 'happy',
      pose: 'leaning',
      background: 'bedroom'
    });

    expect(scene.compositionMode).toBe('layers');
    expect(scene.layers.map((layer) => layer.name)).toEqual(['base', 'expression', 'clothing']);
    expect(scene.layers.map((layer) => layer.zIndex)).toEqual([0, 10, 20]);
    expect(scene.layers[1].asset.alt).toContain('happy expression layer');
    expect(scene.usedFallback).toBe(false);
  });

  it('skips missing optional layers but falls back when required layers fail', () => {
    const manifest: CharacterVisualManifest = {
      ...DEFAULT_CHARACTER_VISUAL_MANIFEST,
      layers: {
        base: DEFAULT_CHARACTER_VISUAL_MANIFEST.layers?.base,
        expression: {
          label: 'Expression overlay',
          required: true,
          assets: {
            byExpression: {
              neutral: {
                kind: 'image',
                src: 'missing-expression.png',
                alt: 'Missing expression layer'
              }
            }
          }
        },
        accessory: {
          label: 'Optional accessory',
          assets: {}
        }
      }
    };

    const scene = expressionManager.resolveScene(manifest, { expression: 'neutral', pose: 'idle' }, new Set(['missing-expression.png']));

    expect(scene.compositionMode).toBe('sprite');
    expect(scene.layers).toEqual([]);
    expect(scene.sprite.alt).toContain('neutral idle fallback sprite');
    expect(scene.usedFallback).toBe(true);
  });

  it('normalizes relative layer paths and preserves future sprite sheet frame metadata', () => {
    const manifest: CharacterVisualManifest = {
      ...DEFAULT_CHARACTER_VISUAL_MANIFEST,
      assetBasePath: '/characters/reverie',
      layerOrder: ['base', 'expression'],
      layers: {
        base: {
          label: 'Sheet base',
          required: true,
          assets: {
            byPose: {
              idle: {
                kind: 'image',
                src: 'sprites/body-sheet.png',
                alt: 'Idle body sheet frame',
                frame: { x: 720, y: 0, width: 720, height: 1000 }
              }
            }
          }
        },
        expression: DEFAULT_CHARACTER_VISUAL_MANIFEST.layers?.expression
      }
    };

    const scene = expressionManager.resolveScene(manifest, { expression: 'flirty', pose: 'idle' });

    expect(scene.compositionMode).toBe('layers');
    expect(scene.layers[0].asset.src).toBe('/characters/reverie/sprites/body-sheet.png');
    expect(scene.layers[0].asset.frame).toEqual({ x: 720, y: 0, width: 720, height: 1000 });
  });
});
