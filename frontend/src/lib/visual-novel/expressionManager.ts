import type { VisualStateMetadata } from '$lib/types/visualNovel';

const EXPRESSION_ALIASES: Record<string, string> = {
  joy: 'happy',
  pleased: 'happy',
  smile: 'happy',
  flirty: 'teasing',
  playful: 'teasing',
  calm: 'neutral',
  default: 'neutral',
  contemplative: 'thinking'
};

const POSE_ALIASES: Record<string, string> = {
  default: 'idle',
  calm: 'idle',
  talk: 'speaking',
  talking: 'speaking',
  thoughtful: 'thinking'
};

/** Normalizes backend visual_state hints without inferring emotions or adding growth logic. */
export class ExpressionManager {
  normalizeVisualState(input: unknown, source: VisualStateMetadata['source'] = 'chat'): VisualStateMetadata | undefined {
    if (!this.isRecord(input)) {
      return undefined;
    }

    const expression = this.normalizeKey(input.expression ?? input.emotion ?? input.mood, EXPRESSION_ALIASES);
    const pose = this.normalizeKey(input.pose ?? input.stance, POSE_ALIASES);
    const background = this.normalizeKey(input.background ?? input.scene ?? input.location);
    const characterId = this.normalizePlain(input.character_id ?? input.characterId);

    if (!expression && !pose && !background && !characterId) {
      return undefined;
    }

    return {
      characterId,
      expression,
      pose,
      background,
      updatedAt: new Date(),
      source
    };
  }

  private normalizeKey(value: unknown, aliases: Record<string, string> = {}): string | undefined {
    if (typeof value !== 'string') return undefined;
    const normalized = value.trim().toLowerCase();
    if (!normalized) return undefined;
    return aliases[normalized] ?? normalized;
  }

  private normalizePlain(value: unknown): string | undefined {
    return typeof value === 'string' && value.trim() ? value.trim() : undefined;
  }

  private isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
  }
}

export const expressionManager = new ExpressionManager();
