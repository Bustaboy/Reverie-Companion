<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { growthStore } from '$lib/stores/growthStore';
  import { journalStore } from '$lib/stores/journalStore';
  import type { PersonalLoRAExample, PersonalLoRAJob } from '$lib/types/growth';

  let trainingConsentChecked = $state(false);
  let statusRefreshTimer: ReturnType<typeof globalThis.setInterval> | undefined;

  const isLoading = $derived($growthStore.loadState === 'loading');
  const isRefreshing = $derived($growthStore.loadState === 'refreshing');
  const isSaving = $derived($growthStore.actionState === 'saving');
  const isTrainingAction = $derived($growthStore.actionState === 'training');
  const approvedExamples = $derived($growthStore.examples.filter((example) => example.status === 'approved'));
  const pendingExamples = $derived($growthStore.examples.filter((example) => example.status === 'pending_review'));
  const reviewExamples = $derived(
    $growthStore.examples.filter((example) => example.status === 'pending_review' || example.status === 'approved')
  );
  const activeJob = $derived($growthStore.currentJob);
  const trainingIsBusy = $derived(activeJob?.status === 'queued' || activeJob?.status === 'running');
  const canStartTraining = $derived(
    Boolean($growthStore.settings?.training_opt_in) &&
      approvedExamples.length > 0 &&
      trainingConsentChecked &&
      !trainingIsBusy &&
      !isTrainingAction
  );

  onMount(() => {
    void growthStore.load();
    void journalStore.loadEntries();
    statusRefreshTimer = globalThis.setInterval(() => {
      const status = $growthStore.currentJob?.status;
      if (status === 'queued' || status === 'running') void growthStore.refresh();
    }, 2_500);
  });

  onDestroy(() => {
    if (statusRefreshTimer) globalThis.clearInterval(statusRefreshTimer);
  });

  const refreshTraining = () => {
    void growthStore.refresh();
    void journalStore.refresh();
  };

  const updateCollectionOptIn = (event: Event) => {
    const enabled = event.currentTarget instanceof HTMLInputElement && event.currentTarget.checked;
    void growthStore.updateSettings({ collection_opt_in: enabled });
  };

  const updateTrainingOptIn = (event: Event) => {
    const enabled = event.currentTarget instanceof HTMLInputElement && event.currentTarget.checked;
    trainingConsentChecked = false;
    void growthStore.updateSettings({ training_opt_in: enabled });
  };

  const approveExample = (itemId: string) => void growthStore.approveExample(itemId);
  const rejectExample = (itemId: string) => void growthStore.rejectExample(itemId);
  const deleteExample = (itemId: string) => void growthStore.deleteExample(itemId);
  const startTraining = () => {
    if (canStartTraining) void growthStore.startTraining();
  };
  const stopTraining = () => void growthStore.stopTraining();

  const labelFor = (value: string | undefined) =>
    (value ?? 'unknown')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());

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

  const percent = (value: number | undefined) => `${Math.round((value ?? 0) * 100)}%`;

  const sourceDateFor = (example: PersonalLoRAExample) => {
    const entry = $journalStore.entries.find((item) => item.entry_id === example.source_journal_id);
    return entry?.created_at ? formatDate(entry.created_at) : 'Journal source linked';
  };

  const summaryFor = (example: PersonalLoRAExample) =>
    example.text || 'A private reflection candidate is waiting for your review.';

  const latestCompletedJob = (job: PersonalLoRAJob | null) => (job?.status === 'completed' ? job : null);
</script>

