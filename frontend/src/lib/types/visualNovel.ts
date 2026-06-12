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
  /** Temporary growth/reactivity cue emitted only on final SSE done events. */
  growthCue?: string;
  /** 0-1 visual modifier intensity for subtle pose/expression emphasis. */
  intensity?: number;
  /** 0-1 backend heuristic confidence; low confidence should already be neutral. */
  confidence?: number;
  /** Suggested temporary modifier lifetime; clamped by the Svelte store to 30-60s. */
  decayMs?: number;
}

export interface VisualGrowthModifier {
  cue: string;
  intensity: number;
  startedAt: number;
  expiresAt: number;
  decayMs: number;
}

export interface NormalizedVisualState {
  characterId: string;
  expression: VisualExpression;
  pose: VisualPose;
  background: VisualBackground;
}

export interface ResolvedVisualNovelScene {
  manifest: CharacterVisualManifest;
  state: NormalizedVisualState;
  sprite: VisualAssetRef;
  background: VisualAssetRef;
  expressionLabel: string;
  poseLabel: string;
  usedFallback: boolean;
}
