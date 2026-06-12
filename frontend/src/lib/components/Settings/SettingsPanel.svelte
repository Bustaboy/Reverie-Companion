<script lang="ts">
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';
  import {
    settingsStore,
    type AppearanceTheme,
    type ContextBudgetPreset,
    type ImageDefaultPreset,
    type InterfaceDensity,
    type MemoryPruningMode,
    type PerformancePreset,
    type ReflectionFrequency,
    type ReflectionSensitivity,
    type TTSLatencyPreset
  } from '$lib/stores/settingsStore';
  import { voiceService, type VoiceMoodSettings, type VoiceProfile } from '$lib/api/voiceService';
  import { extensionService } from '$lib/api/extensionService';
  import { extensionEventBus } from '$lib/extensions/extensionBus';
  import { extensionRegistry, extensionSettingsSections } from '$lib/extensions/registry';
  import type { ExtensionSettingField } from '$lib/extensions/contracts';

  type SettingsSectionId =
    | 'general'
    | 'whats-new'
    | 'appearance'
    | 'voice'
    | 'images'
    | 'growth'
    | 'memory'
    | 'extensibility'
    | 'performance'
    | 'backup';

  const SETTINGS_STORAGE_KEY = 'reverie.memoryReflectionSettings.v2';
  const PINNED_JOURNAL_STORAGE_KEY = 'reverie.journal.pinnedEntryIds.v1';
  const BACKUP_KIND = 'reverie.settings_control_hub.backup';

  type BackupScope = 'characters' | 'growth' | 'settings' | 'full';

  const settingsSections: Array<{
    id: SettingsSectionId;
    label: string;
    eyebrow: string;
    description: string;
    search: string;
  }> = [
    {
      id: 'general',
      label: 'General',
      eyebrow: 'Start here',
      description: 'Local autosave, defaults, and day-to-day companion behavior.',
      search: 'general autosave local defaults companion behavior privacy'
    },
    {
      id: 'whats-new',
      label: 'What’s New',
      eyebrow: 'Milestone 3',
      description: 'A concise tour of the completed immersion, growth, media, and release polish stack.',
      search: 'what new milestone 3 visual novel tts images growth settings release polish onboarding'
    },
    {
      id: 'appearance',
      label: 'Appearance',
      eyebrow: 'Warm interface',
      description: 'Choose the premium dark feel, density, and motion comfort.',
      search: 'appearance theme dark ember midnight density compact comfortable motion accessibility'
    },
    {
      id: 'voice',
      label: 'TTS & Voice',
      eyebrow: 'Spoken presence',
      description: 'Speech playback, mood-sensitive delivery, and local voice profiles.',
      search: 'tts voice speech autoplay volume speed latency mood orpheus piper clone nsfw sample preview'
    },
    {
      id: 'images',
      label: 'Image Generation',
      eyebrow: 'Scene visuals',
      description: '8GB-aware presets and optional assistant image automation.',
      search: 'image generation comfyui preset preview balanced high auto assistant scene visualization'
    },
    {
      id: 'growth',
      label: 'Growth & Self-Learning',
      eyebrow: 'Transparent change',
      description: 'Reflection pace, sensitivity, growth notes, and training guardrails.',
      search: 'growth self learning reflection frequency sensitivity notifications automation training lora adapter'
    },
    {
      id: 'memory',
      label: 'Memory',
      eyebrow: 'Continuity',
      description: 'Long-term memory, context budget, and pruning posture.',
      search: 'memory long term context budget pruning recall preferences promises boundaries'
    },
    {
      id: 'extensibility',
      label: 'Extensibility',
      eyebrow: 'Extension hub',
      description: 'Extension-registered settings with isolated local persistence.',
      search: 'extensibility extensions plugins manifests settings sections diagnostics contracts'
    },
    {
      id: 'performance',
      label: 'Performance & 8GB',
      eyebrow: 'Resource safety',
      description: 'VRAM guardrails, background task limits, and downgrade explanations.',
      search: 'performance 8gb vram guardrails resource background task warnings downgrade oom rtx 4070'
    },
    {
      id: 'backup',
      label: 'Import / Export',
      eyebrow: 'Portability',
      description: 'Export characters, growth data, settings, or a full local backup.',
      search: 'backup export import characters growth settings restore reset defaults'
    }
  ];

  const milestoneHighlights: Array<{ title: string; detail: string; impact: string }> = [
    {
      title: 'Visual Novel foundation',
      detail: 'Dynamic expressions and a full-immersive scene mode now react to chat emotion, memory, reflection, and growth cues without keeping heavy visual runtimes resident.',
      impact: '8GB impact: lightweight sprites and lazy assets; no Live2D/GPU model tax.'
    },
    {
      title: 'Emotional TTS',
      detail: 'Assistant replies can route through local voice profiles with mood-aware prosody, streaming playback, voice cloning foundations, and per-character tuning.',
      impact: '8GB impact: Piper/fast modes stay responsive; richer voices yield to chat and image jobs.'
    },
    {
      title: 'In-chat image generation',
      detail: 'Scene prompts can draw from conversation, character state, and VN context, then land in a persistent local gallery with retry and reuse controls.',
      impact: '8GB impact: one queued ComfyUI job at a time, preview-first defaults, automatic downgrades.'
    },
    {
      title: 'Growth visibility',
      detail: 'Growth Dashboard, Diary Journal, Memory Browser, Personal LoRA review, and Character Encyclopedia make self-learning inspectable and reversible.',
      impact: 'Trust impact: approval gates before training; private/deleted content stays excluded.'
    },
    {
      title: 'Settings & extensibility hub',
      detail: 'A searchable Control Hub now centralizes memory, media, performance, backup, and extension settings with typed manifest isolation.',
      impact: 'Release impact: safer defaults, clear copy, and portable local JSON backups.'
    }
  ];

  const backupScopeOptions: Array<{ scope: BackupScope; label: string; description: string }> = [
    { scope: 'characters', label: 'characters', description: 'character and voice-facing local keys' },
    { scope: 'growth', label: 'growth data', description: 'journal, reflection, memory, growth, and training-facing local keys' },
    { scope: 'settings', label: 'settings', description: 'core settings, extension settings, and API base URL' },
    { scope: 'full', label: 'full local backup', description: 'every current reverie.* browser key plus the settings snapshot' }
  ];

  const appearanceOptions: Array<{ value: AppearanceTheme; label: string; description: string }> = [
    { value: 'warm_dark', label: 'Warm dark', description: 'Default premium near-black palette with rose-gold warmth.' },
    { value: 'ember', label: 'Ember', description: 'Softer copper accents for a more intimate evening feel.' },
    { value: 'midnight', label: 'Midnight', description: 'Quieter blue-black contrast for long sessions.' }
  ];

  const densityOptions: Array<{ value: InterfaceDensity; label: string; description: string }> = [
    { value: 'comfortable', label: 'Comfortable', description: 'Roomier cards and copy for clarity.' },
    { value: 'compact', label: 'Compact', description: 'Tighter spacing for laptop screens.' }
  ];

  const reflectionFrequencyOptions: Array<{ value: ReflectionFrequency; label: string; description: string }> = [
    { value: 'low', label: 'Low', description: 'Reflect only after clear milestones or when you ask for it.' },
    { value: 'balanced', label: 'Balanced', description: 'Notice meaningful patterns without interrupting ordinary conversation.' },
    { value: 'high', label: 'High', description: 'Check in more often after emotional turns, repairs, or important promises.' }
  ];

  const reflectionSensitivityOptions: Array<{ value: ReflectionSensitivity; label: string; description: string }> = [
    { value: 'conservative', label: 'Conservative', description: 'Only keep what is explicit, repeated, or clearly important.' },
    { value: 'balanced', label: 'Balanced', description: 'A careful middle path for preferences, boundaries, and relationship moments.' },
    { value: 'responsive', label: 'Responsive', description: 'Notice subtler shifts while still avoiding big assumptions.' }
  ];

  const pruningOptions: Array<{ value: MemoryPruningMode; label: string; description: string }> = [
    { value: 'protective', label: 'Protective', description: 'Keep more approved memories; prune only stale low-confidence notes.' },
    { value: 'balanced', label: 'Balanced', description: 'Recommended: protect identity, boundaries, promises, and recent relationship context.' },
    { value: 'lean', label: 'Lean', description: 'Trim aggressively to reduce storage and retrieval noise on modest systems.' }
  ];

  const contextBudgetOptions: Array<{ value: ContextBudgetPreset; label: string; description: string; detail: string }> = [
    { value: 'gentle', label: 'Gentle', description: 'Keeps recall lighter for busy laptops or battery moments.', detail: 'Smallest memory bundle' },
    { value: 'balanced', label: 'Balanced', description: 'Recommended for the 8GB target: warm continuity with calm resource use.', detail: '8GB-aware default' },
    { value: 'roomy', label: 'Roomy', description: 'Allows a little more remembered context when your system has headroom.', detail: 'More context when idle' }
  ];

  const imagePresetOptions: Array<{ value: ImageDefaultPreset; label: string; description: string; impact: string }> = [
    { value: 'preview_8gb', label: 'Preview', description: 'Fastest and safest default for 8GB laptops.', impact: 'Lowest VRAM pressure' },
    { value: 'balanced_8gb', label: 'Balanced', description: 'Higher detail when VRAM is available; falls back safely.', impact: 'Guarded quality' },
    { value: 'high_8gb', label: 'High', description: 'Best local detail, still queued and 8GB-gated.', impact: 'Use with headroom' }
  ];

  const performancePresetOptions: Array<{ value: PerformancePreset; label: string; description: string; detail: string }> = [
    { value: '8gb_safe', label: '8GB Safe', description: 'Prioritizes TTS responsiveness, preview images, gentle context, and one background task.', detail: 'Best for RTX 4070 laptop defaults' },
    { value: 'balanced', label: 'Balanced', description: 'Keeps normal 8GB guardrails while allowing richer context when the machine is idle.', detail: 'Recommended daily mode' },
    { value: 'quality', label: 'Quality', description: 'Opts up to roomier context and more expressive voice/image quality after headroom checks.', detail: 'Use when plugged in with thermal headroom' }
  ];

  const ttsLatencyOptions: Array<{ value: TTSLatencyPreset; label: string; description: string }> = [
    { value: 'quality', label: 'Quality', description: 'Prefer Orpheus-style expressiveness when the machine has room.' },
    { value: 'balanced', label: 'Balanced', description: 'Recommended for 8GB: expressive enough without aggressive preloading.' },
    { value: 'speed', label: 'Speed', description: 'Favor quick fallback voices and interruption-friendly playback.' }
  ];

  let activeSection = $state<SettingsSectionId>('whats-new');
  let searchQuery = $state('');
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
  let backupStatus = $state<string | null>(null);
  let backupError = $state<string | null>(null);
  let importFileInput = $state<HTMLInputElement | null>(null);
  let samplePreview = $state('Warm, close, and emotionally aware — with TTS priority protected on 8GB systems.');

  const cloneAudio = $derived(cloneRecording ?? cloneFile);
  const normalizedSearch = $derived(searchQuery.trim().toLowerCase());
  const matchingSections = $derived(
    settingsSections.filter((section) => !normalizedSearch || `${section.label} ${section.description} ${section.search}`.toLowerCase().includes(normalizedSearch))
  );
  const visibleSectionIds = $derived(new Set(matchingSections.map((section) => section.id)));
  const searchSummary = $derived(
    normalizedSearch
      ? `${matchingSections.length} matching section${matchingSections.length === 1 ? '' : 's'}`
      : 'All core controls visible'
  );
  const savedLabel = $derived(
    $settingsStore.savedAt
      ? `Saved locally ${$settingsStore.savedAt.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`
      : 'Saved locally on this device'
  );
  const activeImagePreset = $derived(imagePresetOptions.find((option) => option.value === $settingsStore.imageDefaultPreset) ?? imagePresetOptions[0]);
  const activePerformancePreset = $derived(performancePresetOptions.find((option) => option.value === $settingsStore.performancePreset) ?? performancePresetOptions[0]);
  const visibleExtensionSections = $derived(
    normalizedSearch
      ? $extensionSettingsSections.filter((section) => `${section.title} ${section.description ?? ''} ${section.extensionName}`.toLowerCase().includes(normalizedSearch))
      : $extensionSettingsSections
  );

  const shouldShow = (sectionId: SettingsSectionId) => visibleSectionIds.has(sectionId);

  const defaultMoodSettings = (): VoiceMoodSettings => ({ baseline_expressiveness: 1, emotional_sensitivity: 1, nsfw_intensity: 1 });
  const moodFor = (profile: VoiceProfile): VoiceMoodSettings => profile.mood_settings ?? defaultMoodSettings();

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
      extensionEventBus.publish('settings.extensions_loaded', 'settings', 'reverie.settings', { extension_count: registry.extensions.length });
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

  const setExtensionSetting = (extensionId: string, field: ExtensionSettingField, value: boolean | number | string | null) => {
    settingsStore.setExtensionSetting(extensionId, field.key, value);
    extensionEventBus.publish('settings.extension_setting_changed', 'settings', extensionId, { key: field.key, value });
  };

  const handleExtensionInput = (extensionId: string, field: ExtensionSettingField, event: Event) => {
    const target = event.currentTarget as HTMLInputElement | HTMLSelectElement;
    if (field.kind === 'boolean') return setExtensionSetting(extensionId, field, (target as HTMLInputElement).checked);
    if (field.kind === 'number') return setExtensionSetting(extensionId, field, Number(target.value));
    setExtensionSetting(extensionId, field, target.value);
  };

  onMount(() => {
    void loadVoiceProfiles();
    void loadExtensions();
    return () => {
      if (cloneRecordingUrl) URL.revokeObjectURL(cloneRecordingUrl);
    };
  });

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
    voiceProfiles = voiceProfiles.map((candidate) => (candidate.voice_id === profile.voice_id ? { ...candidate, mood_settings: nextMood } : candidate));
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

  const localStorageEntriesForScope = (scope: BackupScope) => {
    if (!browser) return {};
    const entries: Record<string, string> = {};
    for (let index = 0; index < window.localStorage.length; index += 1) {
      const key = window.localStorage.key(index);
      if (!key) continue;
      const normalized = key.toLowerCase();
      const include =
        scope === 'full'
          ? key.startsWith('reverie.')
          : scope === 'settings'
            ? key === SETTINGS_STORAGE_KEY || normalized.includes('setting') || normalized.includes('api')
            : scope === 'growth'
              ? normalized.includes('growth') || normalized.includes('journal') || normalized.includes('reflection') || normalized.includes('lora') || normalized.includes('memory')
              : normalized.includes('character') || normalized.includes('voice') || normalized.includes('persona');
      if (include) entries[key] = window.localStorage.getItem(key) ?? '';
    }
    if (scope === 'growth' && window.localStorage.getItem(PINNED_JOURNAL_STORAGE_KEY)) {
      entries[PINNED_JOURNAL_STORAGE_KEY] = window.localStorage.getItem(PINNED_JOURNAL_STORAGE_KEY) ?? '';
    }
    return Object.fromEntries(Object.entries(entries).sort(([left], [right]) => left.localeCompare(right)));
  };

  const downloadJson = (filename: string, payload: unknown) => {
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.rel = 'noopener';
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 750);
  };

  const exportBackup = (scope: BackupScope) => {
    backupError = null;
    const scopeCopy = backupScopeOptions.find((option) => option.scope === scope) ?? backupScopeOptions[3];
    const localStorage = localStorageEntriesForScope(scope);
    const exportedAt = new Date();
    const payload = {
      kind: BACKUP_KIND,
      version: 1,
      scope,
      scope_label: scopeCopy.label,
      exported_at: exportedAt.toISOString(),
      source: 'Reverie Settings & Control Hub',
      note: 'Local-first export. Backend character/growth databases remain authoritative when connected; this captures current browser-side control hub state.',
      included_local_storage_keys: Object.keys(localStorage),
      control_hub_snapshot: settingsStore.getSnapshot(),
      settings: settingsStore.getSnapshot(),
      local_storage: localStorage
    };
    const stamp = exportedAt.toISOString().replace(/[:.]/g, '-');
    downloadJson(`reverie-${scope}-backup-${stamp}.json`, payload);
    backupStatus = `Exported ${scopeCopy.label} (${Object.keys(localStorage).length} local key${Object.keys(localStorage).length === 1 ? '' : 's'}).`;
  };

  const importBackup = async (event: Event) => {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    backupError = null;
    backupStatus = `Reading ${file.name}…`;
    try {
      const payload = JSON.parse(await file.text()) as {
        kind?: string;
        scope?: BackupScope;
        settings?: unknown;
        control_hub_snapshot?: unknown;
        local_storage?: Record<string, unknown>;
      };
      if (payload.kind && payload.kind !== BACKUP_KIND) {
        throw new Error('This JSON file is not a Reverie Settings & Control Hub backup.');
      }
      const safeEntries = Object.entries(payload.local_storage ?? {}).filter(
        (entry): entry is [string, string] => entry[0].startsWith('reverie.') && typeof entry[1] === 'string'
      );
      const scopeLabel = payload.scope ? (backupScopeOptions.find((option) => option.scope === payload.scope)?.label ?? payload.scope) : 'local';
      const hasSettings = Boolean(payload.settings ?? payload.control_hub_snapshot);
      if (safeEntries.length === 0 && !hasSettings) {
        throw new Error('That backup did not contain importable Reverie settings or local storage keys.');
      }
      const confirmed = confirm(
        `Import ${file.name}?\n\nThis will replace ${safeEntries.length} matching local key${safeEntries.length === 1 ? '' : 's'} from the ${scopeLabel} backup${hasSettings ? ' and refresh Control Hub settings' : ''}.`
      );
      if (!confirmed) {
        backupStatus = 'Import cancelled. No local data was changed.';
        return;
      }
      if (browser) {
        for (const [key, value] of safeEntries) window.localStorage.setItem(key, value);
      }
      const settingsPayload = payload.settings ?? payload.control_hub_snapshot;
      if (settingsPayload) {
        settingsStore.importSettingsPayload(settingsPayload);
      } else if (browser) {
        const rawSettings = window.localStorage.getItem(SETTINGS_STORAGE_KEY);
        if (rawSettings) settingsStore.importSettingsPayload(JSON.parse(rawSettings));
      }
      backupStatus = `Imported ${file.name}: ${safeEntries.length} local key${safeEntries.length === 1 ? '' : 's'} restored.`;
    } catch (error) {
      backupError = error instanceof Error ? error.message : 'That file was not a readable Reverie backup.';
      backupStatus = null;
    } finally {
      input.value = '';
    }
  };

  const resetWithConfirmation = () => {
    const phrase = prompt('Type RESET to restore calm defaults. Extension settings saved under the hub will also be cleared.');
    if (phrase !== 'RESET') {
      backupStatus = 'Reset cancelled. No settings were changed.';
      return;
    }
    settingsStore.resetMemoryReflectionSettings();
    backupStatus = 'Restored calm defaults.';
    backupError = null;
  };
