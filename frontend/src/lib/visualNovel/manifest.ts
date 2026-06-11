import {
  VISUAL_EXPRESSIONS,
  VISUAL_POSES,
  type CharacterVisualManifest,
  type ResolvedVisualAsset,
  type ResolvedVisualScene,
  type VisualAssetRef,
  type VisualExpression,
  type VisualPose,
  type VisualState
} from '$lib/types/visualNovel';

const PLACEHOLDER_PREFIX = 'placeholder://';
const SPRITE_CACHE_LIMIT = 8;

const expressionPlaceholders = Object.fromEntries(
  VISUAL_EXPRESSIONS.map((expression) => [expression, `${PLACEHOLDER_PREFIX}expression/${expression}`])
) as Record<VisualExpression, VisualAssetRef>;

const posePlaceholders = Object.fromEntries(
  VISUAL_POSES.map((pose) => [pose, `${PLACEHOLDER_PREFIX}pose/${pose}`])
) as Record<VisualPose, VisualAssetRef>;

export const defaultVisualManifest: CharacterVisualManifest = {
  characterId: 'reverie',
  defaultBackground: `${PLACEHOLDER_PREFIX}background/default`,
  fallbackExpression: 'neutral',
  expressions: expressionPlaceholders,
  poses: posePlaceholders,
  backgrounds: {
    default: `${PLACEHOLDER_PREFIX}background/default`,
    'slime-cave': `${PLACEHOLDER_PREFIX}background/slime-cave`,
    bedroom: `${PLACEHOLDER_PREFIX}background/bedroom`,
    'rain-window': `${PLACEHOLDER_PREFIX}background/rain-window`,
    'garden-night': `${PLACEHOLDER_PREFIX}background/garden-night`,
    studio: `${PLACEHOLDER_PREFIX}background/studio`
  },
  layers: ['base', 'expression', 'clothing']
};

export class VisualAssetCache {
  private readonly maxEntries: number;
  private readonly entries = new Map<string, HTMLImageElement>();

  constructor(maxEntries = SPRITE_CACHE_LIMIT) {
    this.maxEntries = maxEntries;
  }

  preload(asset: ResolvedVisualAsset): void {
    if (!asset.src || asset.kind === 'placeholder' || typeof Image === 'undefined') {
      return;
    }

    if (this.entries.has(asset.src)) {
      const existing = this.entries.get(asset.src);
      this.entries.delete(asset.src);
      if (existing) {
        this.entries.set(asset.src, existing);
      }
      return;
    }

    const image = new Image();
    image.decoding = 'async';
    image.src = asset.src;
    this.entries.set(asset.src, image);
    this.trim();
  }

  size(): number {
    return this.entries.size;
  }

  private trim(): void {
    while (this.entries.size > this.maxEntries) {
      const oldestKey = this.entries.keys().next().value;
      if (!oldestKey) {
        return;
      }
      this.entries.delete(oldestKey);
    }
  }
}

export const visualAssetCache = new VisualAssetCache();

export const resolveVisualScene = (
  manifest: CharacterVisualManifest,
  visualState: VisualState
): ResolvedVisualScene => {
  const fallbackExpression = manifest.fallbackExpression;
  const expressionRef = manifest.expressions[visualState.expression] ?? manifest.expressions[fallbackExpression];
  const poseRef = manifest.poses[visualState.pose] ?? manifest.poses.idle;
  const backgroundRef = manifest.backgrounds?.[visualState.background] ?? manifest.defaultBackground;

  return {
    background: resolveAsset(backgroundRef, `background:${visualState.background}`, 'Scene background', !manifest.backgrounds?.[visualState.background]),
    pose: resolveAsset(poseRef, `pose:${visualState.pose}`, `${visualState.pose} pose`, !manifest.poses[visualState.pose]),
    expression: resolveAsset(
      expressionRef,
      `expression:${visualState.expression}`,
      `${visualState.expression} expression`,
      !manifest.expressions[visualState.expression]
    )
  };
};

export const preloadVisualSceneAssets = (scene: ResolvedVisualScene, cache = visualAssetCache): void => {
  cache.preload(scene.background);
  cache.preload(scene.pose);
  cache.preload(scene.expression);
};

export const isPlaceholderAsset = (asset: ResolvedVisualAsset): boolean => asset.kind === 'placeholder';

const resolveAsset = (
  asset: VisualAssetRef | undefined,
  slot: string,
  label: string,
  fallbackUsed: boolean
): ResolvedVisualAsset => {
  if (!asset) {
    return { kind: 'placeholder', slot, label, fallbackUsed: true };
  }

  if (typeof asset === 'string') {
    if (!asset || asset.startsWith(PLACEHOLDER_PREFIX)) {
      return { kind: 'placeholder', slot, label, fallbackUsed };
    }

    return { kind: 'image', src: asset, slot, label, fallbackUsed };
  }

  return {
    kind: 'spritesheet',
    src: asset.src,
    frame: asset.frame,
    label: asset.label ?? label,
    slot,
    fallbackUsed
  };
};
