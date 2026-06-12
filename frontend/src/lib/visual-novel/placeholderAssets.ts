import type { VisualAssetRef, VisualExpression, VisualPose } from '$lib/types/visualNovel';

interface SvgPlaceholderOptions {
  alt: string;
  label: string;
  kind: 'sprite' | 'background' | 'base' | 'expression' | 'clothing';
  primary?: string;
  secondary?: string;
  expression?: VisualExpression;
  pose?: VisualPose;
}

const encodeSvg = (svg: string): string => `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;

const commonDefs = (primary = '#f09a9f', secondary = '#7a4a84'): string => `
  <defs>
    <radialGradient id="a" cx="50%" cy="20%" r="55%">
      <stop offset="0%" stop-color="#fff1ef" stop-opacity="0.42"/>
      <stop offset="48%" stop-color="${primary}" stop-opacity="0.72"/>
      <stop offset="100%" stop-color="${secondary}" stop-opacity="0.9"/>
    </radialGradient>
    <linearGradient id="b" x1="15%" y1="0%" x2="85%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="#100d14" stop-opacity="0.08"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="28" stdDeviation="34" flood-color="#000000" flood-opacity="0.35"/>
    </filter>
  </defs>`;

const poseTransform = (pose?: VisualPose): string => {
  if (pose === 'leaning') return 'translate(0 -28) scale(1.04)';
  if (pose === 'speaking') return 'translate(0 -8)';
  if (pose === 'listening') return 'rotate(-1 360 500)';
  return '';
};

const expressionMouth = (expression?: VisualExpression): string => {
  if (expression === 'sad' || expression === 'concerned') {
    return '<path d="M319 405c28-22 54-22 82 0" fill="none" stroke="#fff2ef" stroke-width="10" stroke-linecap="round" opacity="0.78"/>';
  }
  if (expression === 'surprised') {
    return '<ellipse cx="360" cy="393" rx="21" ry="27" fill="#fff2ef" opacity="0.74"/>';
  }
  if (expression === 'thinking') {
    return '<path d="M330 398c22 11 43 11 65 0" fill="none" stroke="#fff2ef" stroke-width="9" stroke-linecap="round" opacity="0.68"/>';
  }
  return '<path d="M319 393c28 25 54 25 82 0" fill="none" stroke="#fff2ef" stroke-width="10" stroke-linecap="round" opacity="0.78"/>';
};

const expressionEyes = (expression?: VisualExpression): string => {
  if (expression === 'happy' || expression === 'flirty') {
    return '<path d="M302 334c14-12 28-12 42 0" fill="none" stroke="#2a1f2e" stroke-width="9" stroke-linecap="round" opacity="0.74"/><path d="M392 334c14-12 28-12 42 0" fill="none" stroke="#2a1f2e" stroke-width="9" stroke-linecap="round" opacity="0.74"/>';
  }
  return '<circle cx="315" cy="334" r="12" fill="#2a1f2e" opacity="0.74"/><circle cx="405" cy="334" r="12" fill="#2a1f2e" opacity="0.74"/>';
};

const baseLayerSvg = ({ label, primary = '#f09a9f', secondary = '#7a4a84', pose }: SvgPlaceholderOptions): string => `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 1000" role="img" aria-label="${label}">
  ${commonDefs(primary, secondary)}
  <rect width="720" height="1000" fill="none"/>
  <g filter="url(#shadow)" transform="${poseTransform(pose)}">
    <path d="M360 86c150 0 238 106 238 253v420c0 86-70 156-156 156H278c-86 0-156-70-156-156V339C122 192 210 86 360 86Z" fill="url(#a)"/>
    <path d="M210 350c28-112 91-169 150-169s122 57 150 169c-40-38-90-57-150-57s-110 19-150 57Z" fill="#fff8f7" opacity="0.2"/>
    <circle cx="360" cy="344" r="122" fill="url(#b)" stroke="#ffffff" stroke-opacity="0.16" stroke-width="3"/>
  </g>
