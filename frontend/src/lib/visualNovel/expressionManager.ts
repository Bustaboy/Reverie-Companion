import type { GrowthVisualModifier, VisualExpression, VisualPose, VisualState } from '$lib/types/visualNovel';

export const GROWTH_MODIFIER_DURATION_MS = 45_000;

export const DEFAULT_VISUAL_STATE: VisualState = {
  characterId: 'reverie',
  emotion: 'neutral',
  expression: 'neutral',
  pose: 'idle',
  background: 'default',
  intensity: 0.15,
  confidence: 0.25,
  sources: ['fallback_neutral']
};

export class ExpressionManager {
  normalizeVisualState(visualState: VisualState | undefined): VisualState {
    if (!visualState) {
      return DEFAULT_VISUAL_STATE;
    }

    return {
      ...DEFAULT_VISUAL_STATE,
      ...visualState,
      sources: visualState.sources.length ? visualState.sources.slice(0, 8) : DEFAULT_VISUAL_STATE.sources
    };
  }

  createGrowthModifier(visualState: VisualState, now = Date.now()): GrowthVisualModifier | null {
    if (!visualState.growthCue) {
      return null;
    }

    return {
      cue: visualState.growthCue,
      confidenceBoost: 0.1,
      poseShift: this.poseShiftForGrowth(visualState.expression),
      expiresAt: now + GROWTH_MODIFIER_DURATION_MS
    };
  }

  applyGrowthModifier(visualState: VisualState, modifier: GrowthVisualModifier | null): VisualState {
    if (!modifier) {
      return this.withoutTemporaryGrowth(visualState);
    }

    return {
      ...visualState,
      pose: modifier.poseShift,
      confidence: this.clamp01(visualState.confidence + modifier.confidenceBoost),
      sources: this.withSource(visualState.sources, 'temporary_growth_modifier')
    };
  }

  withoutTemporaryGrowth(visualState: VisualState): VisualState {
    return {
      ...visualState,
      growthCue: undefined,
      pose: visualState.pose ?? this.poseForExpression(visualState.expression),
      sources: visualState.sources.filter((source) => source !== 'temporary_growth_modifier')
    };
  }

  poseForExpression(expression: VisualExpression): VisualPose {
    const poses: Record<VisualExpression, VisualPose> = {
      neutral: 'idle',
      happy: 'leaning',
      tender: 'close',
      teasing: 'leaning',
      shy: 'guarded',
      embarrassed: 'guarded',
      confident: 'assertive',
      dominant: 'assertive',
      aroused: 'close',
      angry: 'guarded',
      sad: 'guarded',
      surprised: 'close'
    };
    return poses[expression];
  }

  private poseShiftForGrowth(expression: VisualExpression): VisualPose {
    if (expression === 'confident' || expression === 'dominant') {
      return 'assertive';
    }
    if (expression === 'tender' || expression === 'teasing' || expression === 'aroused') {
      return 'leaning';
    }
    return this.poseForExpression(expression);
  }

  private withSource(sources: string[], source: string): string[] {
    return sources.includes(source) ? sources : [...sources, source].slice(0, 8);
  }

  private clamp01(value: number): number {
    return Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0));
  }
}

export const expressionManager = new ExpressionManager();
