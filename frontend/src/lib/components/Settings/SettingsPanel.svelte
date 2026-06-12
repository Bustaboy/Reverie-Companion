<script lang="ts">
  import { onMount } from 'svelte';
  import {
    settingsStore,
    type ContextBudgetPreset,
    type ReflectionFrequency,
    type ReflectionSensitivity,
    type TTSLatencyPreset,
    type ImageDefaultPreset,
    type PerformancePreset,
    type SettingsState,
    type ExtensionSettingValue
  } from '$lib/stores/settingsStore';
  import { voiceService, type VoiceProfile, type VoiceMoodSettings } from '$lib/api/voiceService';
  import { extensionService } from '$lib/api/extensionService';
  import { extensionRegistry, extensionSettingsSections } from '$lib/extensions/registry';
  import { extensionEventBus } from '$lib/extensions/extensionBus';
  import type { ExtensionSettingField } from '$lib/extensions/contracts';

  type HubSection = {
    id: string;
    label: string;
    eyebrow: string;
    title: string;
    summary: string;
    tags: string[];
  };

  const hubSections: HubSection[] = [
    {
      id: 'general',
      label: 'General',
      eyebrow: 'Local-first basics',
      title: 'General controls',
      summary: 'Everyday safety rails, saved-state clarity, and calm defaults for a private companion workspace.',
      tags: ['general', 'defaults', 'backup', 'local']
    },
    {
      id: 'appearance',
      label: 'Appearance',
      eyebrow: 'Warm premium dark',
      title: 'Appearance & preview',
      summary: 'Preview Reverie’s visual language without adding runtime animation or heavy effects.',
      tags: ['appearance', 'theme', 'density', 'preview']
    },
    {
      id: 'voice',
      label: 'TTS & Voice',
      eyebrow: 'Local voice',
      title: 'TTS & voice',
      summary: 'Keep speech expressive, interruptible, and aware of the 8GB target.',
      tags: ['tts', 'voice', 'mood', 'audio', 'orpheus']
    },
    {
      id: 'images',
      label: 'Images',
      eyebrow: 'Scene visualization',
      title: 'Image generation',
      summary: 'Choose safe local image defaults and understand when jobs queue or downgrade.',
      tags: ['image', 'generation', 'preset', 'comfyui', 'gallery']
    },
    {
      id: 'growth',
      label: 'Growth',
      eyebrow: 'Self-learning',
      title: 'Growth & self-learning',
      summary: 'Control reflection cadence, growth notices, and review-first learning behavior.',
      tags: ['growth', 'self-learning', 'reflection', 'journal', 'lora', 'training']
    },
    {
      id: 'memory',
      label: 'Memory',
      eyebrow: 'Remembering with consent',
      title: 'Memory',
      summary: 'Tune durable memory, context budget, and pruning expectations.',
      tags: ['memory', 'rag', 'context', 'pruning', 'recall']
    },
    {
      id: 'extensions',
      label: 'Extensibility',
      eyebrow: 'Extension contracts',
      title: 'Extensibility',
      summary: 'Let extensions register small typed settings while keeping failures isolated.',
      tags: ['extension', 'plugin', 'manifest', 'settings']
    },
    {
      id: 'performance',
      label: 'Performance & 8GB',
      eyebrow: 'RTX 4070 8GB guardrails',
      title: 'Performance & 8GB',
      summary: 'Make resource tradeoffs visible before a local model, voice, or image job competes for VRAM.',
      tags: ['performance', '8gb', 'vram', 'background', 'resource']
    },
    {
      id: 'data',
      label: 'Export / Import',
      eyebrow: 'Portable local data',
      title: 'Export, import, backup, and reset',
      summary: 'Move settings safely, capture a local backup, and reset with confirmation.',
      tags: ['export', 'import', 'backup', 'characters', 'growth', 'reset']
    }
  ];

  const reflectionFrequencyOptions: Array<{ value: ReflectionFrequency; label: string; description: string }> = [
    { value: 'low', label: 'Low', description: 'Reflect only after clear milestones or when you ask for it.' },
    { value: 'balanced', label: 'Balanced', description: 'Notice meaningful patterns without interrupting ordinary conversation.' },
    { value: 'high', label: 'High', description: 'Check in more often after emotional turns, repairs, or important promises.' }
  ];

  const reflectionSensitivityOptions: Array<{ value: ReflectionSensitivity; label: string; description: string }> = [
    { value: 'conservative', label: 'Conservative', description: 'Only keep what is explicit, repeated, or clearly important.' },
    { value: 'balanced', label: 'Balanced', description: 'A careful middle path for preferences, boundaries, and relationship moments.' },
    { value: 'responsive', label: 'Responsive', description: 'Notice subtler shifts while still avoiding big identity assumptions.' }
  ];

  const contextBudgetOptions: Array<{ value: ContextBudgetPreset; label: string; description: string; detail: string }> = [
    { value: 'gentle', label: 'Gentle', description: 'Smallest memory bundle for battery, heat, or active media jobs.', detail: 'Lowest VRAM/RAM pressure' },
    { value: 'balanced', label: 'Balanced', description: 'Recommended 8GB default: warm continuity with calm resource use.', detail: '8GB-aware default' },
    { value: 'roomy', label: 'Roomy', description: 'More remembered context when your machine has headroom.', detail: 'More context when idle' }
  ];

  const imagePresetOptions: Array<{ value: ImageDefaultPreset; label: string; description: string; preview: string; impact: string }> = [
    { value: 'preview_8gb', label: 'Preview', description: 'Fastest and safest default for 8GB laptops.', preview: '512–768px draft look', impact: 'Lowest VRAM; best while chatting or using voice.' },
    { value: 'balanced_8gb', label: 'Balanced', description: 'Higher detail when VRAM is available; falls back safely.', preview: '768px polished still', impact: 'Moderate VRAM; queued behind interactive work.' },
    { value: 'high_8gb', label: 'High', description: 'Best local detail, still serialized and 8GB-gated.', preview: 'High-detail pass', impact: 'Highest local cost; may downgrade near guardrails.' }
  ];

  const performancePresetOptions: Array<{ value: PerformancePreset; label: string; description: string; detail: string }> = [
    { value: '8gb_safe', label: '8GB Safe', description: 'Prioritizes TTS responsiveness, preview images, gentle context, and one background task.', detail: 'Best RTX 4070 laptop default' },
    { value: 'balanced', label: 'Balanced', description: 'Normal 8GB guardrails with richer context when the machine is idle.', detail: 'Recommended daily mode' },
    { value: 'quality', label: 'Quality', description: 'Opts up to roomier context and expressive media after headroom checks.', detail: 'Use plugged in with thermal headroom' }
  ];

  const ttsLatencyOptions: Array<{ value: TTSLatencyPreset; label: string; description: string }> = [
    { value: 'quality', label: 'Quality', description: 'Prefer Orpheus-style expressiveness when the machine has room.' },
    { value: 'balanced', label: 'Balanced', description: 'Recommended for 8GB: expressive enough without aggressive preloading.' },
    { value: 'speed', label: 'Speed', description: 'Favor quick fallback voices and interruption-friendly playback.' }
  ];

  let searchQuery = $state('');
  let activeSectionId = $state('general');
  let cloneName = $state('');
  let cloneFile = $state<File | null>(null);
  let cloneRecording = $state<Blob | null>(null);
  let cloneRecordingUrl = $state<string | null>(null);
  let isRecording = $state(false);
  let isCreatingVoice = $state(false);
  let cloneStatus = $state<string | null>(null);
  let cloneError = $state<string | null>(null);
  let clonedProfile = $state<VoiceProfile | null>(null);
  let mediaRecorder: MediaRecorder | null = null;
  let recordingStartedAt = 0;
  let recordingDurationSeconds = $state<number | null>(null);
  let voiceProfiles = $state<VoiceProfile[]>([]);
  let voicesLoading = $state(false);
  let voiceMoodStatus = $state<string | null>(null);
  let voiceMoodError = $state<string | null>(null);
  let savingMoodVoiceId = $state<string | null>(null);
  let extensionsLoading = $state(false);
  let extensionStatus = $state<string | null>(null);
  let extensionError = $state<string | null>(null);
  let dataStatus = $state<string | null>(null);
  let dataError = $state<string | null>(null);
  let resetConfirmation = $state('');
  let importInput = $state<HTMLInputElement | null>(null);

  const cloneAudio = $derived(cloneRecording ?? cloneFile);
  const savedLabel = $derived(
    $settingsStore.savedAt
      ? `Saved locally ${$settingsStore.savedAt.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`
      : 'Saved locally on this device'
  );
  const normalizedSearch = $derived(searchQuery.trim().toLowerCase());
  const visibleSections = $derived(
    normalizedSearch
      ? hubSections.filter((section) =>
          [section.label, section.eyebrow, section.title, section.summary, ...section.tags]
            .join(' ')
            .toLowerCase()
            .includes(normalizedSearch)
        )
      : hubSections
  );

  const defaultMoodSettings = (): VoiceMoodSettings => ({
    baseline_expressiveness: 1,
    emotional_sensitivity: 1,
    nsfw_intensity: 1
  });

  const moodFor = (profile: VoiceProfile): VoiceMoodSettings => profile.mood_settings ?? defaultMoodSettings();

  const sectionVisible = (sectionId: string) => visibleSections.some((section) => section.id === sectionId);

  const scrollToSection = (sectionId: string) => {
    activeSectionId = sectionId;
    document.getElementById(`settings-${sectionId}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const loadVoiceProfiles = async () => {
    voicesLoading = true;
    voiceMoodError = null;
    try {
      voiceProfiles = await voiceService.listVoices();
    } catch (error) {
      voiceMoodError = error instanceof Error ? error.message : 'Could not load local voice profiles.';
    } finally {
      voicesLoading = false;
    }
  };

  const loadExtensions = async () => {
    extensionsLoading = true;
    extensionError = null;
    try {
      const registry = await extensionService.listExtensions();
      extensionRegistry.setBackendExtensions(registry.extensions);
      extensionStatus = `${registry.extensions.length} extension contract${registry.extensions.length === 1 ? '' : 's'} loaded.`;
      extensionEventBus.publish('settings.extensions_loaded', 'settings', 'reverie.settings', {
        extension_count: registry.extensions.length
      });
    } catch (error) {
      extensionError = error instanceof Error ? error.message : 'Could not load backend extension contracts.';
      extensionRegistry.reportError(extensionError);
    } finally {
      extensionsLoading = false;
    }
  };

  const extensionSettingValue = (extensionId: string, field: ExtensionSettingField) => {
    const value = $settingsStore.extensionSettings[extensionId]?.[field.key];
    return value ?? field.default;
  };

  const setExtensionSetting = (extensionId: string, field: ExtensionSettingField, value: ExtensionSettingValue) => {
    settingsStore.setExtensionSetting(extensionId, field.key, value);
    extensionEventBus.publish('settings.extension_setting_changed', 'settings', extensionId, { key: field.key, value });
  };

  const handleExtensionInput = (extensionId: string, field: ExtensionSettingField, event: Event) => {
    const target = event.currentTarget as HTMLInputElement | HTMLSelectElement;
    if (field.kind === 'boolean') return setExtensionSetting(extensionId, field, (target as HTMLInputElement).checked);
    if (field.kind === 'number') return setExtensionSetting(extensionId, field, Number(target.value));
    setExtensionSetting(extensionId, field, target.value);
  };

  const handleImageDefaultPresetChange = (preset: ImageDefaultPreset) => settingsStore.setImageDefaultPreset(preset);
  const handleTTSVolumeChange = (event: Event) => settingsStore.setTTSVolume(Number((event.currentTarget as HTMLInputElement).value));
  const handleTTSSpeedChange = (event: Event) => settingsStore.setTTSSpeed(Number((event.currentTarget as HTMLInputElement).value));

  const handleCloneFileChange = (event: Event) => {
    const file = (event.currentTarget as HTMLInputElement).files?.[0] ?? null;
    cloneFile = file;
    cloneRecording = null;
    cloneError = null;
    cloneStatus = file ? `Selected ${file.name}.` : null;
    if (cloneRecordingUrl) URL.revokeObjectURL(cloneRecordingUrl);
    cloneRecordingUrl = file ? URL.createObjectURL(file) : null;
  };

  const startRecording = async () => {
    cloneError = null;
    cloneStatus = 'Listening for a 6-15 second reference…';
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: BlobPart[] = [];
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.push(event.data);
      };
      mediaRecorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunks, { type: mediaRecorder?.mimeType || 'audio/webm' });
        cloneRecording = blob;
        cloneFile = null;
        recordingDurationSeconds = (Date.now() - recordingStartedAt) / 1000;
        if (cloneRecordingUrl) URL.revokeObjectURL(cloneRecordingUrl);
        cloneRecordingUrl = URL.createObjectURL(blob);
        cloneStatus = `Recorded ${Math.round(recordingDurationSeconds)} seconds. Ready to create a profile.`;
        mediaRecorder = null;
      };
      recordingStartedAt = Date.now();
      mediaRecorder.start();
      isRecording = true;
    } catch (error) {
      cloneError = error instanceof Error ? error.message : 'Microphone recording is unavailable.';
      cloneStatus = null;
    }
  };

  const stopRecording = () => {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') return;
    isRecording = false;
    mediaRecorder.stop();
  };

  const updateMoodSetting = async (profile: VoiceProfile, key: keyof VoiceMoodSettings, value: number) => {
    const nextMood = { ...moodFor(profile), [key]: value };
    voiceProfiles = voiceProfiles.map((candidate) =>
      candidate.voice_id === profile.voice_id ? { ...candidate, mood_settings: nextMood } : candidate
    );
    savingMoodVoiceId = profile.voice_id;
    voiceMoodError = null;
    try {
      const updated = await voiceService.updateVoiceProfile(profile.voice_id, { mood_settings: nextMood });
      voiceProfiles = voiceProfiles.map((candidate) => (candidate.voice_id === updated.voice_id ? updated : candidate));
      voiceMoodStatus = `Saved mood controls for ${updated.name}.`;
    } catch (error) {
      voiceMoodError = error instanceof Error ? error.message : 'Could not save those mood controls.';
      void loadVoiceProfiles();
    } finally {
      savingMoodVoiceId = null;
    }
  };

  const createVoiceProfile = async () => {
    if (!cloneAudio || !cloneName.trim()) {
      cloneError = 'Add a profile name and a 6-15 second audio reference first.';
      return;
    }

    isCreatingVoice = true;
    cloneError = null;
    cloneStatus = 'Creating local Orpheus zero-shot voice profile…';
    try {
      clonedProfile = await voiceService.createVoiceProfile({
        name: cloneName.trim(),
        referenceAudio: cloneAudio,
        filename: cloneFile?.name ?? 'recorded-reference.webm',
        durationSeconds: recordingDurationSeconds ?? undefined
      });
      cloneStatus = `Created ${clonedProfile.name}. It will use Orpheus zero-shot cloning when speech is generated.`;
      voiceProfiles = [...voiceProfiles.filter((profile) => profile.voice_id !== clonedProfile?.voice_id), clonedProfile];
    } catch (error) {
      cloneError = error instanceof Error ? error.message : 'Could not create that voice profile.';
      cloneStatus = null;
    } finally {
      isCreatingVoice = false;
    }
  };

  const previewVoiceSample = () => {
    dataError = null;
    if (!('speechSynthesis' in window)) {
      dataError = 'This webview does not expose speech synthesis for quick previews.';
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance('A warm local preview. Reverie will keep voice responsive while protecting the 8 gigabyte budget.');
    utterance.volume = $settingsStore.ttsEnabled ? $settingsStore.ttsVolume : 0;
    utterance.rate = $settingsStore.ttsSpeed;
    window.speechSynthesis.speak(utterance);
  };

  const localStorageSnapshot = () => {
    if (typeof window === 'undefined') return {};
    const snapshot: Record<string, string> = {};
    for (let index = 0; index < window.localStorage.length; index += 1) {
      const key = window.localStorage.key(index);
      if (!key?.startsWith('reverie.')) continue;
      const value = window.localStorage.getItem(key);
      if (value !== null) snapshot[key] = value;
    }
    return snapshot;
  };

  const downloadJson = (filename: string, payload: Record<string, unknown>) => {
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const backupPayload = (kind: 'settings' | 'characters' | 'growth' | 'full') => ({
    schema_version: 'reverie.backup.v1',
    kind,
    exported_at: new Date().toISOString(),
    settings: settingsStore.getSnapshot(),
    app_local_data: localStorageSnapshot(),
    notes: {
      characters: 'Character exports are reserved for character-card data as soon as the character repository is connected to Settings.',
      growth: 'Growth exports preserve local settings now and can accept backend journal/training artifacts in the same backup envelope later.',
      privacy: 'This file may contain intimate local preferences. Store it somewhere private.'
    }
  });

  const exportBackup = (kind: 'settings' | 'characters' | 'growth' | 'full') => {
    dataError = null;
    dataStatus = `Exported ${kind} backup.`;
    downloadJson(`reverie-${kind}-backup-${new Date().toISOString().slice(0, 10)}.json`, backupPayload(kind));
  };

  const importSettingsFile = async (event: Event) => {
    const file = (event.currentTarget as HTMLInputElement).files?.[0];
    if (!file) return;
    dataError = null;
    try {
      const parsed = JSON.parse(await file.text()) as { settings?: Partial<SettingsState> } & Partial<SettingsState>;
      const candidate = parsed.settings && typeof parsed.settings === 'object' ? parsed.settings : parsed;
      settingsStore.importSettings(candidate);
      dataStatus = `Imported settings from ${file.name}. Review the hub before continuing.`;
    } catch (error) {
      dataError = error instanceof Error ? error.message : 'Could not import that settings file.';
    } finally {
      if (importInput) importInput.value = '';
    }
  };

  const resetToDefaults = () => {
    if (resetConfirmation.trim().toUpperCase() !== 'RESET') {
      dataError = 'Type RESET to confirm restoring defaults.';
      return;
    }
    settingsStore.resetAllSettings();
    resetConfirmation = '';
    dataError = null;
    dataStatus = 'Settings restored to safe local defaults.';
  };

  onMount(() => {
    void loadVoiceProfiles();
    void loadExtensions();
    return () => {
      if (cloneRecordingUrl) URL.revokeObjectURL(cloneRecordingUrl);
    };
  });
</script>

<section class="settings-panel settings-hub" aria-labelledby="settings-title">
  <header class="settings-hero settings-hub-hero">
    <div>
      <p class="eyebrow">Settings & Control Hub</p>
      <h1 id="settings-title">Reverie Control Hub</h1>
      <p class="subtitle">
        One warm, searchable place for memory, voice, images, growth, extensions, backups, and 8GB performance guardrails.
      </p>
    </div>
    <div class="settings-save-pill" aria-live="polite"><span aria-hidden="true">✓</span>{savedLabel}</div>
  </header>

  <div class="settings-hub-layout">
    <aside class="settings-hub-sidebar" aria-label="Settings navigation">
      <label class="settings-search">
        <span>Search settings</span>
        <input type="search" bind:value={searchQuery} placeholder="Try voice, 8GB, backup…" />
      </label>
      <nav class="settings-section-nav">
        {#each visibleSections as section}
          <button
            type="button"
            class:active={activeSectionId === section.id}
            aria-current={activeSectionId === section.id ? 'true' : undefined}
            onclick={() => scrollToSection(section.id)}
          >
            <span>{section.label}</span>
            <small>{section.summary}</small>
          </button>
        {/each}
      </nav>
      {#if visibleSections.length === 0}
        <p class="settings-empty-search">No settings match “{searchQuery}”.</p>
      {/if}
    </aside>

    <div class="settings-content settings-hub-content">
      {#if sectionVisible('general')}
        <section id="settings-general" class="settings-hub-section" aria-labelledby="settings-general-title">
          <div class="settings-section-heading">
            <span>{hubSections[0].eyebrow}</span>
            <h2 id="settings-general-title">{hubSections[0].title}</h2>
            <p>{hubSections[0].summary}</p>
          </div>
          <div class="settings-card settings-card-featured">
            <div class="setting-copy">
              <span class="setting-kicker">Trust</span>
              <h3>Private local operation</h3>
              <p>Core chat, settings, memory controls, and growth review remain local-first. Export is explicit and user-triggered.</p>
            </div>
            <div class="settings-health-stack" aria-label="Current defaults">
              <span>Memory {$settingsStore.longTermMemoryEnabled ? 'on' : 'paused'}</span>
              <span>TTS {$settingsStore.ttsEnabled ? 'on' : 'off'}</span>
              <span>{$settingsStore.performancePreset.replace('_', ' ')} mode</span>
            </div>
          </div>
        </section>
      {/if}

      {#if sectionVisible('appearance')}
        <section id="settings-appearance" class="settings-hub-section" aria-labelledby="settings-appearance-title">
          <div class="settings-section-heading">
            <span>{hubSections[1].eyebrow}</span>
            <h2 id="settings-appearance-title">{hubSections[1].title}</h2>
            <p>{hubSections[1].summary}</p>
          </div>
          <div class="settings-preview-grid">
            <article class="settings-card appearance-preview-card">
              <span class="setting-kicker">Preview</span>
              <h3>Premium dark shell</h3>
              <p>Soft borders, warm accents, and restrained motion keep the app intimate without spending GPU budget on decoration.</p>
              <div class="appearance-swatch-row" aria-hidden="true"><span></span><span></span><span></span><span></span></div>
            </article>
            <article class="settings-card appearance-preview-card">
              <span class="setting-kicker">Accessibility</span>
              <h3>Keyboard-first surfaces</h3>
              <p>Search, section navigation, toggles, radios, backup controls, and extension fields are reachable by keyboard.</p>
            </article>
          </div>
        </section>
      {/if}

      {#if sectionVisible('voice')}
        <section id="settings-voice" class="settings-hub-section" aria-labelledby="settings-voice-title">
          <div class="settings-section-heading">
            <span>{hubSections[2].eyebrow}</span>
            <h2 id="settings-voice-title">{hubSections[2].title}</h2>
            <p>{hubSections[2].summary}</p>
          </div>

          <article class="settings-card settings-wide voice-settings-card">
            <div class="setting-copy compact">
              <span class="setting-kicker">Playback</span>
              <h3>Text-to-speech playback</h3>
              <p>Speech stays interruptible and light on memory; TTS gets priority over queued images.</p>
            </div>
            <div class="voice-settings-grid">
              <label class="inline-toggle">
                <input type="checkbox" checked={$settingsStore.ttsEnabled} onchange={(event) => settingsStore.setTTSEnabled((event.currentTarget as HTMLInputElement).checked)} />
                <span>{$settingsStore.ttsEnabled ? 'Voice enabled' : 'Voice disabled'}</span>
              </label>
              <label class="inline-toggle">
                <input type="checkbox" checked={$settingsStore.ttsAutoPlay} disabled={!$settingsStore.ttsEnabled} onchange={(event) => settingsStore.setTTSAutoPlay((event.currentTarget as HTMLInputElement).checked)} />
                <span>{$settingsStore.ttsAutoPlay ? 'Auto-play new replies' : 'Manual playback only'}</span>
              </label>
              <label class="range-setting"><span>Volume <strong>{Math.round($settingsStore.ttsVolume * 100)}%</strong></span><input type="range" min="0" max="1" step="0.01" value={$settingsStore.ttsVolume} disabled={!$settingsStore.ttsEnabled} oninput={handleTTSVolumeChange} /></label>
              <label class="range-setting"><span>Speed <strong>{$settingsStore.ttsSpeed.toFixed(2)}×</strong></span><input type="range" min="0.75" max="1.35" step="0.05" value={$settingsStore.ttsSpeed} disabled={!$settingsStore.ttsEnabled} oninput={handleTTSSpeedChange} /></label>
            </div>
            <div class="option-grid voice-quality-grid" role="radiogroup" aria-label="TTS quality and speed preference">
              {#each ttsLatencyOptions as option}
                <button type="button" class:active={$settingsStore.ttsLatencyPreset === option.value} disabled={!$settingsStore.ttsEnabled} aria-pressed={$settingsStore.ttsLatencyPreset === option.value} onclick={() => settingsStore.setTTSLatencyPreset(option.value)}>
                  <strong>{option.label}</strong><span>{option.description}</span>
                </button>
              {/each}
            </div>
            <button type="button" class="soft-settings-action" onclick={previewVoiceSample}>Preview voice pacing</button>
          </article>

          <article class="settings-card settings-wide">
            <div class="setting-copy compact">
              <span class="setting-kicker">Character Mood</span>
              <h3>Per-character speech tuning</h3>
              <p>These are lightweight profile settings, not extra resident models.</p>
            </div>
            <div class="voice-mood-list" aria-live="polite">
              {#if voicesLoading}
                <p class="voice-mood-empty">Loading local voice profiles…</p>
              {:else if voiceProfiles.length === 0}
                <p class="voice-mood-empty">Create or link a character voice profile to reveal mood controls.</p>
              {:else}
                {#each voiceProfiles as profile (profile.voice_id)}
                  <article class="voice-mood-card">
                    <div class="voice-mood-header"><div><strong>{profile.name}</strong><span>{profile.type === 'character' ? 'Character voice' : 'Narrator'} · {profile.voice_id}</span></div>{#if savingMoodVoiceId === profile.voice_id}<small>Saving…</small>{/if}</div>
                    <label class="range-setting mood-range"><span>Baseline expressiveness <strong>{moodFor(profile).baseline_expressiveness.toFixed(2)}×</strong></span><small>How animated this voice feels before scene emotion is added.</small><input type="range" min="0" max="2" step="0.05" value={moodFor(profile).baseline_expressiveness} onchange={(event) => updateMoodSetting(profile, 'baseline_expressiveness', Number((event.currentTarget as HTMLInputElement).value))} /></label>
                    <label class="range-setting mood-range"><span>Emotional sensitivity <strong>{moodFor(profile).emotional_sensitivity.toFixed(2)}×</strong></span><small>How quickly memories, comfort, tension, and affection color delivery.</small><input type="range" min="0" max="2" step="0.05" value={moodFor(profile).emotional_sensitivity} onchange={(event) => updateMoodSetting(profile, 'emotional_sensitivity', Number((event.currentTarget as HTMLInputElement).value))} /></label>
                    <label class="range-setting mood-range"><span>NSFW intensity <strong>{moodFor(profile).nsfw_intensity.toFixed(2)}×</strong></span><small>How strongly intimate scene cues affect speech tags.</small><input type="range" min="0" max="2" step="0.05" value={moodFor(profile).nsfw_intensity} onchange={(event) => updateMoodSetting(profile, 'nsfw_intensity', Number((event.currentTarget as HTMLInputElement).value))} /></label>
                  </article>
                {/each}
              {/if}
            </div>
            {#if voiceMoodStatus}<p class="status-copy">{voiceMoodStatus}</p>{/if}
            {#if voiceMoodError}<p class="error-copy">{voiceMoodError}</p>{/if}
          </article>

          <article class="settings-card settings-wide clone-voice-section">
            <div class="setting-copy compact"><span class="setting-kicker">Voice clone</span><h3>Local zero-shot profile</h3><p>Use a short reference to create a reusable local voice profile.</p></div>
            <div class="clone-controls">
              <label class="text-setting"><span>Profile name</span><input type="text" bind:value={cloneName} maxlength="80" placeholder="Character voice name" /></label>
              <label class="text-setting"><span>Reference audio</span><input type="file" accept="audio/*" onchange={handleCloneFileChange} /></label>
              <div class="clone-actions"><button type="button" class="soft-settings-action" onclick={isRecording ? stopRecording : startRecording}>{isRecording ? 'Stop recording' : 'Record reference'}</button><button type="button" class="soft-settings-action primary" disabled={isCreatingVoice || !cloneAudio || !cloneName.trim()} onclick={createVoiceProfile}>{isCreatingVoice ? 'Creating…' : 'Create voice profile'}</button></div>
            </div>
            {#if cloneRecordingUrl}<audio controls src={cloneRecordingUrl} aria-label="Selected voice reference preview"></audio>{/if}
            {#if cloneStatus}<p class="status-copy">{cloneStatus}</p>{/if}
            {#if cloneError}<p class="error-copy">{cloneError}</p>{/if}
          </article>
        </section>
      {/if}

      {#if sectionVisible('images')}
        <section id="settings-images" class="settings-hub-section" aria-labelledby="settings-images-title">
          <div class="settings-section-heading"><span>{hubSections[3].eyebrow}</span><h2 id="settings-images-title">{hubSections[3].title}</h2><p>{hubSections[3].summary}</p></div>
          <article class="settings-card settings-wide image-settings-card">
            <label class="inline-toggle"><input type="checkbox" checked={$settingsStore.imageAutoGenerateOnAssistant} onchange={(event) => settingsStore.setImageAutoGenerateOnAssistant((event.currentTarget as HTMLInputElement).checked)} /><span>{$settingsStore.imageAutoGenerateOnAssistant ? 'Auto-generate after replies' : 'Ask before generating images'}</span></label>
            <div class="image-preset-preview-grid" role="radiogroup" aria-label="Default image generation preset">
              {#each imagePresetOptions as option}
                <button type="button" class:active={$settingsStore.imageDefaultPreset === option.value} aria-pressed={$settingsStore.imageDefaultPreset === option.value} onclick={() => handleImageDefaultPresetChange(option.value)}>
                  <span class="image-preview-tile" aria-hidden="true">{option.label.slice(0, 1)}</span><strong>{option.label}</strong><small>{option.preview}</small><p>{option.description}</p><em>{option.impact}</em>
                </button>
              {/each}
            </div>
          </article>
        </section>
      {/if}

      {#if sectionVisible('growth')}
        <section id="settings-growth" class="settings-hub-section" aria-labelledby="settings-growth-title">
          <div class="settings-section-heading"><span>{hubSections[4].eyebrow}</span><h2 id="settings-growth-title">{hubSections[4].title}</h2><p>{hubSections[4].summary}</p></div>
          <article class="settings-card settings-wide"><div class="setting-copy compact"><span class="setting-kicker">Reflection</span><h3>Cadence and care</h3><p>Reflection is slower growth after the conversation settles, not hidden mutation during a reply.</p></div>
            <label class="inline-toggle"><input type="checkbox" checked={$settingsStore.selfReflectionEnabled} onchange={(event) => settingsStore.setSelfReflectionEnabled((event.currentTarget as HTMLInputElement).checked)} /><span>{$settingsStore.selfReflectionEnabled ? 'Self-reflection enabled' : 'Self-reflection paused'}</span></label>
            <div class="option-grid" role="radiogroup" aria-label="Reflection frequency">{#each reflectionFrequencyOptions as option}<button type="button" class:active={$settingsStore.reflectionFrequency === option.value} aria-pressed={$settingsStore.reflectionFrequency === option.value} onclick={() => settingsStore.setReflectionFrequency(option.value)}><strong>{option.label}</strong><span>{option.description}</span></button>{/each}</div>
            <div class="option-grid" role="radiogroup" aria-label="Reflection sensitivity">{#each reflectionSensitivityOptions as option}<button type="button" class:active={$settingsStore.reflectionSensitivity === option.value} aria-pressed={$settingsStore.reflectionSensitivity === option.value} onclick={() => settingsStore.setReflectionSensitivity(option.value)}><strong>{option.label}</strong><span>{option.description}</span></button>{/each}</div>
            <label class="inline-toggle"><input type="checkbox" checked={$settingsStore.growthNotificationsEnabled} onchange={(event) => settingsStore.setGrowthNotificationsEnabled((event.currentTarget as HTMLInputElement).checked)} /><span>{$settingsStore.growthNotificationsEnabled ? 'Show gentle growth notes' : 'Keep growth quiet'}</span></label>
          </article>
        </section>
      {/if}

      {#if sectionVisible('memory')}
        <section id="settings-memory" class="settings-hub-section" aria-labelledby="settings-memory-title">
          <div class="settings-section-heading"><span>{hubSections[5].eyebrow}</span><h2 id="settings-memory-title">{hubSections[5].title}</h2><p>{hubSections[5].summary}</p></div>
          <article class="settings-card settings-card-featured"><div class="setting-copy"><span class="setting-kicker">Memory</span><h3>Long-term memory</h3><p id="long-term-memory-description">Let Reverie keep important preferences, promises, and boundaries. Turning this off pauses durable remembering without deleting existing memory.</p></div><label class="toggle-switch"><input type="checkbox" checked={$settingsStore.longTermMemoryEnabled} onchange={(event) => settingsStore.setLongTermMemoryEnabled((event.currentTarget as HTMLInputElement).checked)} aria-describedby="long-term-memory-description" /><span>{$settingsStore.longTermMemoryEnabled ? 'On' : 'Off'}</span></label></article>
          <article class="settings-card settings-wide"><div class="setting-copy compact"><span class="setting-kicker">8GB awareness</span><h3>Context budget</h3><p>Balanced is designed for smooth local use on the 8GB target.</p></div><div class="budget-grid" role="radiogroup" aria-label="Context budget preset">{#each contextBudgetOptions as option}<button type="button" class:active={$settingsStore.contextBudgetPreset === option.value} aria-pressed={$settingsStore.contextBudgetPreset === option.value} onclick={() => settingsStore.setContextBudgetPreset(option.value)}><span>{option.detail}</span><strong>{option.label}</strong><small>{option.description}</small></button>{/each}</div></article>
          <article class="settings-card"><span class="setting-kicker">Pruning</span><h3>Memory pruning lives in Memory Browser</h3><p class="performance-explainer">This hub explains the policy. Detailed review, edit, bulk pruning, provenance, and deletion stay in the Memory Browser so you can inspect evidence before removing durable records.</p></article>
        </section>
      {/if}

      {#if sectionVisible('extensions')}
        <section id="settings-extensions" class="settings-hub-section" aria-labelledby="settings-extensions-title">
          <div class="settings-section-heading"><span>{hubSections[6].eyebrow}</span><h2 id="settings-extensions-title">{hubSections[6].title}</h2><p>{hubSections[6].summary}</p></div>
          <article class="settings-card settings-wide extension-settings-card">
            <div class="extension-status" aria-live="polite">{#if extensionsLoading}<span>Loading extension contracts…</span>{:else if extensionError}<span class="error">{extensionError}</span>{:else if extensionStatus}<span>{extensionStatus}</span>{/if}</div>
            {#if $extensionSettingsSections.length === 0}
              <p class="performance-explainer">No extension setting sections are registered yet.</p>
            {:else}
              <div class="extension-section-list">{#each $extensionSettingsSections as section (`${section.extensionId}:${section.section_id}`)}<section class="extension-section" aria-label={section.title}><div><span class="setting-kicker">{section.extensionName}</span><h3>{section.title}</h3>{#if section.description}<p>{section.description}</p>{/if}</div><div class="extension-field-list">{#each section.fields as field (`${section.extensionId}:${section.section_id}:${field.key}`)}{#if field.kind === 'boolean'}<label class="checkbox-setting"><input type="checkbox" checked={Boolean(extensionSettingValue(section.extensionId, field))} onchange={(event) => handleExtensionInput(section.extensionId, field, event)} /><span>{field.label}{field.description ? ` — ${field.description}` : ''}</span></label>{:else if field.kind === 'number'}<label class="text-setting"><span>{field.label}</span>{#if field.description}<small>{field.description}</small>{/if}<input type="number" min={field.min_value ?? undefined} max={field.max_value ?? undefined} value={Number(extensionSettingValue(section.extensionId, field) ?? 0)} onchange={(event) => handleExtensionInput(section.extensionId, field, event)} /></label>{:else if field.kind === 'select'}<label class="text-setting"><span>{field.label}</span>{#if field.description}<small>{field.description}</small>{/if}<select value={String(extensionSettingValue(section.extensionId, field) ?? '')} onchange={(event) => handleExtensionInput(section.extensionId, field, event)}>{#each field.options as option}<option value={option}>{option}</option>{/each}</select></label>{:else}<label class="text-setting"><span>{field.label}</span>{#if field.description}<small>{field.description}</small>{/if}<input type="text" value={String(extensionSettingValue(section.extensionId, field) ?? '')} maxlength="500" onchange={(event) => handleExtensionInput(section.extensionId, field, event)} /></label>{/if}{/each}</div></section>{/each}</div>
            {/if}
          </article>
        </section>
      {/if}

      {#if sectionVisible('performance')}
        <section id="settings-performance" class="settings-hub-section" aria-labelledby="settings-performance-title">
          <div class="settings-section-heading"><span>{hubSections[7].eyebrow}</span><h2 id="settings-performance-title">{hubSections[7].title}</h2><p>{hubSections[7].summary}</p></div>
          <article class="settings-card settings-wide"><div class="budget-grid" role="radiogroup" aria-label="Performance preset">{#each performancePresetOptions as option}<button type="button" class:active={$settingsStore.performancePreset === option.value} aria-pressed={$settingsStore.performancePreset === option.value} onclick={() => settingsStore.setPerformancePreset(option.value)}><span>{option.detail}</span><strong>{option.label}</strong><small>{option.description}</small></button>{/each}</div><label class="range-setting"><span>Background task limit <strong>{$settingsStore.backgroundTaskLimit}</strong></span><small>Caps non-interactive jobs like indexing, gallery refreshes, and media helpers so chat and voice stay responsive.</small><input type="range" min="1" max="3" step="1" value={$settingsStore.backgroundTaskLimit} onchange={(event) => settingsStore.setBackgroundTaskLimit(Number((event.currentTarget as HTMLInputElement).value))} /></label><label class="checkbox-setting"><input type="checkbox" checked={$settingsStore.proactiveResourceWarnings} onchange={(event) => settingsStore.setProactiveResourceWarnings((event.currentTarget as HTMLInputElement).checked)} /><span>Show proactive VRAM warnings and auto-downgrade explanations.</span></label><p class="performance-explainer">TTS always has priority. Image generation runs as one exclusive queued job, unloads idle Orpheus first, and automatically falls back toward preview quality when VRAM approaches the 8GB guardrails.</p></article>
        </section>
      {/if}

      {#if sectionVisible('data')}
        <section id="settings-data" class="settings-hub-section" aria-labelledby="settings-data-title">
          <div class="settings-section-heading"><span>{hubSections[8].eyebrow}</span><h2 id="settings-data-title">{hubSections[8].title}</h2><p>{hubSections[8].summary}</p></div>
          <article class="settings-card settings-wide data-management-card">
            <div class="data-action-grid">
              <button type="button" onclick={() => exportBackup('settings')}><strong>Export settings</strong><span>Core and extension settings JSON.</span></button>
              <button type="button" onclick={() => exportBackup('characters')}><strong>Export characters</strong><span>Backup envelope ready for character data.</span></button>
              <button type="button" onclick={() => exportBackup('growth')}><strong>Export growth data</strong><span>Growth-ready envelope with local settings.</span></button>
              <button type="button" onclick={() => exportBackup('full')}><strong>Full backup</strong><span>Settings plus Reverie local storage snapshot.</span></button>
            </div>
            <div class="import-row"><input class="sr-only" bind:this={importInput} id="settings-import-file" type="file" accept="application/json,.json" onchange={importSettingsFile} /><label for="settings-import-file" class="soft-settings-action primary">Import settings JSON</label><p>Imports only recognized settings fields; unknown data is ignored.</p></div>
            <div class="reset-card"><div><span class="setting-kicker">Reset</span><h3>Restore defaults</h3><p>Type <strong>RESET</strong> to confirm. This restores core settings and clears extension setting values, but does not delete memories, voices, images, or growth artifacts.</p></div><input type="text" bind:value={resetConfirmation} placeholder="Type RESET" aria-label="Reset confirmation" /><button type="button" class="danger-settings-action" onclick={resetToDefaults}>Reset to defaults</button></div>
            {#if dataStatus}<p class="status-copy" aria-live="polite">{dataStatus}</p>{/if}
            {#if dataError}<p class="error-copy" aria-live="assertive">{dataError}</p>{/if}
          </article>
        </section>
      {/if}

      <aside class="settings-trust-note" aria-label="Settings trust note">
        <span aria-hidden="true">✦</span>
        <div><strong>You stay in control.</strong><p>Settings are saved locally, extension fields are isolated by extension ID, and expensive media or learning work stays behind 8GB-aware queues and explicit review paths.</p></div>
        <button type="button" onclick={() => scrollToSection('data')}>Open backups</button>
      </aside>
    </div>
  </div>
</section>
