<script lang="ts">
  import { settingsStore, type ContextBudgetPreset, type ReflectionFrequency, type ReflectionSensitivity } from '$lib/stores/settingsStore';

  const reflectionFrequencyOptions: Array<{
    value: ReflectionFrequency;
    label: string;
    description: string;
  }> = [
    {
      value: 'low',
      label: 'Low',
      description: 'Reflect only after clear milestones or when you ask for it.'
    },
    {
      value: 'balanced',
      label: 'Balanced',
      description: 'Notice meaningful patterns without interrupting ordinary conversation.'
    },
    {
      value: 'high',
      label: 'High',
      description: 'Check in more often after emotional turns, repairs, or important promises.'
    }
  ];

  const reflectionSensitivityOptions: Array<{
    value: ReflectionSensitivity;
    label: string;
    description: string;
  }> = [
    {
      value: 'conservative',
      label: 'Conservative',
      description: 'Only keep what is explicit, repeated, or clearly important.'
    },
    {
      value: 'balanced',
      label: 'Balanced',
      description: 'A careful middle path for preferences, boundaries, and relationship moments.'
    },
    {
      value: 'responsive',
      label: 'Responsive',
      description: 'Let Reverie notice subtler shifts while still avoiding big assumptions.'
    }
  ];

  const contextBudgetOptions: Array<{
    value: ContextBudgetPreset;
    label: string;
    description: string;
    detail: string;
  }> = [
    {
      value: 'gentle',
      label: 'Gentle',
      description: 'Keeps recall lighter for busy laptops or battery moments.',
      detail: 'Smallest memory bundle'
    },
    {
      value: 'balanced',
      label: 'Balanced',
      description: 'Recommended for the 8GB target: warm continuity with calm resource use.',
      detail: '8GB-aware default'
    },
    {
      value: 'roomy',
      label: 'Roomy',
      description: 'Allows a little more remembered context when your system has headroom.',
      detail: 'More context when idle'
    }
  ];

  const savedLabel = $derived(
    $settingsStore.savedAt
      ? `Saved locally ${$settingsStore.savedAt.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`
      : 'Saved locally on this device'
  );

  const handleLongTermMemoryChange = (event: Event) => {
    settingsStore.setLongTermMemoryEnabled((event.currentTarget as HTMLInputElement).checked);
  };

  const handleSelfReflectionChange = (event: Event) => {
    settingsStore.setSelfReflectionEnabled((event.currentTarget as HTMLInputElement).checked);
  };

  const handleGrowthNotificationsChange = (event: Event) => {
    settingsStore.setGrowthNotificationsEnabled((event.currentTarget as HTMLInputElement).checked);
  };
</script>

