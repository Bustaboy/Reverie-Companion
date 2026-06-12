<script lang="ts">
  import { browser } from '$app/environment';
  import { ChatWindow } from '$lib/components/Chat';
  import { JournalPanel } from '$lib/components/Journal';
  import { CharacterEncyclopedia } from '$lib/components/Encyclopedia';
  import { GrowthDashboard, PersonalLoRAPanel } from '$lib/components/Growth';
  import { ImageGallery } from '$lib/components/ImageGeneration';
  import { MemoryBrowser } from '$lib/components/Memory';
  import { SettingsPanel } from '$lib/components/Settings';
  import { VisualNovelStage } from '$lib/components/VisualNovel';
  import { resourceStore } from '$lib/stores/resourceStore.svelte';
  import { visualNovelStore } from '$lib/stores/visualNovelStore';
  import { navigationItems, type NavigationItemId } from '$lib/config/navigation';
  import Sidebar from './Sidebar.svelte';

  const enabledSectionIds = navigationItems.filter((item) => item.enabled).map((item) => item.id);
  const sectionFromHash = (): NavigationItemId => {
    if (!browser) return 'chat';
    const candidate = window.location.hash.replace(/^#\/?/, '') as NavigationItemId;
    return enabledSectionIds.includes(candidate) ? candidate : 'chat';
  };

  let activeSection: NavigationItemId = $state(sectionFromHash());

  const navigate = (section: NavigationItemId) => {
    activeSection = section;
    if (browser) window.history.replaceState(null, '', `#${section}`);

    if (section !== 'visual-novel' && $visualNovelStore.fullImmersive) {
      visualNovelStore.setFullImmersive(false);
    }
  };

  const returnToChat = () => navigate('chat');
</script>

<a class="skip-link" href="#reverie-main">Skip to main experience</a>
<div class:immersive-shell={activeSection === 'visual-novel' && $visualNovelStore.fullImmersive} class="app-shell">
  {#if !(activeSection === 'visual-novel' && $visualNovelStore.fullImmersive)}
    <Sidebar activeSection={activeSection} onNavigate={navigate} />
  {/if}
  <main id="reverie-main" class="main-panel" tabindex="-1" aria-label="Reverie active workspace">
    {#if resourceStore.warningLabel}
      <aside class="resource-warning" aria-live="polite">
        <strong>8GB guardrail</strong>
        <span>{resourceStore.warningLabel}</span>
        <small>{resourceStore.compactLabel}</small>
      </aside>
    {/if}
    <svelte:boundary>
      {#if activeSection === 'growth'}
        <GrowthDashboard />
      {:else if activeSection === 'journal'}
        <JournalPanel />
      {:else if activeSection === 'training'}
        <PersonalLoRAPanel />
      {:else if activeSection === 'encyclopedia'}
        <CharacterEncyclopedia />
      {:else if activeSection === 'memory'}
        <MemoryBrowser />
      {:else if activeSection === 'settings'}
        <SettingsPanel />
      {:else if activeSection === 'visual-novel'}
        <VisualNovelStage onReturnToChat={returnToChat} />
      {:else if activeSection === 'images'}
        <ImageGallery />
      {:else}
        <ChatWindow />
      {/if}
      {#snippet failed(error, reset)}
        <section class="panel-error" role="alert">
          <p class="eyebrow">Graceful recovery</p>
          <h2>This panel hit a local UI error.</h2>
          <p>{error instanceof Error ? error.message : 'Reverie kept the app shell alive. Try reopening this panel or switching sections.'}</p>
          <button type="button" onclick={reset}>Reload panel</button>
        </section>
      {/snippet}
    </svelte:boundary>
  </main>
</div>
