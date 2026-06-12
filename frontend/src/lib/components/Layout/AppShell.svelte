<script lang="ts">
  import { AudioPlayer } from '$lib/components/Audio';
  import { ChatWindow } from '$lib/components/Chat';
  import { JournalPanel } from '$lib/components/Journal';
  import { PersonalLoRAPanel } from '$lib/components/Growth';
  import { SettingsPanel } from '$lib/components/Settings';
  import { VisualNovelStage } from '$lib/components/VisualNovel';
  import { visualNovelStore } from '$lib/stores/visualNovelStore';
  import type { NavigationItemId } from '$lib/config/navigation';
  import Sidebar from './Sidebar.svelte';

  let activeSection: NavigationItemId = $state('chat');

  const navigate = (section: NavigationItemId) => {
    activeSection = section;

    if (section !== 'visual-novel' && $visualNovelStore.fullImmersive) {
      visualNovelStore.setFullImmersive(false);
    }
  };

  const returnToChat = () => navigate('chat');
</script>

<div class:immersive-shell={activeSection === 'visual-novel' && $visualNovelStore.fullImmersive} class="app-shell">
  {#if !(activeSection === 'visual-novel' && $visualNovelStore.fullImmersive)}
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
      <VisualNovelStage onReturnToChat={returnToChat} />
    {:else}
      <ChatWindow />
    {/if}
  </main>
  <AudioPlayer />
</div>
