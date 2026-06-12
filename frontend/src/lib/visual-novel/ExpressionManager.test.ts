import { describe, expect, it } from 'vitest';
import { DEFAULT_CHARACTER_VISUAL_MANIFEST } from './defaultManifest';
import { expressionManager } from './ExpressionManager';
import type { CharacterVisualManifest } from '$lib/types/visualNovel';

const cloneManifest = (): CharacterVisualManifest => structuredClone(DEFAULT_CHARACTER_VISUAL_MANIFEST);

describe('ExpressionManager layered visual resolution', () => {
  it('composes character layers in base to expression to clothing order', () => {
    const scene = expressionManager.resolveScene(DEFAULT_CHARACTER_VISUAL_MANIFEST, {
      expression: 'happy',
      pose: 'idle',
      background: 'default'
    });

    expect(scene.characterLayers.map((layer) => layer.slot)).toEqual(['base', 'expression', 'clothing']);
    expect(scene.characterLayers.map((layer) => layer.order)).toEqual([0, 10, 20]);
    expect(scene.characterLayers[1].asset.alt).toContain('happy expression');
    expect(scene.usedFallback).toBe(false);
  });

  it('falls back per missing or failed layer without dropping the full scene', () => {
    const manifest = cloneManifest();
    const failedBaseSrc = manifest.layers?.[0].assets.idle?.default?.src;
    const failedExpressionSrc = manifest.layers?.[1].assets.idle?.happy?.src;
    const scene = expressionManager.resolveScene(
      manifest,
      { expression: 'happy', pose: 'idle', background: 'default' },
      new Set([failedBaseSrc, failedExpressionSrc].filter((src): src is string => Boolean(src)))
    );

    expect(scene.characterLayers).toHaveLength(3);
    expect(scene.characterLayers[0].usedFallback).toBe(true);
    expect(scene.characterLayers[1].usedFallback).toBe(true);
    expect(scene.characterLayers[2].usedFallback).toBe(false);
    expect(scene.usedFallback).toBe(true);
  });

  it('preserves sprite sheet frame metadata and resolves relative sheet paths', () => {
    const manifest = cloneManifest();
    manifest.assetBasePath = 'characters/reverie';
    manifest.layers = [
      {
        id: 'sheet-base',
        slot: 'base',
        label: 'Sheet base',
        required: true,
        assets: {
          idle: {
            default: {
              kind: 'image',
              src: 'sprites/body-sheet.png',
              alt: 'Reverie body sheet frame',
              frame: { x: 256, y: 0, width: 256, height: 512, sheetWidth: 1024, sheetHeight: 512 }
            }
          }
        }
      }
    ];

    const scene = expressionManager.resolveScene(manifest, { expression: 'neutral', pose: 'idle' });

    expect(scene.characterLayers).toHaveLength(1);
    expect(scene.characterLayers[0].asset.src).toBe('characters/reverie/sprites/body-sheet.png');
    expect(scene.characterLayers[0].asset.frame).toEqual({ x: 256, y: 0, width: 256, height: 512, sheetWidth: 1024, sheetHeight: 512 });
  });

  it('keeps legacy single-sprite manifests working when no layers are authored', () => {
    const manifest = cloneManifest();
    manifest.layers = undefined;

    const scene = expressionManager.resolveScene(manifest, { expression: 'flirty', pose: 'leaning' });

    expect(scene.characterLayers).toHaveLength(1);
    expect(scene.characterLayers[0].id).toBe('legacy-sprite');
    expect(scene.characterLayers[0].asset.alt).toContain('flirty leaning');
  });
});
