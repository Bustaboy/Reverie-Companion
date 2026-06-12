<script lang="ts">
  import { voiceService, VoiceServiceError } from '$lib/api/voiceService';
  import { settingsStore, type ContextBudgetPreset, type ReflectionFrequency, type ReflectionSensitivity, type TTSLatencyPreset } from '$lib/stores/settingsStore';

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
  let cloneCharacterId = $state('');
  let referenceFile = $state<File | null>(null);
  let recordedBlob = $state<Blob | null>(null);
  let recordingStartedAt = 0;
  let recordedDurationSeconds = $state<number | null>(null);
  let mediaRecorder = $state<MediaRecorder | null>(null);
  let cloneBusy = $state(false);
  let cloneStatus = $state('Record or upload 6–15 seconds of clear speech. Stored locally.');
  let cloneError = $state<string | null>(null);
  let recordingChunks: BlobPart[] = [];

  const selectedReferenceLabel = $derived.by(() => {
    if (recordedBlob) {
      return `Recording ready${recordedDurationSeconds ? ` · ${recordedDurationSeconds.toFixed(1)}s` : ''}`;
    }
    if (referenceFile) {
      return `${referenceFile.name} · ${(referenceFile.size / (1024 * 1024)).toFixed(2)} MB`;
    }
    return 'No reference audio selected yet.';
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

  const handleTTSVolumeChange = (event: Event) => {
    settingsStore.setTTSVolume(Number((event.currentTarget as HTMLInputElement).value));
  };

  const handleTTSSpeedChange = (event: Event) => {
    settingsStore.setTTSSpeed(Number((event.currentTarget as HTMLInputElement).value));
  };

  const handleReferenceUpload = (event: Event) => {
    const input = event.currentTarget as HTMLInputElement;
    referenceFile = input.files?.[0] ?? null;
    recordedBlob = null;
    recordedDurationSeconds = null;
    cloneError = null;
    cloneStatus = referenceFile ? 'Reference audio selected. Create a profile when ready.' : 'Record or upload 6–15 seconds of clear speech.';
  };

  const startVoiceRecording = async () => {
    cloneError = null;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      cloneError = 'This browser cannot record audio here. Upload a short WAV, WebM, OGG, or MP3 instead.';
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordingChunks = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) recordingChunks.push(event.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        recordedDurationSeconds = (Date.now() - recordingStartedAt) / 1000;
        recordedBlob = new Blob(recordingChunks, { type: recorder.mimeType || 'audio/webm' });
        referenceFile = null;
        mediaRecorder = null;
        cloneStatus = 'Recording captured. Create a voice profile when ready.';
      };
      mediaRecorder = recorder;
      recordingStartedAt = Date.now();
      recorder.start();
      cloneStatus = 'Recording… aim for 6–15 seconds of natural speech.';
    } catch (error) {
      cloneError = error instanceof Error ? error.message : 'Microphone access was not available.';
    }
  };

  const stopVoiceRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
  };

  const createVoiceProfile = async () => {
    cloneError = null;
    const audio = recordedBlob ?? referenceFile;
    if (!audio) {
      cloneError = 'Add a short reference recording first.';
      return;
    }
    if (!cloneName.trim()) {
      cloneError = 'Name the voice profile before saving it.';
      return;
    }
    if (recordedDurationSeconds !== null && (recordedDurationSeconds < 6 || recordedDurationSeconds > 15)) {
      cloneError = 'Please keep recordings between 6 and 15 seconds for clean zero-shot cloning.';
      return;
    }

    cloneBusy = true;
    cloneStatus = 'Saving reference audio locally…';
    try {
      const audio_base64 = await blobToBase64(audio);
      const response = await voiceService.createClone({
        name: cloneName.trim(),
        character_id: cloneCharacterId.trim() || undefined,
        mime_type: audio.type || 'audio/wav',
        duration_seconds: recordedDurationSeconds ?? undefined,
        audio_base64
      });
      cloneStatus = `${response.profile.name} is ready for local Orpheus zero-shot playback.`;
      cloneName = '';
      cloneCharacterId = '';
      referenceFile = null;
      recordedBlob = null;
      recordedDurationSeconds = null;
    } catch (error) {
      cloneError = error instanceof VoiceServiceError ? error.message : 'Voice profile could not be created.';
      cloneStatus = 'Reference audio is still on this device; try again when ready.';
    } finally {
      cloneBusy = false;
    }
  };

  const blobToBase64 = (blob: Blob): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(reader.error);
      reader.onload = () => {
        const result = typeof reader.result === 'string' ? reader.result : '';
        resolve(result.includes(',') ? result.split(',')[1] : result);
      };
      reader.readAsDataURL(blob);
    });
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

      <section class="voice-clone-section" aria-labelledby="voice-clone-title">
        <div class="setting-copy compact">
          <span class="setting-kicker">Clone Voice</span>
          <h3 id="voice-clone-title">Zero-shot voice profile</h3>
          <p>Record or upload a 6–15 second reference. Reverie stores it locally and passes it to Orpheus only when that profile speaks.</p>
        </div>

        <div class="voice-clone-grid">
          <label class="range-setting voice-clone-field">
            <span>Profile name</span>
            <input type="text" bind:value={cloneName} placeholder="Tara warm reference" disabled={cloneBusy} />
          </label>
          <label class="range-setting voice-clone-field">
            <span>Character ID <small>(optional)</small></span>
            <input type="text" bind:value={cloneCharacterId} placeholder="tara" disabled={cloneBusy} />
          </label>
        </div>

        <div class="voice-reference-card">
          <div>
            <strong>{selectedReferenceLabel}</strong>
            <p aria-live="polite">{cloneError ?? cloneStatus}</p>
          </div>
          <div class="voice-reference-actions">
            {#if mediaRecorder}
              <button type="button" class="secondary-button recording" onclick={stopVoiceRecording}>Stop recording</button>
            {:else}
              <button type="button" class="secondary-button" disabled={cloneBusy} onclick={startVoiceRecording}>Record 6–15s</button>
            {/if}
            <label class="secondary-button upload-button">
              Upload audio
              <input type="file" accept="audio/wav,audio/x-wav,audio/webm,audio/ogg,audio/mpeg,audio/mp3" disabled={cloneBusy || Boolean(mediaRecorder)} onchange={handleReferenceUpload} />
            </label>
          </div>
        </div>

        <button type="button" class="primary-voice-action" disabled={cloneBusy || Boolean(mediaRecorder)} onclick={createVoiceProfile}>
          {cloneBusy ? 'Creating voice profile…' : 'Create Voice Profile from Recording'}
        </button>
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
