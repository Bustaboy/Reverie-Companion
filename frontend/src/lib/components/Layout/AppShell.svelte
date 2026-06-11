<script lang="ts">
  import { ChatWindow } from '$lib/components/Chat';
  import { JournalPanel } from '$lib/components/Journal';
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
    {:else}
      <ChatWindow />
    {/if}
  </main>
</div>
