import {
  VISUAL_EXPRESSIONS,
  VISUAL_POSES,
  type CharacterVisualManifest,
  type ResolvedCharacterLayer,
  type ResolvedVisualAsset,
  type ResolvedVisualScene,
  type VisualAssetLayer,
  type VisualAssetRef,
  type VisualExpression,
  type VisualPose,
  type VisualState
} from '$lib/types/visualNovel';

const PLACEHOLDER_PREFIX = 'placeholder://';
const SPRITE_CACHE_LIMIT = 8;
const CORE_LAYER_ORDER: VisualAssetLayer[] = ['base', 'expression', 'clothing'];

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
  layerAssets: {
    clothing: `${PLACEHOLDER_PREFIX}layer/clothing`
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
  const pose = resolveAsset(poseRef, `pose:${visualState.pose}`, `${visualState.pose} pose`, !manifest.poses[visualState.pose]);
  const expression = resolveAsset(
    expressionRef,
    `expression:${visualState.expression}`,
    `${visualState.expression} expression`,
    !manifest.expressions[visualState.expression]
  );

  return {
    background: resolveAsset(backgroundRef, `background:${visualState.background}`, 'Scene background', !manifest.backgrounds?.[visualState.background]),
    pose,
    expression,
    characterLayers: resolveCharacterLayers(manifest, pose, expression)
  };
};

export const preloadVisualSceneAssets = (scene: ResolvedVisualScene, cache = visualAssetCache): void => {
  cache.preload(scene.background);
  for (const layer of scene.characterLayers) {
    cache.preload(layer.asset);
  }
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

const resolveCharacterLayers = (
  manifest: CharacterVisualManifest,
  pose: ResolvedVisualAsset,
  expression: ResolvedVisualAsset
): ResolvedCharacterLayer[] => {
  const orderedLayers = ensureCoreLayers(manifest.layers);
  const layers: ResolvedCharacterLayer[] = [];

  for (const layer of orderedLayers) {
    if (layer === 'base') {
      layers.push({ layer, asset: pose });
      continue;
    }

    if (layer === 'expression') {
      layers.push({ layer, asset: expression });
      continue;
    }

    layers.push({
      layer,
      asset: resolveAsset(
        manifest.layerAssets?.[layer] ?? `${PLACEHOLDER_PREFIX}layer/${layer}`,
        `layer:${layer}`,
        `${layer} layer`,
        !manifest.layerAssets?.[layer]
      )
    });
  }

  return layers.length ? layers : [
    { layer: 'base', asset: pose },
    { layer: 'expression', asset: expression }
  ];
};

const ensureCoreLayers = (layers: VisualAssetLayer[]): VisualAssetLayer[] => {
  const requestedLayers = layers.length ? layers : ['base', 'expression'];
  const uniqueLayers = Array.from(new Set(requestedLayers));

  // Core VN layers are composited in a stable order even when a manifest is
  // authored out of order. Custom future layers remain supported after core.
  const coreLayers = CORE_LAYER_ORDER.filter(
    (layer) => layer === 'base' || layer === 'expression' || uniqueLayers.includes(layer)
  );
  const customLayers = uniqueLayers.filter((layer) => !CORE_LAYER_ORDER.includes(layer));

  return [...coreLayers, ...customLayers];
};
