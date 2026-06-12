<script lang="ts">
  import { ChatWindow } from '$lib/components/Chat';
  import { JournalPanel } from '$lib/components/Journal';
  import { PersonalLoRAPanel } from '$lib/components/Growth';
  import { SettingsPanel } from '$lib/components/Settings';
  import { VisualNovelPanel } from '$lib/components/VisualNovel';
  import { visualNovelStore } from '$lib/stores/visualNovelStore';
  import type { NavigationItemId } from '$lib/config/navigation';
  import Sidebar from './Sidebar.svelte';

  let activeSection = $state<NavigationItemId>('chat');

  const navigate = (section: NavigationItemId) => {
    activeSection = section;
    visualNovelStore.setEnabled(section === 'visual-novel');
  };

  const isVisualNovelImmersive = $derived(activeSection === 'visual-novel' && $visualNovelStore.immersive);
</script>

<div class:vn-immersive={isVisualNovelImmersive} class="app-shell">
  {#if !isVisualNovelImmersive}
    <Sidebar activeSection={activeSection} onNavigate={navigate} />
  {/if}
  <main class="main-panel">
    {#if activeSection === 'journal'}
      <JournalPanel />
    {:else if activeSection === 'training'}
      <PersonalLoRAPanel />
    {:else if activeSection === 'settings'}
      <SettingsPanel />
    {:else if activeSection === 'visual-novel'}
      <VisualNovelPanel />
    {:else}
      <ChatWindow />
    {/if}
  </main>
</div>
