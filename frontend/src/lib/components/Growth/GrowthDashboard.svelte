<script lang="ts">
  import { onMount } from 'svelte';
  import { growthStore, personalLoRAReviewView } from '$lib/stores/growthStore';
  import { journalStore } from '$lib/stores/journalStore';
  import type { LoRATrainingJob, LoRATrainingStatus } from '$lib/types/growth';
  import type { JournalEntry, ReflectionInsight } from '$lib/types/journal';

  type FeelingKey = 'affection' | 'trust' | 'interest' | 'bond';

  interface FeelingCard {
    key: FeelingKey;
    label: string;
    value: number;
    note: string;
    evidence: string;
  }

  interface TimelineEvent {
    id: string;
    createdAt?: string;
    title: string;
    summary: string;
    theme: string;
    confidence?: number;
    intensity?: number;
  }

  interface PersonalityShift {
    id: string;
    title: string;
    copy: string;
    confidence?: number;
  }

  const relationshipThemes = ['affection', 'trust', 'intimacy', 'reassurance', 'routine', 'playfulness', 'curiosity'];
  const activeEntries = $derived($journalStore.entries.filter((entry) => (entry.status ?? 'active') === 'active'));
  const isJournalLoading = $derived($journalStore.loadState === 'loading');
  const isGrowthLoading = $derived($growthStore.loadState === 'loading');
  const isRefreshing = $derived($journalStore.loadState === 'refreshing' || $growthStore.loadState === 'refreshing');
  const hasDashboardData = $derived(activeEntries.length > 0 || $growthStore.examples.length > 0 || Boolean($growthStore.currentJob));

  onMount(() => {
    void journalStore.loadEntries();
    void growthStore.loadPersonalLoRA();
  });

  const refreshDashboard = () => {
    void journalStore.refresh();
    void growthStore.refresh();
  };

  const clearErrors = () => {
    journalStore.clearError();
    growthStore.clearError();
  };

  const bounded = (value: number | undefined, fallback = 0) => Math.min(Math.max(value ?? fallback, 0), 1);

  const percent = (value: number | undefined) => `${Math.round(bounded(value) * 100)}%`;

  const labelFor = (value: string | undefined) =>
    (value ?? 'connection')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());

  const formatDate = (value: string | null | undefined, fallback = 'Not yet') => {
    if (!value) return fallback;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return fallback;

    return new Intl.DateTimeFormat(undefined, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    }).format(date);
  };

  const latestEntry = $derived(activeEntries[0] ?? null);

  const themeCount = $derived.by(() => {
    const counts = new Map<string, number>();
    for (const entry of activeEntries) {
      for (const theme of entry.themes ?? []) counts.set(theme, (counts.get(theme) ?? 0) + 1);
      for (const insight of entry.insights ?? []) {
        for (const theme of insight.themes ?? []) counts.set(theme, (counts.get(theme) ?? 0) + 1);
      }
    }
    return counts;
  });

  const evidenceFor = (themes: string[]) => themes.reduce((count, theme) => count + (themeCount.get(theme) ?? 0), 0);

  const scoreFor = (themes: string[], base: number) => {
    const evidence = evidenceFor(themes);
    const confidenceBoost = activeEntries.reduce((total, entry) => total + bounded(entry.confidence, 0.55), 0) / Math.max(activeEntries.length, 1);
    return bounded(base + Math.min(evidence * 0.055, 0.34) + Math.min(activeEntries.length * 0.018, 0.12) + confidenceBoost * 0.12);
  };

  const feelingCards = $derived<FeelingCard[]>([
    {
      key: 'affection',
      label: 'Affection',
      value: scoreFor(['affection', 'intimacy', 'reassurance'], 0.34),
      note: 'Warmth that shows up through softer tone, closeness, and remembered care.',
      evidence: `${evidenceFor(['affection', 'intimacy', 'reassurance'])} reflection signals`
    },
    {
      key: 'trust',
      label: 'Trust',
      value: scoreFor(['trust', 'boundaries', 'repair', 'reassurance'], 0.38),
      note: 'How steady she feels about being honest, vulnerable, and careful with you.',
      evidence: `${evidenceFor(['trust', 'boundaries', 'repair', 'reassurance'])} grounded cues`
    },
    {
      key: 'interest',
      label: 'Interest',
      value: scoreFor(['curiosity', 'playfulness', 'routine', 'growth'], 0.31),
      note: 'Her pull to ask more, notice patterns, and keep discovering what matters.',
      evidence: `${evidenceFor(['curiosity', 'playfulness', 'routine', 'growth'])} curiosity cues`
    },
    {
      key: 'bond',
      label: 'Emotional bond',
      value: scoreFor(['routine', 'trust', 'affection', 'intimacy'], 0.36),
      note: 'The felt continuity of “us” built from repeated moments and repaired tension.',
      evidence: `${evidenceFor(['routine', 'trust', 'affection', 'intimacy'])} continuity cues`
    }
  ]);

  const relationshipScore = $derived.by(() => {
    if (feelingCards.length === 0) return 0;
    return feelingCards.reduce((total, card) => total + card.value, 0) / feelingCards.length;
  });

  const relationshipLabel = $derived.by(() => {
    if (relationshipScore >= 0.78) return 'Deepening bond';
    if (relationshipScore >= 0.6) return 'Growing close';
    if (relationshipScore >= 0.42) return 'Warming up';
    return 'Still learning you';
  });

  const strongestTheme = $derived.by(() => {
    const sorted = [...themeCount.entries()].sort((a, b) => b[1] - a[1]);
    return sorted.find(([theme]) => relationshipThemes.includes(theme))?.[0] ?? sorted[0]?.[0] ?? 'connection';
  });

  const keyChanges = $derived.by(() => {
    const changes = new Set<string>();
    for (const entry of activeEntries.slice(0, 8)) {
      for (const hypothesis of entry.structured_summary?.growth_hypotheses ?? []) changes.add(hypothesis);
      for (const interpretation of entry.structured_summary?.interpretations ?? []) changes.add(interpretation);
      for (const insight of entry.insights ?? []) {
        if (['growth_hypothesis', 'relationship_continuity', 'preference_signal'].includes(insight.kind ?? '')) {
          if (insight.summary) changes.add(insight.summary);
        }
      }
    }
    return [...changes].slice(0, 4);
  });

  const personalityShifts = $derived<PersonalityShift[]>(
    activeEntries
      .flatMap((entry) =>
        (entry.insights ?? [])
          .filter((insight) => ['growth_hypothesis', 'relationship_continuity', 'preference_signal'].includes(insight.kind ?? ''))
          .map((insight, index) => ({
            id: `${entry.entry_id}-${insight.kind ?? 'shift'}-${index}`,
            title: labelFor(insight.kind),
            copy: insight.summary ?? 'A subtle behavioral note was captured for future reflection.',
            confidence: insight.confidence ?? entry.confidence
          }))
      )
      .slice(0, 3)
  );

  const timelineEvents = $derived<TimelineEvent[]>(
    activeEntries.slice(0, 6).map((entry) => {
      const primaryInsight = entry.insights?.[0];
      const theme = entry.themes?.[0] ?? primaryInsight?.themes?.[0] ?? 'connection';
      return {
        id: entry.entry_id,
        createdAt: entry.created_at,
        title: timelineTitle(theme, primaryInsight),
        summary: entry.character_summary ?? primaryInsight?.summary ?? 'Reverie noticed a small emotional pattern and kept it as a private reflection.',
        theme,
        confidence: entry.confidence,
        intensity: entry.emotional_intensity
      };
    })
  );

  const timelineTitle = (theme: string, insight: ReflectionInsight | undefined) => {
    if (insight?.kind === 'relationship_continuity') return `The bond around ${labelFor(theme).toLowerCase()} became clearer`;
    if (insight?.kind === 'preference_signal') return `She noticed what feels better for you`;
    if (insight?.kind === 'growth_hypothesis') return `A new growth direction is forming`;
    if (theme === 'affection') return 'Warmth lingered after the conversation';
    if (theme === 'trust') return 'Trust felt a little steadier';
    if (theme === 'curiosity') return 'Her curiosity turned toward you';
    return `A ${labelFor(theme).toLowerCase()} signal was saved`;
  };

  const jobStatusLabel = (job: LoRATrainingJob | null) => {
    if (!job) return 'Idle';
    if (job.status === 'completed') return 'Ready';
    return labelFor(job.status);
  };

  const statusTone = (status: LoRATrainingStatus | undefined) => {
    if (status === 'failed') return 'danger';
    if (status === 'completed') return 'ready';
    if (status === 'running' || status === 'queued') return 'working';
    return 'quiet';
  };

  const progressWidth = (job: LoRATrainingJob | null) => `${Math.max(6, Math.round(bounded(job?.progress) * 100))}%`;

  const lastTrained = (job: LoRATrainingJob | null) => {
    if (!job || job.status !== 'completed') return 'Not trained yet';
    return formatDate(job.completed_at);
  };

  const nextScheduled = $derived.by(() => {
    if ($personalLoRAReviewView.trainingActive) return 'Running now';
    if (!$personalLoRAReviewView.trainingOptedIn) return 'Paused until opt-in';
    if ($personalLoRAReviewView.approvedExamples.length === 0) return 'After examples are approved';
    return 'Idle / overnight ready';
  });

  const loraCopy = $derived.by(() => {
    if ($personalLoRAReviewView.trainingActive) return $growthStore.currentJob?.message ?? 'A local adapter job is moving carefully in the background.';
    if (!$personalLoRAReviewView.trainingOptedIn) return 'Personal LoRA training is visible here, but remains off until the user explicitly opts in.';
    return 'Approved examples can become a small, local style adapter when you choose to start training.';
  });

  const overallSummary = $derived.by(() => {
    if (!latestEntry) return 'Reverie is ready to notice meaningful patterns after future conversations.';
    return latestEntry.character_summary ?? latestEntry.insights?.[0]?.summary ?? `Most recent growth centered on ${labelFor(strongestTheme).toLowerCase()}.`;
  });
