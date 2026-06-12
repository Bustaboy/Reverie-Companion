import type {
  CharacterVisualManifest,
  NormalizedVisualState,
  ResolvedVisualNovelScene,
  VisualAssetRef,
  VisualBackground,
  VisualExpression,
  VisualPose,
  VisualStateMetadata
} from '$lib/types/visualNovel';

const EXPRESSION_ALIASES: Record<string, VisualExpression> = {
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

const POSE_ALIASES: Record<string, VisualPose> = {
  default: 'idle',
  still: 'idle',
  attentive: 'listening',
  talk: 'speaking',
  talking: 'speaking',
  close: 'leaning',
  lean: 'leaning',
  closer: 'leaning'
};

const BACKGROUND_ALIASES: Record<string, VisualBackground> = {
  room: 'default',
  home: 'default',
  neutral: 'default',
  evening: 'night'
};

const URL_WITH_SCHEME_PATTERN = /^[a-z][a-z0-9+.-]*:/i;

/**
 * Small resolver for model-provided visual_state metadata.
 * It keeps Task 1A intentionally simple: normalize names, resolve one image per
 * pose/expression slot, and fall back safely without inference or layering.
 */
export class ExpressionManager {
  normalizeState(manifest: CharacterVisualManifest, metadata?: VisualStateMetadata | null): NormalizedVisualState {
    return {
      characterId: metadata?.characterId?.trim() || manifest.id,
      expression: pickKnown(metadata?.expression, manifest.defaults.expression, manifest.expressions, EXPRESSION_ALIASES),
      pose: pickKnown(metadata?.pose, manifest.defaults.pose, manifest.poses, POSE_ALIASES),
      background: pickKnown(metadata?.background, manifest.defaults.background, manifest.backgrounds, BACKGROUND_ALIASES),
      confidence: clampConfidence(metadata?.confidence),
      emotion: pickKnown(metadata?.emotion ?? metadata?.expression, manifest.defaults.expression, manifest.expressions, EXPRESSION_ALIASES),
      growthCue: metadata?.growthCue?.trim() || undefined,
      memoryRecallUsed: metadata?.memoryRecallUsed === true,
      reflectionThemes: Array.isArray(metadata?.reflectionThemes)
        ? metadata.reflectionThemes.filter((theme): theme is string => typeof theme === 'string').slice(0, 4)
        : []
    };
  }

  resolveScene(
    manifest: CharacterVisualManifest,
    metadata?: VisualStateMetadata | NormalizedVisualState | null,
    failedAssetUrls: ReadonlySet<string> = new Set()
  ): ResolvedVisualNovelScene {
    const state = this.normalizeState(manifest, metadata);
    const sprite = firstUsableAsset(
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
        dominantColor: '#f09a9f'
      }
    );
    const background = firstUsableAsset(
      [manifest.backgrounds[state.background], manifest.backgrounds[manifest.defaults.background]],
      manifest,
      failedAssetUrls,
      {
        kind: 'placeholder',
        alt: 'Warm default visual novel background',
        dominantColor: '#1b1723'
      }
    );

    return {
      manifest,
      state,
      sprite: sprite.asset,
      background: background.asset,
      expressionLabel: manifest.expressions[state.expression]?.label ?? manifest.expressions[manifest.defaults.expression].label,
      poseLabel: manifest.poses[state.pose]?.label ?? manifest.poses[manifest.defaults.pose].label,
      usedFallback: sprite.usedFallback || background.usedFallback
    };
  }
}

const normalizeKey = (value?: string): string | undefined => {
  const normalized = value?.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  return normalized || undefined;
};

const pickKnown = <T extends string>(
  value: string | undefined,
  fallback: T,
  known: Record<T, unknown>,
  aliases: Record<string, T>
): T => {
  const key = normalizeKey(value);
  if (!key) return fallback;
  return key in known ? (key as T) : aliases[key] ?? fallback;
};

const firstUsableAsset = (
  candidates: Array<VisualAssetRef | undefined>,
  manifest: CharacterVisualManifest,
  failedAssetUrls: ReadonlySet<string>,
  hardFallback: VisualAssetRef
): { asset: VisualAssetRef; usedFallback: boolean } => {
  const normalizedCandidates = candidates.map((asset) => normalizeAsset(asset, manifest));
  const firstCandidate = normalizedCandidates.find(Boolean);
  const usableCandidate = normalizedCandidates.find((asset) => asset && (!asset.src || !failedAssetUrls.has(asset.src)));

  return {
    asset: usableCandidate ?? hardFallback,
    usedFallback: usableCandidate !== firstCandidate || !firstCandidate
  };
};

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

const clampConfidence = (value?: number): number => {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
};
