<script lang="ts">
  import { settingsStore, type ContextBudgetPreset, type ReflectionFrequency, type ReflectionSensitivity } from '$lib/stores/settingsStore';

  type Choice<T extends string> = {
    value: T;
    label: string;
    description: string;
  };

  const frequencyOptions: Choice<ReflectionFrequency>[] = [
    {
      value: 'low',
      label: 'Low',
      description: 'Reflects only after clear milestones or longer sessions.'
    },
    {
      value: 'balanced',
      label: 'Balanced',
      description: 'A gentle default for steady growth without background noise.'
    },
    {
      value: 'high',
      label: 'High',
      description: 'Checks in more often after emotionally meaningful moments.'
    }
  ];

  const sensitivityOptions: Choice<ReflectionSensitivity>[] = [
    {
      value: 'conservative',
      label: 'Conservative',
      description: 'Only saves lessons when the evidence is very clear.'
    },
    {
      value: 'balanced',
      label: 'Balanced',
      description: 'Notices repeated cues while avoiding fragile assumptions.'
    },
    {
      value: 'responsive',
      label: 'Responsive',
      description: 'Lets Reverie adapt sooner, while still keeping reflections reviewable.'
    }
  ];

  const contextBudgetOptions: Choice<ContextBudgetPreset>[] = [
    {
      value: 'lean',
      label: 'Lean',
      description: 'Best for 8GB systems when you want the quietest background footprint.'
    },
    {
      value: 'balanced',
      label: 'Balanced',
      description: 'Recommended: warm continuity with comfortable 8GB awareness.'
    },
    {
      value: 'deep',
      label: 'Deep recall',
      description: 'Keeps a little more room for relevant memory when conversations get layered.'
    }
  ];

  let savedMessage = $state('Saved locally');
  let savedMessageTimer: ReturnType<typeof setTimeout> | null = null;

  const markSaved = () => {
    savedMessage = 'Saved locally just now';
    if (savedMessageTimer) clearTimeout(savedMessageTimer);
    savedMessageTimer = setTimeout(() => {
      savedMessage = 'Saved locally';
    }, 1800);
  };

  const setMemoryEnabled = (event: Event) => {
    settingsStore.setLongTermMemoryEnabled((event.currentTarget as HTMLInputElement).checked);
    markSaved();
  };

  const setReflectionEnabled = (event: Event) => {
    settingsStore.setSelfReflectionEnabled((event.currentTarget as HTMLInputElement).checked);
    markSaved();
  };

  const setGrowthNotificationsEnabled = (event: Event) => {
    settingsStore.setGrowthNotificationsEnabled((event.currentTarget as HTMLInputElement).checked);
    markSaved();
  };

  const setFrequency = (frequency: ReflectionFrequency) => {
    settingsStore.setReflectionFrequency(frequency);
    markSaved();
  };

  const setSensitivity = (sensitivity: ReflectionSensitivity) => {
    settingsStore.setReflectionSensitivity(sensitivity);
    markSaved();
  };

  const setContextBudgetPreset = (preset: ContextBudgetPreset) => {
    settingsStore.setContextBudgetPreset(preset);
    markSaved();
  };

  const resetSettings = () => {
    settingsStore.resetMemoryReflectionSettings();
    markSaved();
  };
</script>

