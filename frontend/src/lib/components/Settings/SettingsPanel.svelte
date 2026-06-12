<script lang="ts">
  import { onMount } from 'svelte';
  import { settingsStore, type ContextBudgetPreset, type ReflectionFrequency, type ReflectionSensitivity, type TTSLatencyPreset } from '$lib/stores/settingsStore';
  import { voiceService, type VoiceMoodSettings, type VoiceProfile } from '$lib/api/voiceService';

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
  let selectedMoodVoiceId = $state('');
  let isLoadingVoices = $state(false);
  let isSavingMood = $state(false);
  let moodStatus = $state<string | null>(null);
  let moodError = $state<string | null>(null);
  let draftMood = $state<VoiceMoodSettings>({
    baseline_expressiveness: 1,
    emotional_sensitivity: 1,
    nsfw_intensity: 1
  });

  const cloneAudio = $derived(cloneRecording ?? cloneFile);
  const characterVoiceProfiles = $derived(voiceProfiles.filter((profile) => profile.type === 'character'));
  const selectedMoodVoice = $derived(voiceProfiles.find((profile) => profile.voice_id === selectedMoodVoiceId) ?? null);

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

  const handleTTSVolumeChange = (event: Event) => {
    settingsStore.setTTSVolume(Number((event.currentTarget as HTMLInputElement).value));
  };

  const handleTTSSpeedChange = (event: Event) => {
    settingsStore.setTTSSpeed(Number((event.currentTarget as HTMLInputElement).value));
  };

  const clampMood = (value: number) => Math.min(2, Math.max(0, Number.isFinite(value) ? value : 1));

  const moodForProfile = (profile: VoiceProfile | null): VoiceMoodSettings => ({
    baseline_expressiveness: clampMood(profile?.mood_settings?.baseline_expressiveness ?? 1),
    emotional_sensitivity: clampMood(profile?.mood_settings?.emotional_sensitivity ?? 1),
    nsfw_intensity: clampMood(profile?.mood_settings?.nsfw_intensity ?? 1)
  });

  const loadVoiceProfiles = async () => {
    isLoadingVoices = true;
    moodError = null;
    try {
      const profiles = await voiceService.listVoices();
      const characterProfiles = profiles.filter((profile) => profile.type === 'character');
      voiceProfiles = profiles;
      if (!selectedMoodVoiceId && characterProfiles.length > 0) {
        selectedMoodVoiceId = characterProfiles[0].voice_id;
        draftMood = moodForProfile(characterProfiles[0]);
      }
    } catch (error) {
      moodError = error instanceof Error ? error.message : 'Could not load local voice profiles.';
    } finally {
      isLoadingVoices = false;
    }
  };

  const selectMoodVoice = (event: Event) => {
    selectedMoodVoiceId = (event.currentTarget as HTMLSelectElement).value;
    draftMood = moodForProfile(voiceProfiles.find((profile) => profile.voice_id === selectedMoodVoiceId) ?? null);
    moodStatus = null;
    moodError = null;
  };

  const handleMoodChange = (key: keyof VoiceMoodSettings, event: Event) => {
    draftMood = { ...draftMood, [key]: clampMood(Number((event.currentTarget as HTMLInputElement).value)) };
    moodStatus = null;
  };

  const saveMoodSettings = async () => {
    if (!selectedMoodVoice) {
      moodError = 'Create or select a character voice profile first.';
      return;
    }

    isSavingMood = true;
    moodError = null;
    moodStatus = 'Saving character mood locally…';
    try {
      const updated = await voiceService.updateVoiceProfile(selectedMoodVoice.voice_id, { mood_settings: draftMood });
      voiceProfiles = voiceProfiles.map((profile) => (profile.voice_id === updated.voice_id ? updated : profile));
      draftMood = moodForProfile(updated);
      moodStatus = `${updated.name} mood controls are linked to EmotionEngine and TTS routing.`;
    } catch (error) {
      moodError = error instanceof Error ? error.message : 'Could not save mood settings.';
      moodStatus = null;
    } finally {
      isSavingMood = false;
    }
  };

  onMount(() => {
    void loadVoiceProfiles();
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
      voiceProfiles = [...voiceProfiles.filter((profile) => profile.voice_id !== clonedProfile?.voice_id), clonedProfile];
      selectedMoodVoiceId = clonedProfile.voice_id;
      draftMood = moodForProfile(clonedProfile);
      cloneStatus = `Created ${clonedProfile.name}. It will use Orpheus zero-shot cloning when speech is generated.`;
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
          <span class="setting-kicker">Mood</span>
          <h3 id="voice-mood-title">Per-character voice mood</h3>
          <p>Fine-tune how strongly this character reacts to memory, growth cues, high-emotion turns, and intimate scenes. Defaults stay balanced and 8GB-friendly.</p>
        </div>

        <div class="voice-mood-controls">
          <label class="text-setting">
            <span>Character voice profile</span>
            <select disabled={isLoadingVoices || characterVoiceProfiles.length === 0} value={selectedMoodVoiceId} onchange={selectMoodVoice}>
              {#if characterVoiceProfiles.length === 0}
                <option value="">No character voice profiles yet</option>
              {:else}
                {#each characterVoiceProfiles as profile}
                  <option value={profile.voice_id}>{profile.name}</option>
                {/each}
              {/if}
            </select>
          </label>

          <div class="mood-slider-grid">
            <label class="range-setting">
              <span>Baseline Expressiveness <strong>{draftMood.baseline_expressiveness.toFixed(2)}×</strong></span>
              <input type="range" min="0" max="2" step="0.05" value={draftMood.baseline_expressiveness} disabled={!selectedMoodVoice || isSavingMood} oninput={(event) => handleMoodChange('baseline_expressiveness', event)} />
            </label>

            <label class="range-setting">
              <span>Emotional Sensitivity <strong>{draftMood.emotional_sensitivity.toFixed(2)}×</strong></span>
              <input type="range" min="0" max="2" step="0.05" value={draftMood.emotional_sensitivity} disabled={!selectedMoodVoice || isSavingMood} oninput={(event) => handleMoodChange('emotional_sensitivity', event)} />
            </label>

            <label class="range-setting">
              <span>NSFW Intensity <strong>{draftMood.nsfw_intensity.toFixed(2)}×</strong></span>
              <input type="range" min="0" max="2" step="0.05" value={draftMood.nsfw_intensity} disabled={!selectedMoodVoice || isSavingMood} oninput={(event) => handleMoodChange('nsfw_intensity', event)} />
            </label>
          </div>

          <div class="mood-actions">
            <button type="button" class="create-voice-button" disabled={!selectedMoodVoice || isSavingMood} onclick={saveMoodSettings}>
              {isSavingMood ? 'Saving mood…' : 'Save Mood to Voice Profile'}
            </button>
            <button type="button" class="record-button" disabled={isLoadingVoices} onclick={loadVoiceProfiles}>Refresh profiles</button>
          </div>

          <div class="clone-status" aria-live="polite">
            {#if moodError}
              <span class="error">{moodError}</span>
            {:else if moodStatus}
              <span>{moodStatus}</span>
            {/if}
          </div>
        </div>
      </section>

      <section class="clone-voice-section" aria-labelledby="clone-voice-title">
        <div class="setting-copy compact">
          <span class="setting-kicker">Clone Voice</span>
          <h3 id="clone-voice-title">Zero-shot voice profile</h3>
          <p>Record or upload a clear 6-15 second reference. Reverie stores the clip locally and only asks Orpheus to use it when speech is generated.</p>
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
            <span>Keep it natural, quiet, and short.</span>
          </div>

          {#if cloneRecordingUrl}
            <audio controls src={cloneRecordingUrl} aria-label="Voice reference preview"></audio>
          {/if}

          <button type="button" class="create-voice-button" disabled={!cloneAudio || !cloneName.trim() || isCreatingVoice} onclick={createVoiceProfile}>
            {isCreatingVoice ? 'Creating voice profile…' : 'Create Voice Profile from Recording'}
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
