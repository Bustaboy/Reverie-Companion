<script lang="ts">
  import { onMount } from 'svelte';
  import { growthStore, personalLoRAReviewView } from '$lib/stores/growthStore';
  import type { LoRATrainingExample, LoRATrainingJob, LoRATrainingStatus } from '$lib/types/growth';

  const isLoading = $derived($growthStore.loadState === 'loading');
  const isRefreshing = $derived($growthStore.loadState === 'refreshing');
  const isBusy = $derived($growthStore.actionState !== 'idle');

  onMount(() => {
    void growthStore.loadPersonalLoRA();
  });

  const refreshTraining = () => {
    void growthStore.refresh();
  };

  const setCollectionOptIn = (event: Event) => {
    void growthStore.updateSettings({ collection_opt_in: (event.currentTarget as HTMLInputElement).checked });
  };

  const setTrainingOptIn = (event: Event) => {
    void growthStore.updateSettings({ training_opt_in: (event.currentTarget as HTMLInputElement).checked });
  };

  const approveExample = (itemId: string) => {
    void growthStore.approveExample(itemId);
  };

  const rejectExample = (itemId: string) => {
    void growthStore.rejectExample(itemId);
  };

  const deleteExample = (itemId: string) => {
    void growthStore.deleteExample(itemId);
  };

  const startTraining = () => {
    if (!$personalLoRAReviewView.canStartTraining) return;
    void growthStore.startTraining();
  };

  const formatDate = (value: string | null | undefined) => {
    if (!value) return 'Not yet';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Not yet';

    return new Intl.DateTimeFormat(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    }).format(date);
  };

  const percent = (value: number | undefined) => {
    const bounded = Math.min(Math.max(value ?? 0, 0), 1);
    return `${Math.round(bounded * 100)}%`;
  };

  const labelFor = (value: string | undefined) =>
    (value ?? 'unknown')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());

  const exampleSummary = (example: LoRATrainingExample) =>
    example.purpose || example.text || 'A reviewed reflection candidate is waiting for your choice.';

  const jobStatusLabel = (job: LoRATrainingJob | null) => {
    if (!job) return 'Idle';
    if (job.status === 'completed') return 'Ready';
    return labelFor(job.status);
  };

  const adapterStatus = (job: LoRATrainingJob | null) => {
    if ($growthStore.settings?.active_adapter_id) return 'Enabled';
    if (job?.status === 'completed') return 'Trained, not enabled';
    return 'Disabled';
  };

  const lastTrained = (job: LoRATrainingJob | null) => {
    if (!job || job.status !== 'completed') return 'Not trained yet';
    return formatDate(job.completed_at);
  };

  const progressWidth = (job: LoRATrainingJob | null) => {
    const bounded = Math.min(Math.max(job?.progress ?? 0, 0), 1);
    return `${Math.max(6, Math.round(bounded * 100))}%`;
  };

  const startDisabledReason = $derived.by(() => {
    if ($personalLoRAReviewView.trainingActive) return 'Training is already running.';
    if ($growthStore.actionState !== 'idle') return 'Please wait for the current action to finish.';
    if (!$personalLoRAReviewView.trainingOptedIn) return 'Turn on training opt-in before starting.';
    if ($personalLoRAReviewView.approvedExamples.length === 0) return 'Approve at least one candidate before training.';
    return '';
  });

  const statusTone = (status: LoRATrainingStatus | undefined) => {
    if (status === 'failed') return 'danger';
    if (status === 'completed') return 'ready';
    if (status === 'running' || status === 'queued') return 'working';
    return 'quiet';
  };
</script>