<section class="training-panel" aria-label="Personal LoRA training controls">
  <header class="training-hero">
    <div>
      <p class="eyebrow">Training</p>
      <h1>Let growth stay in your hands</h1>
      <p class="subtitle">
        Review the reflection notes Reverie may practice from. Nothing is trained unless you approve examples and choose to begin.
      </p>
    </div>

    <button class="ghost-button" type="button" onclick={refreshTraining} disabled={isLoading || isRefreshing || isSaving}>
      {isRefreshing ? 'Refreshing…' : 'Refresh'}
    </button>
  </header>

  {#if $growthStore.error}
    <div class="training-notice" role="status">
      <strong>Training stayed paused.</strong>
      <span>{$growthStore.error}</span>
    </div>
  {/if}

  {#if isLoading}
    <div class="journal-empty" aria-live="polite">
      <div class="journal-empty-mark">✦</div>
      <h2>Opening Training…</h2>
      <p>Reverie is checking your local review queue and adapter status.</p>
    </div>
  {:else}
    <div class="training-content">
      <section class="lora-status-card" aria-labelledby="lora-status-heading">
        <div>
          <span class="setting-kicker">Personal LoRA</span>
          <h2 id="lora-status-heading">Current status</h2>
          <p>
            Personal LoRA is optional. It is meant to help your companion practice stable style and continuity from approved reflections—not to rewrite who they are.
          </p>
        </div>

        <div class="lora-status-grid">
          <div>
            <span>Collection</span>
            <strong>{$growthStore.settings?.collection_opt_in ? 'Allowed' : 'Off'}</strong>
          </div>
          <div>
            <span>Training</span>
            <strong>{$growthStore.settings?.training_opt_in ? 'Opted in' : 'Off'}</strong>
          </div>
          <div>
            <span>Approved examples</span>
            <strong>{approvedExamples.length}</strong>
          </div>
          <div>
            <span>Last trained</span>
            <strong>{formatDate(latestCompletedJob(activeJob)?.completed_at)}</strong>
          </div>
        </div>
      </section>

      <section class="training-control-card" aria-labelledby="training-consent-heading">
        <div class="training-card-copy">
          <span class="setting-kicker">Consent</span>
          <h2 id="training-consent-heading">Safe opt-in controls</h2>
          <p>
            Collection only creates review cards. Training only uses cards marked Approved by you. Rejected or deleted examples are excluded.
          </p>
        </div>

        <div class="training-toggles">
          <label class="toggle-switch">
            <input
              type="checkbox"
              checked={$growthStore.settings?.collection_opt_in ?? false}
              onchange={updateCollectionOptIn}
            />
            <span>{$growthStore.settings?.collection_opt_in ? 'Collect candidates' : 'Do not collect'}</span>
          </label>
          <label class="toggle-switch">
            <input type="checkbox" checked={$growthStore.settings?.training_opt_in ?? false} onchange={updateTrainingOptIn} />
            <span>{$growthStore.settings?.training_opt_in ? 'Training allowed' : 'Training off'}</span>
          </label>
        </div>
      </section>

      <section class="training-review-card" aria-labelledby="training-review-heading">
        <div class="training-section-heading">
          <div>
            <span class="setting-kicker">Review queue</span>
            <h2 id="training-review-heading">Reflection candidates</h2>
            <p>
              {pendingExamples.length} waiting for review · {$growthStore.counts.approved} approved · {$growthStore.counts.rejected} rejected
            </p>
          </div>
        </div>

        {#if reviewExamples.length === 0}
          <div class="training-empty-state">
            <strong>No training candidates yet</strong>
            <p>
              When reflection creates safe, high-confidence examples, they will appear here for your approval before training can use them.
            </p>
          </div>
        {:else}
          <div class="training-example-list">
            {#each reviewExamples as example (example.item_id)}
              <article class:approved={example.status === 'approved'} class="training-example-card">
                <div class="training-example-main">
                  <div>
                    <span class="training-example-status">{labelFor(example.status)}</span>
                    <h3>{labelFor(example.purpose)}</h3>
                  </div>
                  <p>{summaryFor(example)}</p>
                </div>

                <div class="training-example-meta" aria-label="Training example metadata">
                  <span>{percent(example.confidence)} confidence</span>
                  <span>{example.evidence_count ?? 0} evidence points</span>
                  <span>From {sourceDateFor(example)}</span>
                </div>

                {#if example.themes?.length}
                  <div class="mini-tags" aria-label="Key themes">
                    {#each example.themes as theme}
                      <span>{labelFor(theme)}</span>
                    {/each}
                  </div>
                {/if}

                <div class="training-example-actions" aria-label="Example controls">
                  {#if example.status !== 'approved'}
                    <button type="button" onclick={() => approveExample(example.item_id)} disabled={isSaving}>Approve</button>
                  {/if}
                  <button type="button" class="soft" onclick={() => rejectExample(example.item_id)} disabled={isSaving}>Reject</button>
                  <button type="button" class="danger" onclick={() => deleteExample(example.item_id)} disabled={isSaving}>Delete</button>
                </div>
              </article>
            {/each}
          </div>
        {/if}
      </section>

      <section class="training-start-card" aria-labelledby="start-training-heading">
        <div>
          <span class="setting-kicker">Begin</span>
          <h2 id="start-training-heading">Start Training</h2>
          <p>
            This is a basic foundation job with simple status only. Keep chatting normally; Reverie will keep this training surface calm and reversible.
          </p>
        </div>

        <div class="training-progress-box">
          <div class="training-progress-heading">
            <strong>{labelFor(activeJob?.status ?? 'idle')}</strong>
            <span>{activeJob?.message ?? 'No training job is running.'}</span>
          </div>
          <div class="training-progress-track" aria-label="Training progress">
            <span style={`width: ${Math.round((activeJob?.progress ?? 0) * 100)}%`}></span>
          </div>
          <small>{activeJob?.example_count ?? approvedExamples.length} approved examples ready · Adapter stays off until you enable it later.</small>
        </div>

        <label class="training-confirmation">
          <input type="checkbox" bind:checked={trainingConsentChecked} disabled={!$growthStore.settings?.training_opt_in || trainingIsBusy} />
          <span>I understand only my approved examples will be used, and I can reject or delete candidates before training.</span>
        </label>

        <div class="training-start-actions">
          <button class="primary-training-button" type="button" onclick={startTraining} disabled={!canStartTraining}>
            {isTrainingAction ? 'Starting…' : 'Start Training'}
          </button>
          {#if trainingIsBusy}
            <button class="ghost-button" type="button" onclick={stopTraining} disabled={isTrainingAction}>Stop safely</button>
          {/if}
        </div>
      </section>

      <aside class="training-safety-note" aria-label="Training safety note">
        <span aria-hidden="true">♡</span>
        <div>
          <strong>Your data remains yours.</strong>
          <p>
            Personal LoRA candidates come from local reflections, require review, and preserve source links. This panel avoids advanced parameters so the first experience stays clear: inspect, approve, train, or say no.
          </p>
        </div>
      </aside>
    </div>
  {/if}
</section>
