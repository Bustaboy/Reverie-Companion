export type NavigationItemId = 'chat' | 'growth' | 'journal' | 'training' | 'characters' | 'memory' | 'visual-novel' | 'images' | 'settings';

export interface NavigationItem {
  id: NavigationItemId;
  label: string;
  hint: string;
  enabled: boolean;
}

// Sidebar destinations are intentionally declared outside the component so future routes,
// panels, and feature flags can be added without touching layout markup.
export const navigationItems: NavigationItem[] = [
  { id: 'chat', label: 'Chat', hint: 'Current session', enabled: true },
  { id: 'growth', label: 'Growth', hint: 'Living bond', enabled: true },
  { id: 'journal', label: 'Journal', hint: 'Private reflections', enabled: true },
  { id: 'training', label: 'Training', hint: 'Personal LoRA review', enabled: true },
  { id: 'characters', label: 'Characters', hint: 'Coming soon', enabled: false },
  { id: 'memory', label: 'Memory', hint: 'Long-term recall', enabled: false },
  { id: 'visual-novel', label: 'Visual Novel', hint: 'Immersive scene', enabled: true },
  { id: 'images', label: 'Images', hint: 'Gallery & controls', enabled: true },
  { id: 'settings', label: 'Settings', hint: 'Memory controls', enabled: true }
];
