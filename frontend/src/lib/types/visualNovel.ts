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
  /** X coordinate of the frame within a future sprite sheet, in pixels. */
  x: number;
  /** Y coordinate of the frame within a future sprite sheet, in pixels. */
  y: number;
  /** Frame width, in pixels. */
  width: number;
  /** Frame height, in pixels. */
  height: number;
  /** Full sprite sheet width, in pixels. */
  sheetWidth: number;
  /** Full sprite sheet height, in pixels. */
  sheetHeight: number;
}

export interface VisualAssetRef {
  kind: VisualAssetKind;
  /** Lightweight local path, data URL, or future Tauri asset URL. Undefined means render CSS fallback. */
  src?: string;
  alt: string;
  dominantColor?: string;
  /** Optional frame metadata so the same renderer can support future sprite sheets without a schema break. */
  frame?: VisualSpriteFrame;
}

export type VisualLayerSlot = 'base' | 'expression' | 'clothing' | 'accessory' | 'effect' | string;
export type VisualLayerExpressionKey = VisualExpression | 'default';

export interface CharacterVisualLayerDefinition {
  id: string;
  slot: VisualLayerSlot;
  label: string;
  /** Lower values render behind higher values. Defaults to manifest order. */
  order?: number;
  /** Required layers receive a safe placeholder/fallback if all authored assets are missing. */
  required?: boolean;
  assets: Partial<Record<VisualPose, Partial<Record<VisualLayerExpressionKey, VisualAssetRef>>>>;
}

export interface ResolvedVisualLayer {
  id: string;
  slot: VisualLayerSlot;
  label: string;
  order: number;
  asset: VisualAssetRef;
  usedFallback: boolean;
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
  /** Preferred layered character composition: base → expression → clothing/accessories/effects. */
  layers?: CharacterVisualLayerDefinition[];
  /** Legacy/full-body sprite fallback per pose/expression slot. */
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
  /** Legacy single-sprite fallback retained for imported MVP manifests without layers. */
  sprite: VisualAssetRef;
  /** Ordered resolved layer stack for compositing base → expression → clothing etc. */
  characterLayers: ResolvedVisualLayer[];
  background: VisualAssetRef;
  expressionLabel: string;
  poseLabel: string;
  usedFallback: boolean;
}
