<script lang="ts">
  import { ChatWindow } from '$lib/components/Chat';
  import { JournalPanel } from '$lib/components/Journal';
  import { CharacterEncyclopedia } from '$lib/components/Encyclopedia';
  import { GrowthDashboard, PersonalLoRAPanel } from '$lib/components/Growth';
  import { ImageGallery } from '$lib/components/ImageGeneration';
  import { MemoryBrowser } from '$lib/components/Memory';
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
    {#if activeSection === 'growth'}
      <GrowthDashboard />
    {:else if activeSection === 'journal'}
      <JournalPanel />
    {:else if activeSection === 'training'}
      <PersonalLoRAPanel />
    {:else if activeSection === 'memory'}
      <MemoryBrowser />
    {:else if activeSection === 'encyclopedia'}
      <CharacterEncyclopedia />
    {:else if activeSection === 'settings'}
      <SettingsPanel />
    {:else if activeSection === 'visual-novel'}
      <VisualNovelStage onReturnToChat={returnToChat} />
    {:else if activeSection === 'images'}
      <ImageGallery />
    {:else}
      <ChatWindow />
    {/if}
  </main>
</div>
