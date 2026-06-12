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

export interface VisualSpriteFrame {
  /** Pixel X offset within a future sprite sheet. */
  x: number;
  /** Pixel Y offset within a future sprite sheet. */
  y: number;
  width: number;
  height: number;
}

export interface VisualAssetRef {
  kind: VisualAssetKind;
  /** Lightweight local path, data URL, or future Tauri asset URL. Undefined means render CSS fallback. */
  src?: string;
  alt: string;
  dominantColor?: string;
  /** Optional future sprite-sheet frame metadata; rendered as a cropped sheet cell when present. */
  frame?: VisualSpriteFrame;
}

export type VisualLayerName = 'base' | 'expression' | 'clothing' | 'hair' | 'accessory' | 'effect' | (string & {});

export interface VisualLayerAssetMap {
  /** Layer fallback for any pose/expression. */
  default?: VisualAssetRef;
  /** Pose-level fallback, useful for base bodies or pose-specific clothing. */
  byPose?: Partial<Record<VisualPose, VisualAssetRef>>;
  /** Expression-level fallback, useful for face overlays shared across poses. */
  byExpression?: Partial<Record<VisualExpression, VisualAssetRef>>;
  /** Most specific mapping for layer art. */
  byPoseExpression?: Partial<Record<VisualPose, Partial<Record<VisualExpression, VisualAssetRef>>>>;
}

export interface VisualLayerDefinition {
  label: string;
  /** Missing required layers trigger the full-sprite/CSS fallback; optional layers are skipped. */
  required?: boolean;
  zIndex?: number;
  opacity?: number;
  blendMode?: string;
  assets: VisualLayerAssetMap;
}

export interface ResolvedVisualLayer {
  name: VisualLayerName;
  label: string;
  asset: VisualAssetRef;
  zIndex: number;
  opacity: number;
  blendMode?: string;
  usedFallback: boolean;
}

export interface CharacterVisualManifest {
  id: string;
  characterName: string;
  version: number;
  /** Optional base URL/path for relative sprite, layer, and background entries in imported manifests. */
  assetBasePath?: string;
  defaults: {
    expression: VisualExpression;
    pose: VisualPose;
    background: VisualBackground;
  };
  expressions: Record<VisualExpression, { label: string }>;
  poses: Record<VisualPose, { label: string }>;
  backgrounds: Record<VisualBackground, VisualAssetRef>;
  /** Ordered compositing from back to front: base → expression → clothing → accessories/effects. */
  layerOrder?: VisualLayerName[];
  /** Layered sprite parts for the normal VN renderer. Optional to preserve old full-sprite manifests. */
  layers?: Partial<Record<VisualLayerName, VisualLayerDefinition>>;
  /** Full sprite fallback for legacy imports or when a required layer is missing/failed. */
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
  layers: ResolvedVisualLayer[];
  background: VisualAssetRef;
  expressionLabel: string;
  poseLabel: string;
  usedFallback: boolean;
  compositionMode: 'layers' | 'sprite';
}
