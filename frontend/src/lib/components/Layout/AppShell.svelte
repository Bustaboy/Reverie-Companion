<script lang="ts">
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';
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

  const WELCOME_DISMISSED_KEY = 'reverie.milestone3Welcome.dismissed.v1';

  const enabledSectionIds = navigationItems.filter((item) => item.enabled).map((item) => item.id);
  const sectionFromHash = (): NavigationItemId => {
    if (!browser) return 'chat';
    const candidate = window.location.hash.replace(/^#\/?/, '') as NavigationItemId;
    return enabledSectionIds.includes(candidate) ? candidate : 'chat';
  };

  let activeSection: NavigationItemId = $state(sectionFromHash());
  let showWelcome = $state(false);

  onMount(() => {
    showWelcome = !window.localStorage.getItem(WELCOME_DISMISSED_KEY);
  });

  const dismissWelcome = () => {
    showWelcome = false;
    if (browser) window.localStorage.setItem(WELCOME_DISMISSED_KEY, 'true');
  };

  const openSectionFromWelcome = (section: NavigationItemId) => {
    dismissWelcome();
    navigate(section);
  };

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
    {#if showWelcome}
      <section class="milestone-welcome" aria-labelledby="milestone-welcome-title" aria-live="polite">
        <div>
          <p class="eyebrow">Milestone 3 complete</p>
          <h2 id="milestone-welcome-title">Reverie now has an immersion stack.</h2>
          <p>Try Visual Novel expressions, emotional voice, local scene images, Growth visibility, and the searchable Settings Hub. Heavy media stays queued behind 8GB guardrails so chat remains the heart of the experience.</p>
        </div>
        <div class="milestone-welcome-actions">
          <button type="button" onclick={() => openSectionFromWelcome('settings')}>What’s new</button>
          <button type="button" onclick={() => openSectionFromWelcome('visual-novel')}>Open VN mode</button>
          <button type="button" class="ghost" aria-label="Dismiss Milestone 3 welcome" onclick={dismissWelcome}>Dismiss</button>
        </div>
      </section>
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
