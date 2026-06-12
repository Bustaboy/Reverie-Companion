import type { VisualAssetRef } from '$lib/types/visualNovel';

interface SvgPlaceholderOptions {
  alt: string;
  label: string;
  kind: 'sprite' | 'background';
  primary?: string;
  secondary?: string;
}

const encodeSvg = (svg: string): string => `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;

const spriteSvg = ({ label, primary = '#f09a9f', secondary = '#7a4a84' }: SvgPlaceholderOptions): string => `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 1000" role="img" aria-label="${label}">
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
  </defs>
  <rect width="720" height="1000" fill="none"/>
  <g filter="url(#shadow)">
    <path d="M360 86c150 0 238 106 238 253v420c0 86-70 156-156 156H278c-86 0-156-70-156-156V339C122 192 210 86 360 86Z" fill="url(#a)"/>
    <path d="M210 350c28-112 91-169 150-169s122 57 150 169c-40-38-90-57-150-57s-110 19-150 57Z" fill="#fff8f7" opacity="0.2"/>
    <circle cx="360" cy="344" r="122" fill="url(#b)" stroke="#ffffff" stroke-opacity="0.16" stroke-width="3"/>
    <circle cx="315" cy="334" r="12" fill="#2a1f2e" opacity="0.74"/>
    <circle cx="405" cy="334" r="12" fill="#2a1f2e" opacity="0.74"/>
    <path d="M319 393c28 25 54 25 82 0" fill="none" stroke="#fff2ef" stroke-width="10" stroke-linecap="round" opacity="0.78"/>
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

export const createSvgPlaceholderAsset = (options: SvgPlaceholderOptions): VisualAssetRef => ({
  kind: 'image',
  src: encodeSvg(options.kind === 'sprite' ? spriteSvg(options) : backgroundSvg(options)),
  alt: options.alt,
  dominantColor: options.primary
});
