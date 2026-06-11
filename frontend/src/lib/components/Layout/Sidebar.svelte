<script lang="ts">
  import { navigationItems, type NavigationItemId } from '$lib/config/navigation';

  interface Props {
    activeSection: NavigationItemId;
    onNavigate: (section: NavigationItemId) => void;
  }

  let { activeSection, onNavigate }: Props = $props();
</script>

<aside class="sidebar" aria-label="Reverie workspace navigation">
  <div class="brand">
    <div class="brand-mark">R</div>
    <div>
      <strong>Reverie</strong>
      <span>Offline companion</span>
    </div>
  </div>

  <nav class="nav-list" aria-label="Primary navigation">
    {#each navigationItems as item}
      <button
        class:active={item.id === activeSection}
        type="button"
        disabled={!item.enabled}
        aria-current={item.id === activeSection ? 'page' : undefined}
        onclick={() => item.enabled && onNavigate(item.id)}
      >
        <span>{item.label}</span>
        <small>{item.hint}</small>
      </button>
    {/each}
  </nav>

  <div class="sidebar-card">
    <p>Growth stays local</p>
    <span>Journal entries are private reflection artifacts you can inspect before memory or training review uses them.</span>
  </div>
</aside>
