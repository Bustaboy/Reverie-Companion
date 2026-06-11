export const VISUAL_EXPRESSIONS = [
  'neutral',
  'happy',
  'tender',
  'teasing',
  'shy',
  'embarrassed',
  'confident',
  'dominant',
  'aroused',
  'angry',
  'sad',
  'surprised'
] as const;

export const VISUAL_POSES = ['idle', 'close', 'leaning', 'guarded', 'assertive'] as const;

export type VisualExpression = (typeof VISUAL_EXPRESSIONS)[number];
export type VisualPose = (typeof VISUAL_POSES)[number];
export type VisualAssetLayer = 'base' | 'expression' | 'clothing' | string;

export interface SpriteSheetFrame {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface SpriteSheetAsset {
  type: 'spritesheet';
  src: string;
  frame: SpriteSheetFrame;
  label?: string;
}

export type VisualAssetRef = string | SpriteSheetAsset;

export interface CharacterVisualManifest {
  characterId: string;
  defaultBackground: VisualAssetRef;
  fallbackExpression: VisualExpression;
  expressions: Partial<Record<VisualExpression, VisualAssetRef>>;
  poses: Partial<Record<VisualPose, VisualAssetRef>>;
  backgrounds?: Record<string, VisualAssetRef>;
  layerAssets?: Partial<Record<VisualAssetLayer, VisualAssetRef>>;
  layers: VisualAssetLayer[];
}

export interface VisualState {
  characterId: string;
  emotion: VisualExpression;
  expression: VisualExpression;
  pose: VisualPose;
  background: string;
  intensity: number;
  confidence: number;
  sources: string[];
  growthCue?: string;
}

export interface GrowthVisualModifier {
  cue: string;
  confidenceBoost: number;
  poseShift: VisualPose;
  expiresAt: number;
}

export interface ResolvedVisualAsset {
  kind: 'image' | 'spritesheet' | 'placeholder';
  slot: string;
  label: string;
  src?: string;
  frame?: SpriteSheetFrame;
  fallbackUsed: boolean;
}

export interface ResolvedCharacterLayer {
  layer: VisualAssetLayer;
  asset: ResolvedVisualAsset;
}

export interface ResolvedVisualScene {
  background: ResolvedVisualAsset;
  pose: ResolvedVisualAsset;
  expression: ResolvedVisualAsset;
  characterLayers: ResolvedCharacterLayer[];
}

export interface SceneMediaCapabilities {
  available: boolean;
  modes: Array<'image' | 'video'>;
  resourcePresets: Array<'preview_8gb' | 'balanced_8gb' | 'quality_manual' | 'video_experimental'>;
  message?: string;
}