<section class="training-panel" aria-labelledby="training-title">
  <header class="training-hero">
    <div>
      <p class="eyebrow">Personal growth</p>
      <h1 id="training-title">Training, only with your say</h1>
      <p class="subtitle">
        Review the reflections Reverie thinks may help her learn your style. Nothing here is used for personal LoRA training until you approve it and opt in.
      </p>
    </div>
    <button class="ghost-button" type="button" onclick={refreshTraining} disabled={isLoading || isRefreshing || isBusy}>
      {isRefreshing ? 'Refreshing…' : 'Refresh'}
    </button>
  </header>

  {#if $growthStore.error}
    <div class="training-notice" role="status">
      <strong>The training panel needs a moment.</strong>
      <span>{$growthStore.error}</span>
    </div>
  {/if}

  {#if isLoading}
    <div class="training-empty" aria-live="polite">
      <div class="training-empty-mark">✦</div>
      <h2>Opening growth controls…</h2>
      <p>Reverie is checking the local review queue and adapter status.</p>
    </div>
  {:else}
    <div class="training-content">
      <section class="training-overview" aria-label="Personal LoRA status">
        <article class="training-card status-card">
          <div>
            <span class="setting-kicker">Current LoRA</span>
            <h2>{adapterStatus($growthStore.currentJob)}</h2>
            <p>
              {$personalLoRAReviewView.trainingOptedIn
                ? 'Personal training is allowed after you approve examples.'
                : 'Training is paused until you explicitly opt in.'}
            </p>
          </div>
          <div class="lora-status-grid">
            <div>
              <span>Last trained</span>
              <strong>{lastTrained($growthStore.currentJob)}</strong>
            </div>
            <div>
              <span>Training status</span>
              <strong>{jobStatusLabel($growthStore.currentJob)}</strong>
            </div>
            <div>
              <span>Approved examples</span>
              <strong>{$personalLoRAReviewView.approvedExamples.length}</strong>
            </div>
            <div>
              <span>Needs review</span>
              <strong>{$growthStore.counts.pending_review}</strong>
            </div>
          </div>
        </article>

        <article class="training-card trust-card">
          <span aria-hidden="true">♡</span>
          <div>
            <h2>Your data stays yours</h2>
            <p>
              Reverie keeps this local and conservative: deleted or rejected candidates are not used, review stays required, and only approved examples can enter a training run.
            </p>
          </div>
        </article>

        <article class="training-card controls-card">
          <div class="setting-copy compact">
            <span class="setting-kicker">Consent</span>
            <h2>Opt-in controls</h2>
            <p>Collection finds possible examples. Training is a separate choice.</p>
          </div>
          <label class="inline-toggle">
            <input type="checkbox" checked={$personalLoRAReviewView.collectionOptedIn} onchange={setCollectionOptIn} />
            <span>{$personalLoRAReviewView.collectionOptedIn ? 'Collect review candidates' : 'Do not collect candidates'}</span>
          </label>
          <label class="inline-toggle">
            <input type="checkbox" checked={$personalLoRAReviewView.trainingOptedIn} onchange={setTrainingOptIn} />
            <span>{$personalLoRAReviewView.trainingOptedIn ? 'Allow approved examples to train' : 'Training opt-in is off'}</span>
          </label>
          <p class="training-small-note">
            {$personalLoRAReviewView.reviewRequired ? 'Review is required before training.' : 'Review is currently optional in settings, but this panel still uses approved examples only.'}
          </p>
        </article>

        <article class="training-card start-card">
          <div>
            <span class="setting-kicker">Start</span>
            <h2>A simple training run</h2>
            <p>
              Starts the basic local training controller with approved examples only. Detailed progress and advanced parameters are intentionally left out for now.
            </p>
          </div>
          {#if $personalLoRAReviewView.trainingActive}
            <div class="training-progress" aria-label="Training progress">
              <div>
                <span class="status-dot {statusTone($growthStore.currentJob?.status)}"></span>
                <strong>{$growthStore.currentJob?.message ?? 'Training is underway…'}</strong>
              </div>
              <div class="progress-track"><span style={`width: ${progressWidth($growthStore.currentJob)}`}></span></div>
            </div>
          {:else if $growthStore.currentJob?.status === 'failed'}
            <p class="training-warning">{$growthStore.currentJob.error ?? 'The last training run did not finish.'}</p>
          {:else}
            <p class="training-small-note">
              {startDisabledReason || `Ready when you are: ${$personalLoRAReviewView.approvedExamples.length} approved examples available.`}
            </p>
          {/if}
          <button class="primary-training-button" type="button" onclick={startTraining} disabled={!$personalLoRAReviewView.canStartTraining}>
            {$growthStore.actionState === 'training' ? 'Starting…' : 'Start Training'}
          </button>
        </article>
      </section>

      <section class="candidate-section" aria-labelledby="candidate-heading">
        <div class="candidate-section-header">
          <div>
            <p class="eyebrow">Review queue</p>
            <h2 id="candidate-heading">Pending training candidates</h2>
          </div>
          <span>{$personalLoRAReviewView.pendingExamples.length} waiting · {$personalLoRAReviewView.approvedExamples.length} approved</span>
        </div>

        {#if $personalLoRAReviewView.pendingExamples.length === 0}
          <div class="training-empty compact-empty">
            <div class="training-empty-mark">✓</div>
            <h3>No pending candidates</h3>
            <p>When reflections qualify for training review, they will appear here before anything can be used.</p>
          </div>
        {:else}
          <div class="candidate-list">
            {#each $personalLoRAReviewView.pendingExamples as example (example.item_id)}
              <article class="candidate-card">
                <div class="candidate-main">
                  <div class="candidate-topline">
                    <span>Source reflection · {formatDate(example.created_at)}</span>
                    <strong>{percent(example.confidence)} confidence</strong>
                  </div>
                  <h3>{exampleSummary(example)}</h3>
                  {#if example.text && example.text !== example.purpose}
                    <p>{example.text}</p>
                  {/if}
                  <div class="candidate-meta">
                    <span>{example.evidence_count ?? 0} evidence notes</span>
                    {#if example.source_journal_id}<span>Journal link saved</span>{/if}
                    {#if example.sensitivity_tags?.length}<span>Sensitive: {example.sensitivity_tags.map(labelFor).join(', ')}</span>{/if}
                  </div>
                  {#if example.themes?.length}
                    <div class="training-tags" aria-label="Key themes">
                      {#each example.themes as theme}
                        <span>{labelFor(theme)}</span>
                      {/each}
                    </div>
                  {/if}
                </div>
                <div class="candidate-actions" aria-label="Candidate actions">
                  <button type="button" class="approve" onclick={() => approveExample(example.item_id)} disabled={isBusy}>
                    Approve
                  </button>
                  <button type="button" onclick={() => rejectExample(example.item_id)} disabled={isBusy}>Reject</button>
                  <button type="button" class="danger" onclick={() => deleteExample(example.item_id)} disabled={isBusy}>
                    Delete
                  </button>
                </div>
              </article>
            {/each}
          </div>
        {/if}
      </section>

      {#if $personalLoRAReviewView.recentlyReviewedExamples.length > 0}
        <section class="reviewed-strip" aria-label="Recently rejected examples">
          <strong>Recently kept out of training</strong>
          {#each $personalLoRAReviewView.recentlyReviewedExamples as example (example.item_id)}
            <span>{exampleSummary(example)}</span>
          {/each}
        </section>
      {/if}
    </div>
  {/if}
</section>
