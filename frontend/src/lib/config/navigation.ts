export interface NavigationItem {
  label: string;
  hint: string;
  active: boolean;
}

// Sidebar destinations are intentionally declared outside the component so future routes,
// panels, and feature flags can be added without touching layout markup.
export const navigationItems: NavigationItem[] = [
  { label: 'Chat', hint: 'Current session', active: true },
  { label: 'Characters', hint: 'Coming soon', active: false },
  { label: 'Memory', hint: 'Long-term recall', active: false },
  { label: 'Visual Novel', hint: 'Future mode', active: false },
  { label: 'Settings', hint: 'Privacy & models', active: false }
];
