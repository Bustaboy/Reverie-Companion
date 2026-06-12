export type VisualExpression =
  | 'neutral'
  | 'happy'
  | 'sad'
  | 'thinking'
  | 'flirty'
  | 'surprised'
  | 'concerned';

export type VisualPose = 'idle' | 'listening' | 'speaking' | 'leaning';

export type VisualBackground = 'default' | 'bedroom' | 'cafe' | 'night';

export type VisualAssetKind = 'image' | 'placeholder';

export interface VisualAssetRef {
  kind: VisualAssetKind;
  /** Lightweight local path or future Tauri asset URL. Undefined means render CSS fallback. */
  src?: string;
  alt: string;
  dominantColor?: string;
}

export interface CharacterVisualManifest {
  id: string;
  characterName: string;
  version: number;
  /** Optional base URL/path for relative sprite and background entries in imported manifests. */
  assetBasePath?: string;
  defaults: {
    expression: VisualExpression;
    pose: VisualPose;
    background: VisualBackground;
  };
  expressions: Record<VisualExpression, { label: string }>;
  poses: Record<VisualPose, { label: string }>;
  backgrounds: Record<VisualBackground, VisualAssetRef>;
  /** One full sprite image per pose/expression slot for the MVP; layering is intentionally out of scope. */
  sprites: Record<VisualPose, Partial<Record<VisualExpression, VisualAssetRef>>>;
}

export interface VisualStateMetadata {
  characterId?: string;
  expression?: string;
  pose?: string;
  background?: string;
  confidence?: number;
  emotion?: string;
  growthCue?: string;
  memoryRecallUsed?: boolean;
  reflectionThemes?: string[];
}

export interface NormalizedVisualState {
  characterId: string;
  expression: VisualExpression;
  pose: VisualPose;
  background: VisualBackground;
  confidence: number;
  emotion: VisualExpression;
  growthCue?: string;
  memoryRecallUsed: boolean;
  reflectionThemes: string[];
}

export interface GrowthVisualModifier {
  cue: string;
  startedAt: number;
  expiresAt: number;
  intensity: number;
}

export interface ResolvedVisualNovelScene {
  manifest: CharacterVisualManifest;
  state: NormalizedVisualState;
  sprite: VisualAssetRef;
  background: VisualAssetRef;
  expressionLabel: string;
  poseLabel: string;
  usedFallback: boolean;
  growthModifier?: GrowthVisualModifier;
}
