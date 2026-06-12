import type {
  CharacterVisualLayerDefinition,
  CharacterVisualManifest,
  NormalizedVisualState,
  ResolvedVisualLayer,
  ResolvedVisualNovelScene,
  VisualAssetRef,
  VisualBackground,
  VisualExpression,
  VisualLayerExpressionKey,
  VisualPose,
  VisualStateMetadata
} from '$lib/types/visualNovel';

type AliasMap<T extends string> = Record<string, T>;

const EXPRESSION_ALIASES: AliasMap<VisualExpression> = {
  calm: 'neutral',
  content: 'happy',
  joy: 'happy',
  joyful: 'happy',
  smile: 'happy',
  playful: 'flirty',
  shy: 'flirty',
  thoughtful: 'thinking',
  focused: 'thinking',
  worried: 'concerned',
  anxious: 'concerned',
  startled: 'surprised',
  upset: 'sad'
};

const POSE_ALIASES: AliasMap<VisualPose> = {
  default: 'idle',
  still: 'idle',
  attentive: 'listening',
  talk: 'speaking',
  talking: 'speaking',
  close: 'leaning',
  lean: 'leaning',
  closer: 'leaning'
};

const BACKGROUND_ALIASES: AliasMap<VisualBackground> = {
  room: 'default',
  home: 'default',
  neutral: 'default',
  evening: 'night'
};

const URL_WITH_SCHEME_PATTERN = /^[a-z][a-z0-9+.-]*:/i;
const SPRITE_FALLBACK_TONE = '#f09a9f';
const BACKGROUND_FALLBACK_TONE = '#1b1723';

/**
 * Small resolver for chat-provided visual_state metadata.
 * It normalizes names, resolves layered character assets when available, keeps
 * legacy single-sprite fallback support, and never does additional inference work.
 */
export class ExpressionManager {
  normalizeState(manifest: CharacterVisualManifest, metadata?: VisualStateMetadata | NormalizedVisualState | null): NormalizedVisualState {
    return {
      characterId: metadata?.characterId?.trim() || manifest.id,
      expression: pickKnown(metadata?.expression, manifest.defaults.expression, manifest.expressions, EXPRESSION_ALIASES),
      pose: pickKnown(metadata?.pose, manifest.defaults.pose, manifest.poses, POSE_ALIASES),
      background: pickKnown(metadata?.background, manifest.defaults.background, manifest.backgrounds, BACKGROUND_ALIASES)
    };
  }

  resolveScene(
    manifest: CharacterVisualManifest,
    metadata?: VisualStateMetadata | NormalizedVisualState | null,
    failedAssetUrls: ReadonlySet<string> = new Set()
  ): ResolvedVisualNovelScene {
    const state = this.normalizeState(manifest, metadata);
    const sprite = resolveFirstUsableAsset(
      [
        manifest.sprites[state.pose]?.[state.expression],
        manifest.sprites[state.pose]?.[manifest.defaults.expression],
        manifest.sprites[manifest.defaults.pose]?.[state.expression],
        manifest.sprites[manifest.defaults.pose]?.[manifest.defaults.expression]
      ],
      manifest,
      failedAssetUrls,
      {
        kind: 'placeholder',
        alt: `${manifest.characterName} neutral idle placeholder`,
        dominantColor: SPRITE_FALLBACK_TONE
      }
    );
    const background = resolveFirstUsableAsset(
      [manifest.backgrounds[state.background], manifest.backgrounds[manifest.defaults.background]],
      manifest,
      failedAssetUrls,
      {
        kind: 'placeholder',
        alt: 'Warm default visual novel background',
        dominantColor: BACKGROUND_FALLBACK_TONE
      }
    );
    const characterLayers = resolveCharacterLayers(manifest, state, failedAssetUrls, sprite.asset);

    return {
      manifest,
      state,
      sprite: sprite.asset,
      characterLayers: characterLayers.layers,
      background: background.asset,
      expressionLabel: manifest.expressions[state.expression]?.label ?? manifest.expressions[manifest.defaults.expression].label,
      poseLabel: manifest.poses[state.pose]?.label ?? manifest.poses[manifest.defaults.pose].label,
      usedFallback: sprite.usedFallback || background.usedFallback || characterLayers.usedFallback
    };
  }
}

const normalizeKey = (value?: string | null): string | undefined => {
  const normalized = value?.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  return normalized || undefined;
};

const pickKnown = <T extends string>(value: string | undefined, fallback: T, known: Record<T, unknown>, aliases: AliasMap<T>): T => {
  const key = normalizeKey(value);
  if (!key) return fallback;
  return key in known ? (key as T) : aliases[key] ?? fallback;
};

