<script lang="ts">
  import { ChatWindow } from '$lib/components/Chat';
  import { JournalPanel } from '$lib/components/Journal';
  import type { WorkspaceSection } from '$lib/config/navigation';
  import { journalStore } from '$lib/stores/journalStore';
  import Sidebar from './Sidebar.svelte';

  let activeSection: WorkspaceSection = $state('chat');

  const navigate = (section: WorkspaceSection) => {
    activeSection = section;
    if (section === 'journal') {
      journalStore.open();
    }
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