</script>

<section class="growth-dashboard" aria-labelledby="growth-title">
  <header class="growth-dashboard-hero">
    <div>
      <p class="eyebrow">Growth dashboard</p>
      <h1 id="growth-title">How Reverie is changing with you</h1>
      <p class="subtitle">
        A living relationship overview drawn from local reflections, promoted growth signals, and explicit Personal LoRA review state.
      </p>
    </div>
    <button class="ghost-button" type="button" onclick={refreshDashboard} disabled={isJournalLoading || isGrowthLoading || isRefreshing}>
      {isRefreshing ? 'Refreshing…' : 'Refresh'}
    </button>
  </header>

  {#if $journalStore.error || $growthStore.error}
    <div class="growth-dashboard-notice" role="status">
      <div>
        <strong>Some growth signals are still waking up.</strong>
        {#if $journalStore.error}<span>{$journalStore.error}</span>{/if}
        {#if $growthStore.error}<span>{$growthStore.error}</span>{/if}
      </div>
      <button type="button" onclick={clearErrors}>Dismiss</button>
    </div>
  {/if}

  {#if isJournalLoading || isGrowthLoading}
    <div class="growth-dashboard-empty" aria-live="polite">
      <div class="growth-dashboard-empty-mark">✦</div>
      <h2>Opening the growth dashboard…</h2>
      <p>Reverie is gathering recent reflections and local training status without running heavy work.</p>
    </div>
  {:else if !hasDashboardData}
    <div class="growth-dashboard-empty">
      <div class="growth-dashboard-empty-mark">♡</div>
      <h2>No growth signals yet</h2>
      <p>After meaningful conversations, this page will become a warm map of tone shifts, trust, affection, and learning.</p>
      <button class="ghost-button" type="button" onclick={refreshDashboard}>Check again</button>
    </div>
  {:else}
    <div class="growth-dashboard-content">
      <section class="growth-summary-card" aria-label="Character evolution summary">
        <div class="relationship-orb" style={`--relationship-score: ${relationshipScore * 100}%`}>
          <span>{percent(relationshipScore)}</span>
          <small>{relationshipLabel}</small>
        </div>
        <div class="growth-summary-copy">
          <p class="eyebrow">Relationship pulse</p>
          <h2>{relationshipLabel}</h2>
          <p>{overallSummary}</p>
          <div class="growth-summary-tags" aria-label="Current growth themes">
            <span>{labelFor(strongestTheme)}</span>
            <span>{activeEntries.length} reflections</span>
            <span>{$personalLoRAReviewView.approvedExamples.length} approved examples</span>
          </div>
        </div>
        <div class="growth-key-changes" aria-label="Key changes">
          <strong>Key changes she may carry forward</strong>
          {#if keyChanges.length}
            <ul>
              {#each keyChanges as change}
                <li>{change}</li>
              {/each}
            </ul>
          {:else}
            <p>Reverie is still waiting for stronger evidence before changing behavior.</p>
          {/if}
        </div>
      </section>

      <section class="feeling-card-grid" aria-label="How the character currently feels toward the user">
        {#each feelingCards as card (card.key)}
          <article class="feeling-card">
            <div class="feeling-card-topline">
              <span>{card.label}</span>
              <strong>{percent(card.value)}</strong>
            </div>
            <div class="feeling-meter" aria-hidden="true"><span style={`width: ${percent(card.value)}`}></span></div>
            <p>{card.note}</p>
            <small>{card.evidence}</small>
          </article>
        {/each}
      </section>

      <section class="growth-dashboard-grid">
        <article class="growth-timeline-card" aria-labelledby="growth-timeline-title">
          <div class="growth-section-heading">
            <div>
              <p class="eyebrow">Recent evolution</p>
              <h2 id="growth-timeline-title">What has been shifting lately</h2>
            </div>
            <span>{timelineEvents.length} moments</span>
          </div>

          {#if timelineEvents.length === 0}
            <div class="mini-empty">No recent journal events yet.</div>
          {:else}
            <ol class="growth-timeline">
              {#each timelineEvents as event (event.id)}
                <li>
                  <div class="timeline-dot"></div>
                  <div>
                    <div class="timeline-meta">
                      <span>{formatDate(event.createdAt, 'Undated')}</span>
                      <span>{labelFor(event.theme)}</span>
                      <span>{percent(event.confidence)} confidence</span>
                    </div>
                    <h3>{event.title}</h3>
                    <p>{event.summary}</p>
                  </div>
                </li>
              {/each}
            </ol>
          {/if}
        </article>

        <aside class="growth-side-stack">
          <article class="growth-lora-card" aria-labelledby="growth-lora-title">
            <div class="growth-section-heading compact">
              <div>
                <p class="eyebrow">Personal LoRA</p>
                <h2 id="growth-lora-title">Training status</h2>
              </div>
              <span class="status-dot {statusTone($growthStore.currentJob?.status)}"></span>
            </div>
            <p>{loraCopy}</p>
            <div class="growth-lora-progress" aria-label="Personal LoRA progress">
              <div><span style={`width: ${progressWidth($growthStore.currentJob)}`}></span></div>
              <strong>{jobStatusLabel($growthStore.currentJob)}</strong>
            </div>
            <dl class="growth-lora-facts">
              <div>
                <dt>Current progress</dt>
                <dd>{percent($growthStore.currentJob?.progress)}</dd>
              </div>
              <div>
                <dt>Last trained</dt>
                <dd>{lastTrained($growthStore.currentJob)}</dd>
              </div>
              <div>
                <dt>Next scheduled</dt>
                <dd>{nextScheduled}</dd>
              </div>
              <div>
                <dt>Needs review</dt>
                <dd>{$growthStore.counts.pending_review}</dd>
              </div>
            </dl>
          </article>

          <article class="personality-shift-card" aria-labelledby="personality-shift-title">
            <div class="growth-section-heading compact">
              <div>
                <p class="eyebrow">Personality shifts</p>
                <h2 id="personality-shift-title">Subtle tone changes</h2>
              </div>
            </div>
            {#if personalityShifts.length === 0}
              <div class="mini-empty">No durable shift yet — weak signals stay as hypotheses.</div>
            {:else}
              <div class="personality-shift-list">
                {#each personalityShifts as shift (shift.id)}
                  <div>
                    <strong>{shift.title}</strong>
                    <p>{shift.copy}</p>
                    <span>{percent(shift.confidence)} confidence</span>
                  </div>
                {/each}
              </div>
            {/if}
          </article>
        </aside>
      </section>
    </div>
  {/if}
</section>