const resolveFirstUsableAsset = (
  candidates: Array<VisualAssetRef | undefined>,
  manifest: CharacterVisualManifest,
  failedAssetUrls: ReadonlySet<string>,
  fallback: VisualAssetRef
): { asset: VisualAssetRef; usedFallback: boolean } => {
  const resolvedCandidates = candidates.map((asset) => normalizeAsset(asset, manifest));
  const firstCandidate = resolvedCandidates.find(Boolean);
  const asset = resolvedCandidates.find((candidate) => candidate && isUsableAsset(candidate, failedAssetUrls)) ?? fallback;

  return {
    asset,
    usedFallback: !firstCandidate || asset !== firstCandidate
  };
};

const resolveCharacterLayers = (
  manifest: CharacterVisualManifest,
  state: NormalizedVisualState,
  failedAssetUrls: ReadonlySet<string>,
  fallbackSprite: VisualAssetRef
): { layers: ResolvedVisualLayer[]; usedFallback: boolean } => {
  if (!manifest.layers?.length) {
    return {
      layers: [
        {
          id: 'legacy-sprite',
          slot: 'base',
          label: 'Full sprite',
          order: 0,
          asset: fallbackSprite,
          usedFallback: fallbackSprite.kind === 'placeholder'
        }
      ],
      usedFallback: fallbackSprite.kind === 'placeholder'
    };
  }

  const resolvedLayers = manifest.layers
    .map((layer, index) => resolveLayer(layer, index, manifest, state, failedAssetUrls, fallbackSprite))
    .filter((layer): layer is ResolvedVisualLayer => Boolean(layer))
    .sort((left, right) => left.order - right.order);

  if (resolvedLayers.length > 0) {
    return {
      layers: resolvedLayers,
      usedFallback: resolvedLayers.some((layer) => layer.usedFallback)
    };
  }

  return {
    layers: [
      {
        id: 'legacy-sprite',
        slot: 'base',
        label: 'Full sprite',
        order: 0,
        asset: fallbackSprite,
        usedFallback: true
      }
    ],
    usedFallback: true
  };
};

const resolveLayer = (
  layer: CharacterVisualLayerDefinition,
  index: number,
  manifest: CharacterVisualManifest,
  state: NormalizedVisualState,
  failedAssetUrls: ReadonlySet<string>,
  fallbackSprite: VisualAssetRef
): ResolvedVisualLayer | null => {
  const candidates = resolveLayerCandidates(layer, state, manifest.defaults.pose, manifest.defaults.expression);
  const fallback = layer.required ? fallbackSprite : undefined;
  const resolved = resolveFirstUsableLayerAsset(candidates, manifest, failedAssetUrls, fallback);

  if (!resolved) return null;

  return {
    id: layer.id,
    slot: layer.slot,
    label: layer.label,
    order: layer.order ?? index,
    asset: resolved.asset,
    usedFallback: resolved.usedFallback
  };
};

const resolveLayerCandidates = (
  layer: CharacterVisualLayerDefinition,
  state: NormalizedVisualState,
  defaultPose: VisualPose,
  defaultExpression: VisualExpression
): Array<VisualAssetRef | undefined> => {
  const expressionKeys: VisualLayerExpressionKey[] = [state.expression, 'default', defaultExpression];
  return [state.pose, defaultPose].flatMap((pose) => expressionKeys.map((expression) => layer.assets[pose]?.[expression]));
};

const resolveFirstUsableLayerAsset = (
  candidates: Array<VisualAssetRef | undefined>,
  manifest: CharacterVisualManifest,
  failedAssetUrls: ReadonlySet<string>,
  fallback?: VisualAssetRef
): { asset: VisualAssetRef; usedFallback: boolean } | null => {
  const resolvedCandidates = candidates.map((asset) => normalizeAsset(asset, manifest));
  const firstCandidate = resolvedCandidates.find(Boolean);
  const asset = resolvedCandidates.find((candidate) => candidate && isUsableAsset(candidate, failedAssetUrls));

  if (asset) {
    return { asset, usedFallback: asset !== firstCandidate };
  }

  if (!fallback) return null;
  return { asset: fallback, usedFallback: true };
};

const isUsableAsset = (asset: VisualAssetRef, failedAssetUrls: ReadonlySet<string>): boolean => !asset.src || !failedAssetUrls.has(asset.src);

const normalizeAsset = (asset: VisualAssetRef | undefined, manifest: CharacterVisualManifest): VisualAssetRef | undefined => {
  if (!asset?.src) return asset;

  return {
    ...asset,
    src: resolveAssetPath(asset.src, manifest.assetBasePath)
  };
};

const resolveAssetPath = (src: string, assetBasePath?: string): string => {
  const trimmedSrc = src.trim();
  if (!assetBasePath || !trimmedSrc || trimmedSrc.startsWith('/') || URL_WITH_SCHEME_PATTERN.test(trimmedSrc)) {
    return trimmedSrc;
  }

  return `${assetBasePath.replace(/\/+$/, '')}/${trimmedSrc.replace(/^\.\//, '').replace(/^\/+/, '')}`;
};

export const expressionManager = new ExpressionManager();