</script>

<section class="settings-panel control-hub" class:settings-compact={$settingsStore.interfaceDensity === 'compact'} aria-labelledby="settings-title">
  <header class="settings-hero control-hub-hero">
    <div>
      <p class="eyebrow">Settings & Control Hub</p>
      <h1 id="settings-title">One calm place to tune Reverie</h1>
      <p class="subtitle">
        Search every major local control, review the 8GB impact before changing quality, and let extensions add their own safe setting sections without cluttering the core experience.
      </p>
    </div>
    <div class="settings-hero-actions">
      <div class="settings-save-pill" aria-live="polite"><span aria-hidden="true">✓</span>{savedLabel}</div>
      <button type="button" class="hub-secondary-action" onclick={() => exportBackup('full')}>Quick backup</button>
    </div>
  </header>

  <div class="settings-hub-layout">
    <aside class="settings-hub-nav" aria-label="Settings sections">
      <label class="settings-search">
        <span>Search settings</span>
        <input type="search" bind:value={searchQuery} placeholder="Try “8GB”, “voice”, “backup”…" aria-label="Search settings" />
      </label>
      <nav>
        {#each matchingSections as section}
          {#if shouldShow(section.id)}
            <button type="button" class:active={activeSection === section.id} onclick={() => (activeSection = section.id)}>
              <span>{section.eyebrow}</span>
              <strong>{section.label}</strong>
            </button>
          {/if}
        {/each}
      </nav>
      <div class="settings-nav-meta" aria-live="polite">
        <span>{searchSummary}</span>
        <button type="button" disabled={!normalizedSearch} onclick={() => (searchQuery = '')}>Clear search</button>
      </div>
      <p class="settings-nav-note">Core controls save instantly to this device. Backend safety gates can still downgrade heavy jobs to protect the 8GB target.</p>
    </aside>

    <div class="settings-content control-hub-content">
      {#if matchingSections.length === 0}
        <section class="settings-empty-state settings-wide" aria-live="polite">
          <span aria-hidden="true">⌕</span>
          <h2>No settings matched “{searchQuery}”.</h2>
          <p>Try a broader word like “voice”, “memory”, “8GB”, “backup”, or clear search to return to the full Control Hub.</p>
          <button type="button" class="hub-secondary-action" onclick={() => (searchQuery = '')}>Clear search</button>
        </section>
      {/if}

      {#if shouldShow('whats-new') && (!normalizedSearch || activeSection === 'whats-new')}
        <section class="settings-section settings-wide" aria-labelledby="whats-new-settings-title">
          <div class="settings-section-heading">
            <span class="setting-kicker">Milestone 3</span>
            <h2 id="whats-new-settings-title">What’s new in Milestone 3</h2>
            <p>Milestone 3 closes the first complete immersion and production-readiness arc: characters can be seen, heard, remembered, reviewed, extended, backed up, and protected by clear 8GB resource guardrails.</p>
          </div>
          <div class="milestone-card-grid">
            {#each milestoneHighlights as item}
              <article class="settings-card milestone-card">
                <strong>{item.title}</strong>
                <p>{item.detail}</p>
                <span>{item.impact}</span>
              </article>
            {/each}
          </div>
          <aside class="settings-inline-tip" aria-label="Milestone 3 tip">
            <span aria-hidden="true">✦</span>
            <p><strong>Suggested first tour:</strong> open Visual Novel mode, enable TTS if you want spoken replies, generate one scene image from chat, then review Growth and Memory to see what Reverie learned.</p>
          </aside>
        </section>
      {/if}

      {#if shouldShow('general') && (!normalizedSearch || activeSection === 'general')}
        <section class="settings-section settings-wide" aria-labelledby="general-settings-title">
          <div class="settings-section-heading">
            <span class="setting-kicker">General</span>
            <h2 id="general-settings-title">Local control center</h2>
            <p>Reverie keeps these controls lightweight: no resident settings service, no cloud dependency, and clear reset/export escape hatches.</p>
          </div>
          <div class="settings-card-grid three-up">
            <article class="settings-card mini-hub-card">
              <strong>Local-first</strong>
              <span>{savedLabel}</span>
              <p>Settings persist in local storage until backend-wide preferences are connected.</p>
            </article>
            <article class="settings-card mini-hub-card">
              <strong>Current 8GB mode</strong>
              <span>{activePerformancePreset.label}</span>
              <p>{activePerformancePreset.detail}</p>
            </article>
            <article class="settings-card mini-hub-card">
              <strong>Extension sections</strong>
              <span>{$extensionSettingsSections.length}</span>
              <p>Registered declaratively through the Task 5C extension contract.</p>
            </article>
          </div>
        </section>
      {/if}

      {#if shouldShow('appearance') && (!normalizedSearch || activeSection === 'appearance')}
        <section class="settings-section settings-wide" aria-labelledby="appearance-settings-title">
          <div class="settings-section-heading">
            <span class="setting-kicker">Appearance</span>
            <h2 id="appearance-settings-title">Warm premium dark design</h2>
            <p>These preferences are intentionally cheap CSS-level choices, so they do not affect model memory or local inference performance.</p>
          </div>
          <article class="settings-card settings-wide">
            <div class="option-grid" role="radiogroup" aria-label="Appearance theme">
              {#each appearanceOptions as option}
                <button type="button" class:active={$settingsStore.appearanceTheme === option.value} aria-pressed={$settingsStore.appearanceTheme === option.value} onclick={() => settingsStore.setAppearanceTheme(option.value)}>
                  <strong>{option.label}</strong>
                  <span>{option.description}</span>
                </button>
              {/each}
            </div>
            <div class="appearance-preview" data-theme={$settingsStore.appearanceTheme} aria-label="Appearance preview">
              <div><span></span><span></span><span></span></div>
              <strong>Preview card</strong>
              <p>Soft hierarchy, restrained glow, readable contrast, and keyboard-visible controls.</p>
            </div>
          </article>
          <article class="settings-card settings-wide">
            <div class="option-grid compact-options" role="radiogroup" aria-label="Interface density">
              {#each densityOptions as option}
                <button type="button" class:active={$settingsStore.interfaceDensity === option.value} aria-pressed={$settingsStore.interfaceDensity === option.value} onclick={() => settingsStore.setInterfaceDensity(option.value)}>
                  <strong>{option.label}</strong>
                  <span>{option.description}</span>
                </button>
              {/each}
            </div>
            <label class="checkbox-setting">
              <input type="checkbox" checked={$settingsStore.reducedMotionPreference} onchange={(event) => settingsStore.setReducedMotionPreference((event.currentTarget as HTMLInputElement).checked)} />
              <span>Prefer extra-calm motion inside new settings surfaces.</span>
            </label>
          </article>
        </section>
      {/if}

      {#if shouldShow('voice') && (!normalizedSearch || activeSection === 'voice')}
        <section class="settings-section settings-wide" aria-labelledby="voice-settings-title">
          <div class="settings-section-heading">
            <span class="setting-kicker">TTS & Voice</span>
            <h2 id="voice-settings-title">Spoken presence without VRAM surprises</h2>
            <p>TTS remains priority media. Speed and fallback choices can keep speech responsive while Orpheus-style voices stay optional.</p>
          </div>

          <article class="settings-card settings-wide voice-settings-card">
            <div class="setting-copy compact">
              <span class="setting-kicker">Playback</span>
              <h3>Voice output</h3>
              <p>Use voice playback for assistant replies, or leave text-only mode on for maximum resource headroom.</p>
            </div>
            <label class="inline-toggle">
              <input type="checkbox" checked={$settingsStore.ttsEnabled} onchange={(event) => settingsStore.setTTSEnabled((event.currentTarget as HTMLInputElement).checked)} />
              <span>{$settingsStore.ttsEnabled ? 'Voice playback enabled' : 'Text-only mode'}</span>
            </label>
            <label class="inline-toggle">
              <input type="checkbox" checked={$settingsStore.ttsAutoPlay} disabled={!$settingsStore.ttsEnabled} onchange={(event) => settingsStore.setTTSAutoPlay((event.currentTarget as HTMLInputElement).checked)} />
              <span>{$settingsStore.ttsAutoPlay ? 'Auto-play assistant speech' : 'Wait for manual play'}</span>
            </label>
            <div class="voice-settings-grid">
              <label class="range-setting"><span>Volume <strong>{Math.round($settingsStore.ttsVolume * 100)}%</strong></span><input type="range" min="0" max="1" step="0.01" value={$settingsStore.ttsVolume} disabled={!$settingsStore.ttsEnabled} oninput={(event) => settingsStore.setTTSVolume(Number((event.currentTarget as HTMLInputElement).value))} /></label>
              <label class="range-setting"><span>Speed <strong>{$settingsStore.ttsSpeed.toFixed(2)}×</strong></span><input type="range" min="0.75" max="1.35" step="0.05" value={$settingsStore.ttsSpeed} disabled={!$settingsStore.ttsEnabled} oninput={(event) => settingsStore.setTTSSpeed(Number((event.currentTarget as HTMLInputElement).value))} /></label>
            </div>
            <div class="option-grid voice-quality-grid" role="radiogroup" aria-label="TTS quality and speed preference">
              {#each ttsLatencyOptions as option}
                <button type="button" class:active={$settingsStore.ttsLatencyPreset === option.value} disabled={!$settingsStore.ttsEnabled} aria-pressed={$settingsStore.ttsLatencyPreset === option.value} onclick={() => settingsStore.setTTSLatencyPreset(option.value)}>
                  <strong>{option.label}</strong><span>{option.description}</span>
                </button>
              {/each}
            </div>
            <div class="tts-preview-card" aria-live="polite">
              <div><strong>Live speech preview</strong><span>{samplePreview}</span></div>
              <button type="button" onclick={() => (samplePreview = `Sample queued with ${$settingsStore.ttsLatencyPreset} latency, ${Math.round($settingsStore.ttsVolume * 100)}% volume, ${$settingsStore.ttsSpeed.toFixed(2)}× speed.`)}>Update sample</button>
            </div>
          </article>

          <article class="settings-card settings-wide voice-mood-section" aria-labelledby="voice-mood-title">
            <div class="setting-copy compact">
              <span class="setting-kicker">Character Mood</span>
              <h3 id="voice-mood-title">Per-character speech tuning</h3>
              <p>Fine-tune how each linked voice reacts to emotional, intimate, and high-stakes scenes. These are lightweight profile settings, not extra models.</p>
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
            <div class="clone-status" aria-live="polite">{#if voiceMoodError}<span class="error">{voiceMoodError}</span>{:else if voiceMoodStatus}<span>{voiceMoodStatus}</span>{/if}</div>
          </article>

          <article class="settings-card settings-wide clone-voice-section" aria-labelledby="clone-voice-title">
            <div class="setting-copy compact"><span class="setting-kicker">Clone Voice</span><h3 id="clone-voice-title">Zero-shot voice profile</h3><p>Record or upload a clear 6-15 second reference. Reverie stores the clip locally and only asks Orpheus to use it when speech is generated.</p></div>
            <div class="clone-voice-controls">
              <label class="text-setting"><span>Profile name</span><input type="text" bind:value={cloneName} placeholder="Tara warm close-up" maxlength="120" /></label>
              <label class="file-setting"><span>Upload reference audio</span><input type="file" accept="audio/*" onchange={handleCloneFileChange} /></label>
              <div class="recording-row">{#if isRecording}<button type="button" class="record-button active" onclick={stopRecording}>Stop recording</button>{:else}<button type="button" class="record-button" onclick={startRecording}>Record reference</button>{/if}<span>Keep it natural, quiet, and short. Piper remains available if Orpheus cannot fit in VRAM.</span></div>
              {#if cloneRecordingUrl}<audio controls src={cloneRecordingUrl} aria-label="Voice reference preview"></audio>{/if}
              <button type="button" class="create-voice-button" disabled={!cloneAudio || !cloneName.trim() || isCreatingVoice} onclick={createVoiceProfile}>{isCreatingVoice ? 'Creating voice profile…' : 'Create local voice profile'}</button>
              <div class="clone-status" aria-live="polite">{#if cloneError}<span class="error">{cloneError}</span>{:else if cloneStatus}<span>{cloneStatus}</span>{/if}</div>
            </div>
          </article>
        </section>
      {/if}

      {#if shouldShow('images') && (!normalizedSearch || activeSection === 'images')}
        <section class="settings-section settings-wide" aria-labelledby="image-settings-title">
          <div class="settings-section-heading"><span class="setting-kicker">Image Generation</span><h2 id="image-settings-title">Local scene visualization</h2><p>Generate images only when you ask by default. Auto-generation is low-priority and still lets voice/chat go first.</p></div>
          <article class="settings-card settings-wide image-settings-card">
            <label class="inline-toggle"><input type="checkbox" checked={$settingsStore.imageAutoGenerateOnAssistant} onchange={(event) => settingsStore.setImageAutoGenerateOnAssistant((event.currentTarget as HTMLInputElement).checked)} /><span>{$settingsStore.imageAutoGenerateOnAssistant ? 'Auto-generate after replies' : 'Ask before generating images'}</span></label>
            <div class="option-grid compact-options" role="radiogroup" aria-label="Default image generation preset">
              {#each imagePresetOptions as option}
                <button type="button" class:active={$settingsStore.imageDefaultPreset === option.value} aria-pressed={$settingsStore.imageDefaultPreset === option.value} onclick={() => settingsStore.setImageDefaultPreset(option.value)}><strong>{option.label}</strong><span>{option.description}</span><small>{option.impact}</small></button>
              {/each}
            </div>
            <div class="image-preset-preview" data-preset={$settingsStore.imageDefaultPreset}><div><span></span></div><strong>{activeImagePreset.label} preset preview</strong><p>{activeImagePreset.description} Backend VRAM checks can still downgrade this before ComfyUI starts.</p></div>
          </article>
        </section>
      {/if}

      {#if shouldShow('growth') && (!normalizedSearch || activeSection === 'growth')}
        <section class="settings-section settings-wide" aria-labelledby="growth-settings-title">
          <div class="settings-section-heading"><span class="setting-kicker">Growth & Self-Learning</span><h2 id="growth-settings-title">Transparent character growth</h2><p>Reflection runs outside the active response path and future training remains opt-in, auditable, and reversible.</p></div>
          <article class="settings-card settings-card-featured"><div class="setting-copy"><span class="setting-kicker">Reflection</span><h3>Self-reflection</h3><p id="self-reflection-description">Allow private review after the conversation settles. Reflection is slower growth, not constant monitoring or rewriting from one fragile moment.</p></div><label class="toggle-switch"><input type="checkbox" checked={$settingsStore.selfReflectionEnabled} onchange={(event) => settingsStore.setSelfReflectionEnabled((event.currentTarget as HTMLInputElement).checked)} aria-describedby="self-reflection-description" /><span>{$settingsStore.selfReflectionEnabled ? 'On' : 'Off'}</span></label></article>
          <article class="settings-card settings-wide"><div class="setting-copy compact"><span class="setting-kicker">Pace</span><h3>Reflection frequency</h3><p>Pick how often Reverie pauses later to understand what mattered.</p></div><div class="option-grid" role="radiogroup" aria-label="Reflection frequency">{#each reflectionFrequencyOptions as option}<button type="button" class:active={$settingsStore.reflectionFrequency === option.value} aria-pressed={$settingsStore.reflectionFrequency === option.value} onclick={() => settingsStore.setReflectionFrequency(option.value)}><strong>{option.label}</strong><span>{option.description}</span></button>{/each}</div></article>
          <article class="settings-card settings-wide"><div class="setting-copy compact"><span class="setting-kicker">Care</span><h3>Reflection sensitivity</h3><p>Choose how cautious Reverie should be before treating a moment as meaningful growth.</p></div><div class="option-grid" role="radiogroup" aria-label="Reflection sensitivity">{#each reflectionSensitivityOptions as option}<button type="button" class:active={$settingsStore.reflectionSensitivity === option.value} aria-pressed={$settingsStore.reflectionSensitivity === option.value} onclick={() => settingsStore.setReflectionSensitivity(option.value)}><strong>{option.label}</strong><span>{option.description}</span></button>{/each}</div></article>
          <article class="settings-card settings-wide"><div class="setting-copy compact"><span class="setting-kicker">Presence</span><h3>Growth notifications</h3><p>Show occasional notes when Reverie notices a meaningful shift—no dashboards, no pressure.</p></div><label class="inline-toggle"><input type="checkbox" checked={$settingsStore.growthNotificationsEnabled} onchange={(event) => settingsStore.setGrowthNotificationsEnabled((event.currentTarget as HTMLInputElement).checked)} /><span>{$settingsStore.growthNotificationsEnabled ? 'Show gentle growth notes' : 'Keep growth quiet'}</span></label></article>
        </section>
      {/if}

      {#if shouldShow('memory') && (!normalizedSearch || activeSection === 'memory')}
        <section class="settings-section settings-wide" aria-labelledby="memory-settings-title">
          <div class="settings-section-heading"><span class="setting-kicker">Memory</span><h2 id="memory-settings-title">Continuity with pruning controls</h2><p>Protect identity, explicit preferences, boundaries, and important promises while keeping context lean enough for the 8GB target.</p></div>
          <article class="settings-card settings-card-featured"><div class="setting-copy"><span class="setting-kicker">Durable recall</span><h3>Long-term memory</h3><p id="long-term-memory-description">Let Reverie keep important preferences, promises, and boundaries. Turning this off keeps the current chat intact while durable remembering pauses.</p></div><label class="toggle-switch"><input type="checkbox" checked={$settingsStore.longTermMemoryEnabled} onchange={(event) => settingsStore.setLongTermMemoryEnabled((event.currentTarget as HTMLInputElement).checked)} aria-describedby="long-term-memory-description" /><span>{$settingsStore.longTermMemoryEnabled ? 'On' : 'Off'}</span></label></article>
          <article class="settings-card settings-wide"><div class="setting-copy compact"><span class="setting-kicker">8GB awareness</span><h3>Context budget</h3><p>A simple preset for remembered context. Balanced is designed for smooth local use on the 8GB target.</p></div><div class="budget-grid" role="radiogroup" aria-label="Context budget preset">{#each contextBudgetOptions as option}<button type="button" class:active={$settingsStore.contextBudgetPreset === option.value} aria-pressed={$settingsStore.contextBudgetPreset === option.value} onclick={() => settingsStore.setContextBudgetPreset(option.value)}><span>{option.detail}</span><strong>{option.label}</strong><small>{option.description}</small></button>{/each}</div></article>
          <article class="settings-card settings-wide"><div class="setting-copy compact"><span class="setting-kicker">Pruning</span><h3>Memory pruning posture</h3><p>Pruning removes noise from retrieval; it should never silently erase user-protected facts or character identity.</p></div><div class="option-grid" role="radiogroup" aria-label="Memory pruning mode">{#each pruningOptions as option}<button type="button" class:active={$settingsStore.memoryPruningMode === option.value} aria-pressed={$settingsStore.memoryPruningMode === option.value} onclick={() => settingsStore.setMemoryPruningMode(option.value)}><strong>{option.label}</strong><span>{option.description}</span></button>{/each}</div></article>
        </section>
      {/if}

      {#if shouldShow('performance') && (!normalizedSearch || activeSection === 'performance')}
        <section class="settings-section settings-wide" aria-labelledby="performance-settings-title">
          <div class="settings-section-heading"><span class="setting-kicker">Performance & 8GB</span><h2 id="performance-settings-title">Guardrails you can understand</h2><p>Heavy media and learning work must stay queued, explain downgrades, and yield to chat/voice responsiveness.</p></div>
          <article class="settings-card settings-wide performance-settings-card">
            <div class="option-grid" role="radiogroup" aria-label="Performance preset">{#each performancePresetOptions as option}<button type="button" class:active={$settingsStore.performancePreset === option.value} aria-pressed={$settingsStore.performancePreset === option.value} onclick={() => settingsStore.setPerformancePreset(option.value)}><strong>{option.label}</strong><span>{option.description}</span><small>{option.detail}</small></button>{/each}</div>
            <label class="range-setting"><span>Background task limit <strong>{$settingsStore.backgroundTaskLimit}</strong></span><small>Caps non-interactive jobs like indexing, gallery refreshes, and media helpers so chat and voice stay responsive.</small><input type="range" min="1" max="3" step="1" value={$settingsStore.backgroundTaskLimit} onchange={(event) => settingsStore.setBackgroundTaskLimit(Number((event.currentTarget as HTMLInputElement).value))} /></label>
            <label class="checkbox-setting"><input type="checkbox" checked={$settingsStore.proactiveResourceWarnings} onchange={(event) => settingsStore.setProactiveResourceWarnings((event.currentTarget as HTMLInputElement).checked)} /><span>Show proactive VRAM warnings and auto-downgrade explanations.</span></label>
            <p class="performance-explainer">TTS always has priority. Image generation runs as one exclusive queued job, unloads idle Orpheus first, and automatically falls back toward preview quality when VRAM approaches the 8GB guardrails.</p>
          </article>
        </section>
      {/if}

      {#if shouldShow('extensibility') && (!normalizedSearch || activeSection === 'extensibility')}
        <section class="settings-section settings-wide" aria-labelledby="extension-settings-title">
          <div class="settings-section-heading"><span class="setting-kicker">Extensibility</span><h2 id="extension-settings-title">Extension settings</h2><p>Extensions can add small, typed settings here without coupling to core markup. Bad manifests stay isolated and are reported instead of crashing the app.</p></div>
          <article class="settings-card settings-wide extension-settings-card">
            <div class="extension-status" aria-live="polite">{#if extensionsLoading}<span>Loading extension contracts…</span>{:else if extensionError}<span class="error">{extensionError}</span>{:else if extensionStatus}<span>{extensionStatus}</span>{/if}</div>
            {#if visibleExtensionSections.length === 0}
              <p class="performance-explainer">No extension setting sections match this view yet.</p>
            {:else}
              <div class="extension-section-list">
                {#each visibleExtensionSections as section (`${section.extensionId}:${section.section_id}`)}
                  <section class="extension-section" aria-label={section.title}>
                    <div><span class="setting-kicker">{section.extensionName}</span><h3>{section.title}</h3>{#if section.description}<p>{section.description}</p>{/if}</div>
                    <div class="extension-field-list">
                      {#each section.fields as field (`${section.extensionId}:${section.section_id}:${field.key}`)}
                        {#if field.kind === 'boolean'}<label class="checkbox-setting"><input type="checkbox" checked={Boolean(extensionSettingValue(section.extensionId, field))} onchange={(event) => handleExtensionInput(section.extensionId, field, event)} /><span>{field.label}{field.description ? ` — ${field.description}` : ''}</span></label>
                        {:else if field.kind === 'number'}<label class="text-setting"><span>{field.label}</span>{#if field.description}<small>{field.description}</small>{/if}<input type="number" min={field.min_value ?? undefined} max={field.max_value ?? undefined} value={Number(extensionSettingValue(section.extensionId, field) ?? 0)} onchange={(event) => handleExtensionInput(section.extensionId, field, event)} /></label>
                        {:else if field.kind === 'select'}<label class="text-setting"><span>{field.label}</span>{#if field.description}<small>{field.description}</small>{/if}<select value={String(extensionSettingValue(section.extensionId, field) ?? '')} onchange={(event) => handleExtensionInput(section.extensionId, field, event)}>{#each field.options as option}<option value={option}>{option}</option>{/each}</select></label>
                        {:else}<label class="text-setting"><span>{field.label}</span>{#if field.description}<small>{field.description}</small>{/if}<input type="text" value={String(extensionSettingValue(section.extensionId, field) ?? '')} maxlength="500" onchange={(event) => handleExtensionInput(section.extensionId, field, event)} /></label>{/if}
                      {/each}
                    </div>
                  </section>
                {/each}
              </div>
            {/if}
          </article>
        </section>
      {/if}

      {#if shouldShow('backup') && (!normalizedSearch || activeSection === 'backup')}
        <section class="settings-section settings-wide" aria-labelledby="backup-settings-title">
          <div class="settings-section-heading"><span class="setting-kicker">Import / Export / Backup</span><h2 id="backup-settings-title">Your data stays portable</h2><p>Use lightweight JSON exports for the current control hub and local UI state. Connected backend exports can later plug into the same hub actions.</p></div>
          <article class="settings-card settings-wide backup-card">
            <div class="backup-grid">
              {#each backupScopeOptions as option}
                <button type="button" onclick={() => exportBackup(option.scope)}><strong>Export {option.label}</strong><span>{option.description}.</span></button>
              {/each}
            </div>
            <div class="backup-actions">
              <button type="button" class="hub-secondary-action" onclick={() => importFileInput?.click()}>Import backup</button>
              <button type="button" class="hub-danger-action" onclick={resetWithConfirmation}>Reset to defaults</button>
              <input bind:this={importFileInput} class="visually-hidden" type="file" accept="application/json,.json" onchange={importBackup} />
            </div>
            <div class="backup-status-card" aria-live="polite">{#if backupError}<span class="error">{backupError}</span>{:else if backupStatus}<span>{backupStatus}</span>{:else}<span>Exports are plain JSON files. Import only backups you trust from your own device.</span>{/if}</div>
          </article>
        </section>
      {/if}

      <aside class="settings-trust-note settings-wide" aria-label="Settings trust note">
        <span aria-hidden="true">✦</span>
        <div><strong>You stay in control.</strong><p>Settings are grouped for trust: core memory/growth choices stay explicit, 8GB impact is explained before quality increases, and extensions render only through bounded declarative sections.</p></div>
        <button type="button" onclick={resetWithConfirmation}>Restore calm defaults</button>
      </aside>
    </div>
  </div>
</section>