<section class="settings-panel" aria-labelledby="settings-title">
  <header class="settings-hero">
    <div>
      <p class="eyebrow">Settings</p>
      <h1 id="settings-title">Memory & Reflection</h1>
      <p class="subtitle">
        Choose how Reverie remembers, reflects, and gently tells you when something meaningful has changed.
      </p>
    </div>
    <div class="settings-save-state" role="status" aria-live="polite">
      <span aria-hidden="true"></span>
      {savedMessage}
    </div>
  </header>

  <div class="settings-content">
    <section class="settings-card settings-intro" aria-label="Local-first reassurance">
      <span class="settings-orb" aria-hidden="true">✦</span>
      <div>
        <h2>You stay in control</h2>
        <p>
          These preferences are saved on this device. They are intentionally simple for now: clear switches, calm defaults,
          and no hidden growth behavior beyond what you allow.
        </p>
      </div>
    </section>

    <div class="settings-grid">
      <article class="settings-card setting-row">
        <div>
          <h2>Long-term memory</h2>
          <p>
            Lets Reverie keep important preferences, promises, boundaries, and relationship moments for future conversations.
          </p>
        </div>
        <label class="switch-control">
          <input
            type="checkbox"
            checked={$settingsStore.longTermMemoryEnabled}
            aria-label="Enable long-term memory"
            onchange={setMemoryEnabled}
          />
          <span></span>
        </label>
      </article>

      <article class="settings-card setting-row">
        <div>
          <h2>Self-reflection</h2>
          <p>
            Allows Reverie to write private, reviewable reflections after meaningful moments so growth has evidence and context.
          </p>
        </div>
        <label class="switch-control">
          <input
            type="checkbox"
            checked={$settingsStore.selfReflectionEnabled}
            aria-label="Enable self-reflection"
            onchange={setReflectionEnabled}
          />
          <span></span>
        </label>
      </article>

      <article class="settings-card setting-group">
        <div>
          <h2>Reflection frequency</h2>
          <p>How often Reverie pauses to make sense of meaningful conversations.</p>
        </div>
        <div class="segmented-options" role="group" aria-label="Reflection frequency">
          {#each frequencyOptions as option}
            <button
              type="button"
              class:active={$settingsStore.reflectionFrequency === option.value}
              aria-pressed={$settingsStore.reflectionFrequency === option.value}
              onclick={() => setFrequency(option.value)}
            >
              <strong>{option.label}</strong>
              <span>{option.description}</span>
            </button>
          {/each}
        </div>
      </article>

      <article class="settings-card setting-group">
        <div>
          <h2>Reflection sensitivity</h2>
          <p>How cautious Reverie should be before treating a moment as a lasting lesson.</p>
        </div>
        <div class="segmented-options" role="group" aria-label="Reflection sensitivity">
          {#each sensitivityOptions as option}
            <button
              type="button"
              class:active={$settingsStore.reflectionSensitivity === option.value}
              aria-pressed={$settingsStore.reflectionSensitivity === option.value}
              onclick={() => setSensitivity(option.value)}
            >
              <strong>{option.label}</strong>
              <span>{option.description}</span>
            </button>
          {/each}
        </div>
      </article>

      <article class="settings-card setting-row">
        <div>
          <h2>Growth notifications</h2>
          <p>
            Shows soft in-chat notes when Reverie recognizes a meaningful shift, lesson, or repair worth surfacing.
          </p>
        </div>
        <label class="switch-control">
          <input
            type="checkbox"
            checked={$settingsStore.growthNotificationsEnabled}
            aria-label="Enable growth notifications"
            onchange={setGrowthNotificationsEnabled}
          />
          <span></span>
        </label>
      </article>

      <article class="settings-card setting-group">
        <div>
          <h2>Context budget</h2>
          <p>A simple 8GB-aware preset for how much room memory and reflection should ask for in conversation context.</p>
        </div>
        <div class="segmented-options compact" role="group" aria-label="Context budget preset">
          {#each contextBudgetOptions as option}
            <button
              type="button"
              class:active={$settingsStore.contextBudgetPreset === option.value}
              aria-pressed={$settingsStore.contextBudgetPreset === option.value}
              onclick={() => setContextBudgetPreset(option.value)}
            >
              <strong>{option.label}</strong>
              <span>{option.description}</span>
            </button>
          {/each}
        </div>
      </article>
    </div>

    <footer class="settings-footer-note">
      <div>
        <strong>Warm defaults, reversible choices.</strong>
        <span>Advanced schedules and training controls will come later; this page keeps the first trust controls easy to understand.</span>
      </div>
      <button type="button" class="ghost-button" onclick={resetSettings}>Restore calm defaults</button>
    </footer>
  </div>
</section>
