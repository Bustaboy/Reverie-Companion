<script lang="ts">
  import { ChatWindow } from '$lib/components/Chat';
  import { JournalPanel } from '$lib/components/Journal';
  import { PersonalLoRAPanel } from '$lib/components/Growth';
  import { SettingsPanel } from '$lib/components/Settings';
  import type { NavigationItemId } from '$lib/config/navigation';
  import Sidebar from './Sidebar.svelte';

  let activeSection: NavigationItemId = $state('chat');

  const navigate = (section: NavigationItemId) => {
    activeSection = section;
  };
</script>

<div class="app-shell">
  <Sidebar activeSection={activeSection} onNavigate={navigate} />
  <main class="main-panel">
    {#if activeSection === 'journal'}
      <JournalPanel />
    {:else if activeSection === 'training'}
      <PersonalLoRAPanel />
    {:else if activeSection === 'settings'}
      <SettingsPanel />
    {:else}
      <ChatWindow />
    {/if}
  </main>
</div>
