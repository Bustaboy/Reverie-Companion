import type {
  CharacterVisualAssetSlot,
  CharacterVisualManifest,
  ResolvedVisualAsset,
  ResolvedVisualScene,
  VisualStateMetadata
} from '$lib/types/visualNovel';

const FALLBACK_CHARACTER_ID = 'reverie-default';
const FALLBACK_EXPRESSION = 'neutral';
const FALLBACK_POSE = 'idle';
const FALLBACK_BACKGROUND = 'default';
const MAX_ASSET_CACHE_SIZE = 6;

const svgDataUri = (label: string, from: string, to: string): string => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" role="img" aria-label="${label}"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="${from}"/><stop offset="1" stop-color="${to}"/></linearGradient><radialGradient id="r" cx="50%" cy="28%" r="52%"><stop stop-color="#ffffff" stop-opacity="0.18"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient></defs><rect width="1200" height="800" fill="url(#g)"/><rect width="1200" height="800" fill="url(#r)"/><circle cx="600" cy="355" r="132" fill="#f0a0a4" opacity="0.32"/><path d="M390 725c35-150 110-248 210-248s175 98 210 248" fill="#2a2033" opacity="0.78"/><path d="M488 340c20-73 61-113 112-113s92 40 112 113c-32 36-69 54-112 54s-80-18-112-54Z" fill="#ffd9d2" opacity="0.54"/><text x="600" y="715" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="34" fill="#f8edf5" opacity="0.82">${label}</text></svg>`;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
};

export const fallbackVisualManifest: CharacterVisualManifest = {
  schemaVersion: 1,
  characterId: FALLBACK_CHARACTER_ID,
  displayName: 'Reverie',
  defaults: {
    expression: FALLBACK_EXPRESSION,
    pose: FALLBACK_POSE,
    background: FALLBACK_BACKGROUND
  },
  expressions: [
    { id: FALLBACK_EXPRESSION, alt: 'Reverie with a calm neutral expression' },
    { id: 'happy', alt: 'Reverie with a warm happy expression' },
    { id: 'soft', alt: 'Reverie with a gentle soft expression' },
    { id: 'teasing', alt: 'Reverie with a playful teasing expression' }
  ],
  poses: [
    { id: FALLBACK_POSE, alt: 'Reverie resting in an idle pose' },
    { id: 'speaking', alt: 'Reverie leaning into the conversation' },
    { id: 'thinking', alt: 'Reverie pausing in a thoughtful pose' }
  ],
  backgrounds: [
    { id: FALLBACK_BACKGROUND, alt: 'A warm dark Reverie lounge background' },
    { id: 'night-room', alt: 'A quiet night room background' }
  ]
};

const placeholderBySlot = {
  expression: svgDataUri('Expression fallback', '#3b2634', '#7d4057'),
  pose: svgDataUri('Pose fallback', '#241b2f', '#5f3d70'),
  background: svgDataUri('Default background', '#100d14', '#34213f')
} as const;

/**
 * Resolves requested VN visual state against a manifest with bounded caching.
 * It never throws for missing character art: absent slots fall back to neutral,
 * idle, and the default background so chat/VN mode stay responsive on 8GB systems.
 */
export class CharacterVisualResolver {
  private readonly assetCache = new Map<string, ResolvedVisualAsset>();

  constructor(private manifest: CharacterVisualManifest = fallbackVisualManifest) {}

  setManifest(manifest: CharacterVisualManifest | null | undefined): void {
    this.manifest = manifest ?? fallbackVisualManifest;
    this.assetCache.clear();
  }

  resolveScene(metadata: VisualStateMetadata = {}): ResolvedVisualScene {
    const expression = this.normalizeSlot(metadata.expression, this.manifest.defaults?.expression, FALLBACK_EXPRESSION);
    const pose = this.normalizeSlot(metadata.pose, this.manifest.defaults?.pose, FALLBACK_POSE);
    const background = this.normalizeSlot(metadata.background, this.manifest.defaults?.background, FALLBACK_BACKGROUND);

    return {
      characterId: this.manifest.characterId || FALLBACK_CHARACTER_ID,
      displayName: this.manifest.displayName || 'Reverie',
      expression: this.resolveAsset('expression', this.manifest.expressions, expression, FALLBACK_EXPRESSION),
      pose: this.resolveAsset('pose', this.manifest.poses, pose, FALLBACK_POSE),
      background: this.resolveAsset('background', this.manifest.backgrounds, background, FALLBACK_BACKGROUND),
      requested: { expression, pose, background }
    };
  }

  resolveEmergencyFallback(slot: 'expression' | 'pose' | 'background', id?: string): ResolvedVisualAsset {
    const fallbackId = slot === 'expression' ? FALLBACK_EXPRESSION : slot === 'pose' ? FALLBACK_POSE : FALLBACK_BACKGROUND;
    return {
      id: id || fallbackId,
      src: placeholderBySlot[slot],
      alt: `Fallback ${slot} art`,
      isFallback: true
    };
  }

  private resolveAsset(
    slot: 'expression' | 'pose' | 'background',
    assets: CharacterVisualAssetSlot[],
    requestedId: string,
    fallbackId: string
  ): ResolvedVisualAsset {
    const cacheKey = `${this.manifest.characterId}:${slot}:${requestedId}`;
    const cached = this.assetCache.get(cacheKey);
    if (cached) return cached;

    const requested = assets.find((asset) => asset.id === requestedId);
    const fallback = assets.find((asset) => asset.id === fallbackId) ?? assets[0];
    const selected = requested ?? fallback;
    const isFallback = !requested || !selected?.src;
    const resolved = selected
      ? {
          id: selected.id,
          src: selected.src ? this.resolvePath(selected.src) : placeholderBySlot[slot],
          alt: selected.alt ?? `${this.manifest.displayName} ${slot} ${selected.id}`,
          isFallback
        }
      : this.resolveEmergencyFallback(slot, fallbackId);

    this.remember(cacheKey, resolved);
    return resolved;
  }

  private normalizeSlot(value: unknown, manifestDefault: unknown, fallback: string): string {
    for (const candidate of [value, manifestDefault, fallback]) {
      if (typeof candidate === 'string' && candidate.trim()) {
        return candidate.trim().toLowerCase();
      }
    }

    return fallback;
  }

  private resolvePath(src: string): string {
    if (/^(data:|blob:|https?:|\/)/.test(src)) {
      return src;
    }

    const basePath = this.manifest.basePath?.replace(/\/+$/, '');
    return basePath ? `${basePath}/${src.replace(/^\/+/, '')}` : src;
  }

  private remember(key: string, asset: ResolvedVisualAsset): void {
    if (this.assetCache.size >= MAX_ASSET_CACHE_SIZE) {
      const oldestKey = this.assetCache.keys().next().value;
      if (oldestKey) this.assetCache.delete(oldestKey);
    }

    this.assetCache.set(key, asset);
  }
}
