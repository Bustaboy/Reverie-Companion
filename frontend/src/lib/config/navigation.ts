export type NavigationItemId = 'chat' | 'journal' | 'characters' | 'memory' | 'visual-novel' | 'settings';

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
  { id: 'journal', label: 'Journal', hint: 'Private reflections', enabled: true },
  { id: 'characters', label: 'Characters', hint: 'Coming soon', enabled: false },
  { id: 'memory', label: 'Memory', hint: 'Long-term recall', enabled: false },
  { id: 'visual-novel', label: 'Visual Novel', hint: 'Future mode', enabled: false },
  { id: 'settings', label: 'Settings', hint: 'Privacy & models', enabled: false }
];
