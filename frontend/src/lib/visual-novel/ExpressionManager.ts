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
  lean: 'leaning'
};

const BACKGROUND_ALIASES: Record<string, VisualBackground> = {
  room: 'default',
  home: 'default',
  neutral: 'default',
  evening: 'night'
};

/**
 * Resolves model-provided visual_state metadata into cheap, bounded VN assets.
 * Missing or failed paths always collapse back to neutral + idle + default rather
 * than forcing the UI to mount broken images or do expensive recovery work.
 */
export class ExpressionManager {
  normalizeState(manifest: CharacterVisualManifest, metadata?: VisualStateMetadata | null): NormalizedVisualState {
    return {
      characterId: metadata?.characterId || manifest.id,
      expression: this.normalizeExpression(manifest, metadata?.expression),
      pose: this.normalizePose(manifest, metadata?.pose),
      background: this.normalizeBackground(manifest, metadata?.background)
    };
  }

  resolveScene(
    manifest: CharacterVisualManifest,
    metadata?: VisualStateMetadata | NormalizedVisualState | null,
    failedAssetUrls: ReadonlySet<string> = new Set()
  ): ResolvedVisualNovelScene {
    const state = this.normalizeState(manifest, metadata);
    const sprite = this.resolveSprite(manifest, state, failedAssetUrls);
    const background = this.resolveBackground(manifest, state, failedAssetUrls);

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

  private normalizeExpression(manifest: CharacterVisualManifest, value?: string): VisualExpression {
    return this.pickKnown(value, manifest.defaults.expression, manifest.expressions, EXPRESSION_ALIASES);
  }

  private normalizePose(manifest: CharacterVisualManifest, value?: string): VisualPose {
    return this.pickKnown(value, manifest.defaults.pose, manifest.poses, POSE_ALIASES);
  }

  private normalizeBackground(manifest: CharacterVisualManifest, value?: string): VisualBackground {
    return this.pickKnown(value, manifest.defaults.background, manifest.backgrounds, BACKGROUND_ALIASES);
  }

  private pickKnown<T extends string>(value: string | undefined, fallback: T, known: Record<T, unknown>, aliases: Record<string, T>): T {
    const normalized = value?.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
    if (!normalized) return fallback;
    if (normalized in known) return normalized as T;
    return aliases[normalized] ?? fallback;
  }

  private resolveSprite(
    manifest: CharacterVisualManifest,
    state: NormalizedVisualState,
    failedAssetUrls: ReadonlySet<string>
  ): { asset: VisualAssetRef; usedFallback: boolean } {
    const candidates = [
      manifest.sprites[state.pose]?.[state.expression],
      manifest.sprites[state.pose]?.[manifest.defaults.expression],
      manifest.sprites[manifest.defaults.pose]?.[state.expression],
      manifest.sprites[manifest.defaults.pose]?.[manifest.defaults.expression]
    ];

    return this.firstUsableAsset(candidates, failedAssetUrls, {
      kind: 'placeholder',
      alt: `${manifest.characterName} neutral idle placeholder`,
      dominantColor: '#f09a9f'
    });
  }

  private resolveBackground(
    manifest: CharacterVisualManifest,
    state: NormalizedVisualState,
    failedAssetUrls: ReadonlySet<string>
  ): { asset: VisualAssetRef; usedFallback: boolean } {
    return this.firstUsableAsset(
      [manifest.backgrounds[state.background], manifest.backgrounds[manifest.defaults.background]],
      failedAssetUrls,
      {
        kind: 'placeholder',
        alt: 'Warm default visual novel background',
        dominantColor: '#1b1723'
      }
    );
  }

  private firstUsableAsset(
    candidates: Array<VisualAssetRef | undefined>,
    failedAssetUrls: ReadonlySet<string>,
    hardFallback: VisualAssetRef
  ): { asset: VisualAssetRef; usedFallback: boolean } {
    const firstCandidate = candidates.find(Boolean);
    const usableCandidate = candidates.find((asset) => asset && (!asset.src || !failedAssetUrls.has(asset.src)));
    return {
      asset: usableCandidate ?? hardFallback,
      usedFallback: usableCandidate !== firstCandidate || !firstCandidate
    };
  }
}

export const expressionManager = new ExpressionManager();
