<script lang="ts">
  import { onMount } from 'svelte';
  import { settingsStore, type ContextBudgetPreset, type ReflectionFrequency, type ReflectionSensitivity, type TTSLatencyPreset, type ImageDefaultPreset } from '$lib/stores/settingsStore';
  import { voiceService, type VoiceProfile, type VoiceMoodSettings } from '$lib/api/voiceService';

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

  const imagePresetOptions: Array<{
    value: ImageDefaultPreset;
    label: string;
    description: string;
  }> = [
    { value: 'preview_8gb', label: 'Preview', description: 'Fastest and safest default for 8GB laptops.' },
    { value: 'balanced_8gb', label: 'Balanced', description: 'Higher detail when VRAM is available; falls back safely.' },
    { value: 'high_8gb', label: 'High', description: 'Best local detail, still queued and 8GB-gated.' }
  ];

  const ttsLatencyOptions: Array<{
    value: TTSLatencyPreset;
    label: string;
    description: string;
  }> = [
    {
      value: 'quality',
      label: 'Quality',
      description: 'Prefer Orpheus-style expressiveness when the machine has room.'
    },
    {
      value: 'balanced',
      label: 'Balanced',
      description: 'Recommended for 8GB: expressive enough without aggressive preloading.'
    },
    {
      value: 'speed',
      label: 'Speed',
      description: 'Favor quick fallback voices and interruption-friendly playback.'
    }
  ];

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

  const cloneAudio = $derived(cloneRecording ?? cloneFile);

  const defaultMoodSettings = (): VoiceMoodSettings => ({
    baseline_expressiveness: 1,
    emotional_sensitivity: 1,
    nsfw_intensity: 1
  });

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

  onMount(() => {
    void loadVoiceProfiles();
    return () => {
      if (cloneRecordingUrl) URL.revokeObjectURL(cloneRecordingUrl);
    };
  });

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

  const handleTTSEnabledChange = (event: Event) => {
    settingsStore.setTTSEnabled((event.currentTarget as HTMLInputElement).checked);
  };

  const handleTTSAutoPlayChange = (event: Event) => {
    settingsStore.setTTSAutoPlay((event.currentTarget as HTMLInputElement).checked);
  };

  const handleImageAutoGenerateChange = (event: Event) => {
    settingsStore.setImageAutoGenerateOnAssistant((event.currentTarget as HTMLInputElement).checked);
  };

  const handleImageDefaultPresetChange = (preset: ImageDefaultPreset) => {
    settingsStore.setImageDefaultPreset(preset);
  };

  const handleTTSVolumeChange = (event: Event) => {
    settingsStore.setTTSVolume(Number((event.currentTarget as HTMLInputElement).value));
  };

  const handleTTSSpeedChange = (event: Event) => {
    settingsStore.setTTSSpeed(Number((event.currentTarget as HTMLInputElement).value));
  };

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

    <article class="settings-card settings-wide image-settings-card">
      <div class="setting-copy compact">
        <span class="setting-kicker">Images</span>
        <h2>Local scene visualization</h2>
        <p>Generate images only when you ask by default. Optional auto-generation queues low-priority preview images after assistant replies and still lets voice/chat go first.</p>
      </div>
      <label class="inline-toggle">
        <input
          type="checkbox"
          checked={$settingsStore.imageAutoGenerateOnAssistant}
          onchange={handleImageAutoGenerateChange}
        />
        <span>{ $settingsStore.imageAutoGenerateOnAssistant ? 'Auto-generate after replies' : 'Ask before generating images' }</span>
      </label>
      <div class="option-grid compact-options" role="radiogroup" aria-label="Default image generation preset">
        {#each imagePresetOptions as option}
          <button
            type="button"
            class:active={$settingsStore.imageDefaultPreset === option.value}
            aria-pressed={$settingsStore.imageDefaultPreset === option.value}
            onclick={() => handleImageDefaultPresetChange(option.value)}
          >
            <strong>{option.label}</strong>
            <span>{option.description}</span>
          </button>
        {/each}
      </div>
    </article>

    <article class="settings-card settings-wide voice-settings-card">
      <div class="setting-copy compact">
        <span class="setting-kicker">Voice</span>
        <h2>Text-to-speech playback</h2>
        <p>Keep speech local, interruptible, and light on memory. Reverie only generates one short audio line at a time.</p>
      </div>

      <div class="voice-settings-grid">
        <label class="inline-toggle">
          <input type="checkbox" checked={$settingsStore.ttsEnabled} onchange={handleTTSEnabledChange} />
          <span>{ $settingsStore.ttsEnabled ? 'Voice enabled' : 'Voice disabled' }</span>
        </label>

        <label class="inline-toggle">
          <input
            type="checkbox"
            checked={$settingsStore.ttsAutoPlay}
            disabled={!$settingsStore.ttsEnabled}
            onchange={handleTTSAutoPlayChange}
          />
          <span>{ $settingsStore.ttsAutoPlay ? 'Auto-play new replies' : 'Manual playback only' }</span>
        </label>

        <label class="range-setting">
          <span>Volume <strong>{Math.round($settingsStore.ttsVolume * 100)}%</strong></span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={$settingsStore.ttsVolume}
            disabled={!$settingsStore.ttsEnabled}
            oninput={handleTTSVolumeChange}
          />
        </label>

        <label class="range-setting">
          <span>Speed <strong>{$settingsStore.ttsSpeed.toFixed(2)}×</strong></span>
          <input
            type="range"
            min="0.75"
            max="1.35"
            step="0.05"
            value={$settingsStore.ttsSpeed}
            disabled={!$settingsStore.ttsEnabled}
            oninput={handleTTSSpeedChange}
          />
        </label>
      </div>

      <div class="option-grid voice-quality-grid" role="radiogroup" aria-label="TTS quality and speed preference">
        {#each ttsLatencyOptions as option}
          <button
            type="button"
            class:active={$settingsStore.ttsLatencyPreset === option.value}
            disabled={!$settingsStore.ttsEnabled}
            aria-pressed={$settingsStore.ttsLatencyPreset === option.value}
            onclick={() => settingsStore.setTTSLatencyPreset(option.value)}
          >
            <strong>{option.label}</strong>
            <span>{option.description}</span>
          </button>
        {/each}
      </div>

      <section class="voice-mood-section" aria-labelledby="voice-mood-title">
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
                <div class="voice-mood-header">
                  <div>
                    <strong>{profile.name}</strong>
                    <span>{profile.type === 'character' ? 'Character voice' : 'Narrator'} · {profile.voice_id}</span>
                  </div>
                  {#if savingMoodVoiceId === profile.voice_id}
                    <small>Saving…</small>
                  {/if}
                </div>

                <label class="range-setting mood-range">
                  <span>Baseline expressiveness <strong>{moodFor(profile).baseline_expressiveness.toFixed(2)}×</strong></span>
                  <small>How animated this voice feels before scene emotion is added.</small>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.05"
                    value={moodFor(profile).baseline_expressiveness}
                    onchange={(event) => updateMoodSetting(profile, 'baseline_expressiveness', Number((event.currentTarget as HTMLInputElement).value))}
                  />
                </label>

                <label class="range-setting mood-range">
                  <span>Emotional sensitivity <strong>{moodFor(profile).emotional_sensitivity.toFixed(2)}×</strong></span>
                  <small>How quickly memories, comfort, tension, and affection color delivery.</small>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.05"
                    value={moodFor(profile).emotional_sensitivity}
                    onchange={(event) => updateMoodSetting(profile, 'emotional_sensitivity', Number((event.currentTarget as HTMLInputElement).value))}
                  />
                </label>

                <label class="range-setting mood-range">
                  <span>NSFW intensity <strong>{moodFor(profile).nsfw_intensity.toFixed(2)}×</strong></span>
                  <small>How strongly intimate scene cues affect speech tags.</small>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.05"
                    value={moodFor(profile).nsfw_intensity}
                    onchange={(event) => updateMoodSetting(profile, 'nsfw_intensity', Number((event.currentTarget as HTMLInputElement).value))}
                  />
                </label>
              </article>
            {/each}
          {/if}
        </div>

        <div class="clone-status" aria-live="polite">
          {#if voiceMoodError}
            <span class="error">{voiceMoodError}</span>
          {:else if voiceMoodStatus}
            <span>{voiceMoodStatus}</span>
          {/if}
        </div>
      </section>

      <section class="clone-voice-section" aria-labelledby="clone-voice-title">
        <div class="setting-copy compact">
          <span class="setting-kicker">Clone Voice</span>
          <h3 id="clone-voice-title">Zero-shot voice profile</h3>
          <p>Record or upload a clear 6-15 second reference. Reverie stores the clip locally, links it to the same mood controls above, and only asks Orpheus to use it when speech is generated.</p>
        </div>

        <div class="clone-voice-controls">
          <label class="text-setting">
            <span>Profile name</span>
            <input type="text" bind:value={cloneName} placeholder="Tara warm close-up" maxlength="120" />
          </label>

          <label class="file-setting">
            <span>Upload reference audio</span>
            <input type="file" accept="audio/*" onchange={handleCloneFileChange} />
          </label>

          <div class="recording-row">
            {#if isRecording}
              <button type="button" class="record-button active" onclick={stopRecording}>Stop recording</button>
            {:else}
              <button type="button" class="record-button" onclick={startRecording}>Record reference</button>
            {/if}
            <span>Keep it natural, quiet, and short. Piper still remains available if Orpheus cannot fit in VRAM.</span>
          </div>

          {#if cloneRecordingUrl}
            <audio controls src={cloneRecordingUrl} aria-label="Voice reference preview"></audio>
          {/if}

          <button type="button" class="create-voice-button" disabled={!cloneAudio || !cloneName.trim() || isCreatingVoice} onclick={createVoiceProfile}>
            {isCreatingVoice ? 'Creating voice profile…' : 'Create local voice profile'}
          </button>

          <div class="clone-status" aria-live="polite">
            {#if cloneError}
              <span class="error">{cloneError}</span>
            {:else if cloneStatus}
              <span>{cloneStatus}</span>
            {/if}
          </div>
        </div>
      </section>
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
