import type {
  CharacterVisualManifest,
  NormalizedVisualState,
  ResolvedVisualLayer,
  ResolvedVisualNovelScene,
  VisualAssetRef,
  VisualBackground,
  VisualExpression,
  VisualLayerDefinition,
  VisualLayerName,
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

const DEFAULT_LAYER_ORDER: VisualLayerName[] = ['base', 'expression', 'clothing', 'hair', 'accessory', 'effect'];
const URL_WITH_SCHEME_PATTERN = /^[a-z][a-z0-9+.-]*:/i;
const SPRITE_FALLBACK_TONE = '#f09a9f';
const BACKGROUND_FALLBACK_TONE = '#1b1723';
const FALLBACK_SPRITE_ASSET: VisualAssetRef = {
  kind: 'placeholder',
  alt: 'Neutral idle placeholder',
  dominantColor: SPRITE_FALLBACK_TONE
};

/**
 * Small resolver for chat-provided visual_state metadata.
 * It normalizes names, composes bounded manifest layers, supports sprite-sheet
 * frame metadata, and falls back safely without inference or heavyweight work.
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
    const layers = resolveVisualLayers(manifest, state, failedAssetUrls);
    const requiredLayerFailed = layers.some((layer) => layer.usedFallback && manifest.layers?.[layer.name]?.required);
    const shouldUseLayers = layers.length > 0 && !requiredLayerFailed;
    const sprite = resolveFullSprite(manifest, state, failedAssetUrls);
    const background = resolveFirstUsableAsset(
      [manifest.backgrounds[state.background], manifest.backgrounds[manifest.defaults.background]],
      manifest,
      failedAssetUrls,
      {
        kind: 'placeholder',
        alt: 'Warm default visual novel background',
        dominantColor: BACKGROUND_FALLBACK_TONE
      }
    ) as { asset: VisualAssetRef; usedFallback: boolean };

    return {
      manifest,
      state,
      sprite: sprite.asset,
      layers: shouldUseLayers ? layers : [],
      background: background.asset,
      expressionLabel: manifest.expressions[state.expression]?.label ?? manifest.expressions[manifest.defaults.expression].label,
      poseLabel: manifest.poses[state.pose]?.label ?? manifest.poses[manifest.defaults.pose].label,
      usedFallback: sprite.usedFallback || background.usedFallback || requiredLayerFailed || layers.some((layer) => layer.usedFallback),
      compositionMode: shouldUseLayers ? 'layers' : 'sprite'
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

const resolveVisualLayers = (
  manifest: CharacterVisualManifest,
  state: NormalizedVisualState,
  failedAssetUrls: ReadonlySet<string>
): ResolvedVisualLayer[] => {
  if (!manifest.layers) return [];

  const orderedNames = createLayerOrder(manifest);
  return orderedNames.flatMap((name, index) => {
    const definition = manifest.layers?.[name];
    if (!definition) return [];

    const resolved = resolveLayerAsset(definition, manifest, state, failedAssetUrls);
    if (!resolved && !definition.required) return [];

    return [
      {
        name,
        label: definition.label,
        asset: resolved?.asset ?? { ...FALLBACK_SPRITE_ASSET, alt: `${manifest.characterName} ${definition.label} fallback` },
        zIndex: definition.zIndex ?? index,
        opacity: definition.opacity ?? 1,
        blendMode: definition.blendMode,
        usedFallback: resolved?.usedFallback ?? true
      }
    ];
  });
};

const createLayerOrder = (manifest: CharacterVisualManifest): VisualLayerName[] => {
  const configuredOrder = manifest.layerOrder ?? DEFAULT_LAYER_ORDER;
  const configured = new Set(configuredOrder);
  const remaining = Object.keys(manifest.layers ?? {}).filter((name) => !configured.has(name));
  return [...configuredOrder, ...remaining];
};

const resolveLayerAsset = (
  definition: VisualLayerDefinition,
  manifest: CharacterVisualManifest,
  state: NormalizedVisualState,
  failedAssetUrls: ReadonlySet<string>
): { asset: VisualAssetRef; usedFallback: boolean } | null => {
  const candidates = [
    definition.assets.byPoseExpression?.[state.pose]?.[state.expression],
    definition.assets.byPoseExpression?.[state.pose]?.[manifest.defaults.expression],
    definition.assets.byPoseExpression?.[manifest.defaults.pose]?.[state.expression],
    definition.assets.byPose?.[state.pose],
    definition.assets.byExpression?.[state.expression],
    definition.assets.byPose?.[manifest.defaults.pose],
    definition.assets.byExpression?.[manifest.defaults.expression],
    definition.assets.default
  ];

  const resolved = resolveFirstUsableAsset(candidates, manifest, failedAssetUrls, undefined);
  return resolved.asset ? (resolved as { asset: VisualAssetRef; usedFallback: boolean }) : null;
};

const resolveFullSprite = (
  manifest: CharacterVisualManifest,
  state: NormalizedVisualState,
  failedAssetUrls: ReadonlySet<string>
): { asset: VisualAssetRef; usedFallback: boolean } =>
  resolveFirstUsableAsset(
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
  ) as { asset: VisualAssetRef; usedFallback: boolean };

const resolveFirstUsableAsset = (
  candidates: Array<VisualAssetRef | undefined>,
  manifest: CharacterVisualManifest,
  failedAssetUrls: ReadonlySet<string>,
  fallback?: VisualAssetRef
): { asset?: VisualAssetRef; usedFallback: boolean } => {
  const resolvedCandidates = candidates.map((asset) => normalizeAsset(asset, manifest));
  const firstCandidate = resolvedCandidates.find(Boolean);
  const asset = resolvedCandidates.find((candidate) => candidate && isUsableAsset(candidate, failedAssetUrls)) ?? fallback;

  return {
    asset,
    usedFallback: !firstCandidate || asset !== firstCandidate
  };
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