<section class="settings-panel" aria-labelledby="settings-title">
  <header class="settings-hero">
    <div>
      <p class="eyebrow">Private local controls</p>
      <h1 id="settings-title">Memory & Reflection</h1>
      <p class="subtitle">
        Choose how much Reverie remembers, reflects, and gently shares signs of growth. These controls stay simple on purpose: clear enough to trust, calm enough to revisit anytime.
      </p>
    </div>
    <div class="settings-save-pill" aria-live="polite">
      <span aria-hidden="true">✓</span>
      {savedLabel}
    </div>
  </header>

  <div class="settings-content">
    <article class="settings-card settings-card-featured">
      <div class="setting-copy">
        <span class="setting-kicker">Memory</span>
        <h2>Long-term memory</h2>
        <p id="long-term-memory-description">
          Let Reverie keep important preferences, promises, and boundaries. Turning this off keeps the current chat intact while durable remembering pauses.
        </p>
      </div>
      <label class="toggle-switch">
        <input
          type="checkbox"
          checked={$settingsStore.longTermMemoryEnabled}
          onchange={handleLongTermMemoryChange}
          aria-describedby="long-term-memory-description"
        />
        <span>{ $settingsStore.longTermMemoryEnabled ? 'On' : 'Off' }</span>
      </label>
    </article>

    <article class="settings-card settings-card-featured">
      <div class="setting-copy">
        <span class="setting-kicker">Reflection</span>
        <h2>Self-reflection</h2>
        <p id="self-reflection-description">
          Allow private review after the conversation settles. Reflection is slower growth, not constant monitoring or rewriting from one fragile moment.
        </p>
      </div>
      <label class="toggle-switch">
        <input
          type="checkbox"
          checked={$settingsStore.selfReflectionEnabled}
          onchange={handleSelfReflectionChange}
          aria-describedby="self-reflection-description"
        />
        <span>{ $settingsStore.selfReflectionEnabled ? 'On' : 'Off' }</span>
      </label>
    </article>

    <article class="settings-card settings-wide">
      <div class="setting-copy compact">
        <span class="setting-kicker">Pace</span>
        <h2>Reflection frequency</h2>
        <p>Pick how often Reverie pauses later to understand what mattered.</p>
      </div>
      <div class="option-grid" role="radiogroup" aria-label="Reflection frequency">
        {#each reflectionFrequencyOptions as option}
          <button
            type="button"
            class:active={$settingsStore.reflectionFrequency === option.value}
            aria-pressed={$settingsStore.reflectionFrequency === option.value}
            onclick={() => settingsStore.setReflectionFrequency(option.value)}
          >
            <strong>{option.label}</strong>
            <span>{option.description}</span>
          </button>
        {/each}
      </div>
    </article>

    <article class="settings-card settings-wide">
      <div class="setting-copy compact">
        <span class="setting-kicker">Care</span>
        <h2>Reflection sensitivity</h2>
        <p>Choose how cautious Reverie should be before treating a moment as meaningful growth.</p>
      </div>
      <div class="option-grid" role="radiogroup" aria-label="Reflection sensitivity">
        {#each reflectionSensitivityOptions as option}
          <button
            type="button"
            class:active={$settingsStore.reflectionSensitivity === option.value}
            aria-pressed={$settingsStore.reflectionSensitivity === option.value}
            onclick={() => settingsStore.setReflectionSensitivity(option.value)}
          >
            <strong>{option.label}</strong>
            <span>{option.description}</span>
          </button>
        {/each}
      </div>
    </article>

    <article class="settings-card settings-wide">
      <div class="setting-copy compact">
        <span class="setting-kicker">Presence</span>
        <h2>Growth notifications</h2>
        <p>Show occasional notes when Reverie notices a meaningful shift—no dashboards, no pressure.</p>
      </div>
      <label class="inline-toggle">
        <input
          type="checkbox"
          checked={$settingsStore.growthNotificationsEnabled}
          onchange={handleGrowthNotificationsChange}
        />
        <span>{ $settingsStore.growthNotificationsEnabled ? 'Show gentle growth notes' : 'Keep growth quiet' }</span>
      </label>
    </article>

    <article class="settings-card settings-wide">
      <div class="setting-copy compact">
        <span class="setting-kicker">8GB awareness</span>
        <h2>Context budget</h2>
        <p>A simple preset for remembered context. Balanced is designed for smooth local use on the 8GB target.</p>
      </div>
      <div class="budget-grid" role="radiogroup" aria-label="Context budget preset">
        {#each contextBudgetOptions as option}
          <button
            type="button"
            class:active={$settingsStore.contextBudgetPreset === option.value}
            aria-pressed={$settingsStore.contextBudgetPreset === option.value}
            onclick={() => settingsStore.setContextBudgetPreset(option.value)}
          >
            <span>{option.detail}</span>
            <strong>{option.label}</strong>
            <small>{option.description}</small>
          </button>
        {/each}
      </div>
    </article>

    <aside class="settings-trust-note" aria-label="Memory and reflection trust note">
      <span aria-hidden="true">✦</span>
      <div>
        <strong>You stay in control.</strong>
        <p>
          These settings are saved in local storage for now and are shaped to match Reverie's transparent growth rules: remember explicit evidence, reflect outside the active response path, and keep future advanced schedules out of the MVP controls.
        </p>
      </div>
      <button type="button" onclick={() => settingsStore.resetMemoryReflectionSettings()}>Restore calm defaults</button>
    </aside>
  </div>
</section>
