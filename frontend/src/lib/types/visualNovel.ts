/** Lightweight visual-state primitives accepted from chat metadata and VN UI controls. */
export type VisualExpression = 'neutral' | 'happy' | 'sad' | 'angry' | 'teasing' | 'surprised' | 'soft' | string;
export type VisualPose = 'idle' | 'speaking' | 'thinking' | 'leaning' | string;

export interface VisualStateMetadata {
  characterId?: string;
  expression?: VisualExpression;
  pose?: VisualPose;
  background?: string;
  updatedAt?: Date;
  source?: 'chat' | 'done' | 'manual' | 'fallback';
}

export interface CharacterVisualAssetSlot {
  /** Stable slot id, e.g. "neutral", "happy", "idle", or "bedroom". */
  id: string;
  /** Browser-loadable asset path. Local manifest paths are resolved relative to the manifest base path. */
  src?: string;
  /** Warm, accessible label used when an image cannot load. */
  alt?: string;
}

export interface CharacterVisualManifest {
  schemaVersion: 1;
  characterId: string;
  displayName: string;
  /** Optional path prefix for relative asset URLs in this manifest. */
  basePath?: string;
  defaults?: {
    expression?: VisualExpression;
    pose?: VisualPose;
    background?: string;
  };
  expressions: CharacterVisualAssetSlot[];
  poses: CharacterVisualAssetSlot[];
  backgrounds: CharacterVisualAssetSlot[];
}

export interface ResolvedVisualAsset {
  id: string;
  src: string;
  alt: string;
  isFallback: boolean;
}

export interface ResolvedVisualScene {
  characterId: string;
  displayName: string;
  expression: ResolvedVisualAsset;
  pose: ResolvedVisualAsset;
  background: ResolvedVisualAsset;
  requested: Required<Pick<VisualStateMetadata, 'expression' | 'pose' | 'background'>>;
}