</svg>`;

const expressionLayerSvg = ({ label, expression }: SvgPlaceholderOptions): string => `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 1000" role="img" aria-label="${label}">
  <rect width="720" height="1000" fill="none"/>
  <g>
    ${expressionEyes(expression)}
    ${expressionMouth(expression)}
    ${expression === 'flirty' ? '<path d="M438 304c28-18 48-7 55 18" fill="none" stroke="#ffe5e0" stroke-width="8" stroke-linecap="round" opacity="0.72"/>' : ''}
  </g>
</svg>`;

const clothingLayerSvg = ({ label, pose }: SvgPlaceholderOptions): string => `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 1000" role="img" aria-label="${label}">
  <rect width="720" height="1000" fill="none"/>
  <g transform="${poseTransform(pose)}">
    <path d="M228 548c70 48 194 48 264 0l56 264c-24 63-79 103-148 103h-80c-69 0-124-40-148-103l56-264Z" fill="#2b2032" opacity="0.58"/>
    <path d="M255 585c52 25 158 25 210 0" fill="none" stroke="#ffd8d4" stroke-width="12" stroke-linecap="round" opacity="0.26"/>
  </g>
</svg>`;

const spriteSvg = (options: SvgPlaceholderOptions): string => `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 1000" role="img" aria-label="${options.label}">
  ${commonDefs(options.primary, options.secondary)}
  <rect width="720" height="1000" fill="none"/>
  <g filter="url(#shadow)" transform="${poseTransform(options.pose)}">
    <path d="M360 86c150 0 238 106 238 253v420c0 86-70 156-156 156H278c-86 0-156-70-156-156V339C122 192 210 86 360 86Z" fill="url(#a)"/>
    <path d="M210 350c28-112 91-169 150-169s122 57 150 169c-40-38-90-57-150-57s-110 19-150 57Z" fill="#fff8f7" opacity="0.2"/>
    <circle cx="360" cy="344" r="122" fill="url(#b)" stroke="#ffffff" stroke-opacity="0.16" stroke-width="3"/>
    ${expressionEyes(options.expression)}
    ${expressionMouth(options.expression)}
    <text x="360" y="620" text-anchor="middle" fill="#fff1ef" font-family="Inter, system-ui, sans-serif" font-size="72" font-weight="800">R</text>
  </g>
</svg>`;

const backgroundSvg = ({ label, primary = '#211826', secondary = '#100d14' }: SvgPlaceholderOptions): string => `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000" role="img" aria-label="${label}">
  <defs>
    <radialGradient id="warm" cx="20%" cy="18%" r="60%">
      <stop offset="0%" stop-color="#f09a9f" stop-opacity="0.35"/>
      <stop offset="52%" stop-color="${primary}" stop-opacity="0.24"/>
      <stop offset="100%" stop-color="${secondary}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="violet" cx="82%" cy="12%" r="62%">
      <stop offset="0%" stop-color="#7a4a84" stop-opacity="0.36"/>
      <stop offset="100%" stop-color="${secondary}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="floor" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="${primary}"/>
      <stop offset="100%" stop-color="${secondary}"/>
    </linearGradient>
  </defs>
  <rect width="1600" height="1000" fill="url(#floor)"/>
  <rect width="1600" height="1000" fill="url(#warm)"/>
  <rect width="1600" height="1000" fill="url(#violet)"/>
  <path d="M0 710c230-58 454-80 672-66 278 17 547 6 928-74v430H0Z" fill="#ffffff" opacity="0.045"/>
  <path d="M150 210h330v380H150z" rx="38" fill="#ffffff" opacity="0.045" stroke="#ffffff" stroke-opacity="0.06"/>
  <path d="M1080 180h270v430h-270z" rx="42" fill="#ffffff" opacity="0.036" stroke="#ffffff" stroke-opacity="0.055"/>
</svg>`;

export const createSvgPlaceholderAsset = (options: SvgPlaceholderOptions): VisualAssetRef => {
  const svg =
    options.kind === 'sprite'
      ? spriteSvg(options)
      : options.kind === 'background'
        ? backgroundSvg(options)
        : options.kind === 'base'
          ? baseLayerSvg(options)
          : options.kind === 'expression'
            ? expressionLayerSvg(options)
            : clothingLayerSvg(options);

  return {
    kind: 'image',
    src: encodeSvg(svg),
    alt: options.alt,
    dominantColor: options.primary
  };
};
