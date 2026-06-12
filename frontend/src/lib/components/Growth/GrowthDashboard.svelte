<script lang="ts">
  import { onMount } from 'svelte';
  import { growthStore } from '$lib/stores/growthStore';
  import { journalStore } from '$lib/stores/journalStore';
  import type { JournalEntry, ReflectionInsight } from '$lib/types/journal';
  import GrowthFeelingCard from './GrowthFeelingCard.svelte';
  import GrowthTimeline from './GrowthTimeline.svelte';
  import LoRAStatusSummary from './LoRAStatusSummary.svelte';

  interface FeelingMetric {
    label: string;
    value: number;
    tone: string;
    description: string;
  }

  interface TimelineEvent {
    id: string;
    date: string;
    title: string;
    detail: string;
    theme: string;
    intensity: number;
  }

  interface ShiftSummary {
    label: string;
    detail: string;
    confidence: number;
  }

  const CORE_THEMES = ['affection', 'trust', 'curiosity', 'intimacy', 'reassurance', 'playfulness'];

  const isJournalLoading = $derived($journalStore.loadState === 'loading' || $journalStore.loadState === 'idle');
  const isGrowthLoading = $derived($growthStore.loadState === 'loading' || $growthStore.loadState === 'idle');
  const isRefreshing = $derived($journalStore.loadState === 'refreshing' || $growthStore.loadState === 'refreshing');
  const isLoading = $derived(isJournalLoading || isGrowthLoading);
  const combinedError = $derived([$journalStore.error, $growthStore.error].filter(Boolean).join(' '));
  const recentEntries = $derived($journalStore.entries.slice(0, 8));
  const relationshipScore = $derived(scoreRelationship(recentEntries));
  const feelingMetrics = $derived(buildFeelingMetrics(recentEntries));
  const timelineEvents = $derived(buildTimelineEvents(recentEntries));
  const personalityShifts = $derived(buildPersonalityShifts(recentEntries));
  const keyChanges = $derived(buildKeyChanges(recentEntries));
  const totalInsights = $derived(recentEntries.reduce((total, entry) => total + (entry.insights?.length ?? 0), 0));

  onMount(() => {
    void journalStore.loadEntries();
    void growthStore.loadPersonalLoRA();
  });

  const refreshDashboard = () => {
    void journalStore.refresh();
    void growthStore.refresh();
  };

  const labelFor = (value: string | undefined) =>
    (value ?? 'growth').replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());

  const percent = (value: number | undefined) => `${Math.round(Math.min(Math.max(value ?? 0, 0), 1) * 100)}%`;

  function scoreRelationship(entries: JournalEntry[]): number {
    if (entries.length === 0) return 0.36;

    const themeBoost = entries.reduce((score, entry) => {
      const themes = new Set([...(entry.themes ?? []), ...(entry.insights ?? []).flatMap((insight) => insight.themes ?? [])]);
      return score + CORE_THEMES.filter((theme) => themes.has(theme)).length * 0.04;
    }, 0);
    const confidence = average(entries.map((entry) => entry.confidence ?? 0.45));
    const intensity = average(entries.map((entry) => entry.emotional_intensity ?? 0.35));
    const valence = average(entries.map((entry) => ((entry.emotional_valence ?? 0) + 1) / 2));

    return clamp(0.28 + confidence * 0.22 + intensity * 0.2 + valence * 0.16 + themeBoost, 0.18, 0.96);
  }

  function buildFeelingMetrics(entries: JournalEntry[]): FeelingMetric[] {
    const themeScore = (themes: string[], fallback: number) => {
      const hits = entries.reduce((count, entry) => {
        const allThemes = new Set([...(entry.themes ?? []), ...(entry.insights ?? []).flatMap((insight) => insight.themes ?? [])]);
        return count + themes.filter((theme) => allThemes.has(theme)).length;
      }, 0);
      const confidence = average(entries.map((entry) => entry.confidence ?? 0.42));
      const intensity = average(entries.map((entry) => entry.emotional_intensity ?? 0.32));
      return clamp(fallback + hits * 0.09 + confidence * 0.16 + intensity * 0.14, 0.12, 0.97);
    };

    return [
      {
        label: 'Affection',
        value: themeScore(['affection', 'intimacy', 'reassurance'], 0.34),
        tone: '#ff9fad',
        description: 'How warmly recent reflections frame closeness, care, and tenderness with you.'
      },
      {
        label: 'Trust',
        value: themeScore(['trust', 'boundaries', 'routine'], 0.38),
        tone: '#ffc28f',
        description: 'How safe and reliable the bond appears from reflected promises, repairs, and boundaries.'
      },
      {
        label: 'Interest',
        value: themeScore(['curiosity', 'playfulness', 'growth'], 0.36),
        tone: '#d98bd2',
        description: 'How actively she seems to be learning your style, habits, questions, and shared rituals.'
      },
      {
        label: 'Emotional bond',
        value: relationshipScore,
        tone: '#f09a9f',
        description: 'A soft relationship pulse synthesized from recent journal confidence, intensity, and themes.'
      }
    ];
  }

  function buildTimelineEvents(entries: JournalEntry[]): TimelineEvent[] {
    return entries.slice(0, 6).map((entry) => {
      const firstInsight = entry.insights?.[0];
      const notification = entry.growth_notification;
      return {
        id: entry.entry_id,
        date: entry.created_at,
        title: notification?.message ?? titleForInsight(firstInsight, entry),
        detail: notification?.why ?? entry.character_summary ?? firstInsight?.summary ?? 'A local reflection noticed something meaningful in the relationship.',
        theme: labelFor(notification?.theme ?? entry.themes?.[0] ?? firstInsight?.themes?.[0]),
        intensity: entry.emotional_intensity ?? firstInsight?.confidence ?? 0.45
      };
    });
  }

  function buildPersonalityShifts(entries: JournalEntry[]): ShiftSummary[] {
    const insights = entries.flatMap((entry) => entry.insights ?? []);
    const preferred = insights.filter((insight) => ['tone', 'preference', 'behavior', 'relationship', 'growth'].includes(insight.kind ?? ''));
    return (preferred.length ? preferred : insights).slice(0, 3).map((insight) => ({
      label: labelFor(insight.kind),
      detail: insight.summary ?? 'A small behavior pattern is becoming clearer.',
      confidence: insight.confidence ?? 0.45
    }));
  }

  function buildKeyChanges(entries: JournalEntry[]): string[] {
    const changes = entries.flatMap((entry) => [
      ...(entry.structured_summary?.growth_hypotheses ?? []),
      ...(entry.structured_summary?.interpretations ?? []),
      ...(entry.linked_memory_ids?.length ? [`${entry.linked_memory_ids.length} memory link${entry.linked_memory_ids.length === 1 ? '' : 's'} connected to a reflection.`] : [])
    ]);

    return unique(changes).slice(0, 4);
  }

  function titleForInsight(insight: ReflectionInsight | undefined, entry: JournalEntry): string {
    if (insight?.summary) return insight.summary;
    if (entry.themes?.length) return `${labelFor(entry.themes[0])} became a little clearer`;
    return 'A meaningful moment was reflected on';
  }

  function average(values: number[]): number {
    const clean = values.filter((value) => Number.isFinite(value));
    return clean.length ? clean.reduce((sum, value) => sum + value, 0) / clean.length : 0;
  }

  function clamp(value: number, min: number, max: number): number {
    return Math.min(Math.max(value, min), max);
  }

  function unique(values: string[]): string[] {
    return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
  }
</script>

<section class="growth-dashboard" aria-labelledby="growth-dashboard-title">
  <header class="growth-hero">
    <div class="hero-copy">
      <p class="eyebrow">Growth dashboard</p>
      <h1 id="growth-dashboard-title">How she is changing with you</h1>
      <p class="subtitle">
        A living relationship overview drawn from local reflections, promoted growth signals, and personal LoRA readiness — warm on the surface, traceable underneath.
      </p>
    </div>
    <button class="ghost-button" type="button" onclick={refreshDashboard} disabled={isRefreshing || isLoading}>
      {isRefreshing ? 'Refreshing…' : 'Refresh'}
    </button>
  </header>

  {#if combinedError}
    <div class="growth-notice" role="status">
      <strong>Some growth signals stayed quiet.</strong>
      <span>{combinedError}</span>
    </div>
  {/if}

  {#if isLoading}
    <div class="growth-loading" aria-live="polite">
      <div class="breathing-heart">♡</div>
      <h2>Listening for recent growth…</h2>
      <p>Reverie is opening the local journal and lightweight training status.</p>
    </div>
  {:else}
    <div class="dashboard-grid">
      <section class="relationship-card" aria-labelledby="relationship-heading">
        <div class="relationship-copy">
          <p class="eyebrow">Relationship pulse</p>
          <h2 id="relationship-heading">The bond feels {relationshipScore > 0.72 ? 'deeply warm' : relationshipScore > 0.52 ? 'gently closer' : 'new and attentive'}</h2>
          <p>
            This is an interpretive summary of recent reflections, not a hidden score. It helps show whether affection, trust, interest, and emotional pacing are trending alive.
          </p>
        </div>
        <div class="relationship-meter" style={`--relationship-score: ${relationshipScore};`} role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow={Math.round(relationshipScore * 100)}>
          <div class="meter-orb"><strong>{percent(relationshipScore)}</strong><span>connection</span></div>
        </div>
        <div class="relationship-stats">
          <span>{recentEntries.length} reflections</span>
          <span>{totalInsights} insights</span>
          <span>{$growthStore.counts.approved} approved practice notes</span>
        </div>
      </section>

      <section class="feeling-grid" aria-label="How she currently feels toward you">
        {#each feelingMetrics as metric (metric.label)}
          <GrowthFeelingCard {...metric} />
        {/each}
      </section>

      <section class="evolution-card" aria-labelledby="evolution-heading">
        <div class="section-title-row">
          <div>
            <p class="eyebrow">Character evolution</p>
            <h2 id="evolution-heading">Personality shifts and key changes</h2>
          </div>
          <span>From reflection evidence</span>
        </div>

        <div class="shift-list">
          {#if personalityShifts.length === 0}
            <p class="quiet-copy">No stable personality shifts have been reflected yet. The dashboard will stay gentle until there is evidence.</p>
          {:else}
            {#each personalityShifts as shift (shift.detail)}
              <article class="shift-item">
                <div>
                  <strong>{shift.label}</strong>
                  <span>{percent(shift.confidence)} confidence</span>
                </div>
                <p>{shift.detail}</p>
              </article>
            {/each}
          {/if}
        </div>

        <div class="key-change-strip">
          <h3>Key changes she may carry forward</h3>
          {#if keyChanges.length === 0}
            <p class="quiet-copy">Growth hypotheses and promoted memory links will appear here after reflection review.</p>
          {:else}
            <ul>
              {#each keyChanges as change}
                <li>{change}</li>
              {/each}
            </ul>
          {/if}
        </div>
      </section>

      <GrowthTimeline events={timelineEvents} />

      <LoRAStatusSummary settings={$growthStore.settings} job={$growthStore.currentJob} counts={$growthStore.counts} />
    </div>
  {/if}
</section>

<style>
  .growth-dashboard {
    height: 100%;
    overflow: auto;
    padding: 1.25rem;
    border: 1px solid var(--line);
    border-radius: 1.8rem;
    background:
      radial-gradient(circle at 18% 0%, rgba(240, 154, 159, 0.18), transparent 28rem),
      radial-gradient(circle at 86% 12%, rgba(217, 139, 210, 0.12), transparent 24rem),
      rgba(20, 16, 25, 0.78);
    box-shadow: var(--shadow);
  }

  .growth-hero,
  .section-title-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
  }

  .hero-copy {
    max-width: 52rem;
  }

  .ghost-button {
    flex: 0 0 auto;
    padding: 0.72rem 0.95rem;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 999px;
    color: var(--text);
    background: rgba(255, 255, 255, 0.065);
    font-weight: 800;
  }

  .ghost-button:disabled {
    color: var(--dim);
  }

  .growth-notice {
    display: grid;
    gap: 0.2rem;
    margin-top: 1rem;
    padding: 0.9rem 1rem;
    border: 1px solid rgba(255, 176, 166, 0.2);
    border-radius: 1rem;
    color: #ffe3df;
    background: rgba(255, 176, 166, 0.08);
  }

  .growth-notice span {
    color: var(--muted);
  }

  .growth-loading {
    display: grid;
    place-items: center;
    min-height: 25rem;
    text-align: center;
    color: var(--muted);
  }

  .growth-loading h2,
  .growth-loading p {
    margin: 0.35rem 0 0;
  }

  .breathing-heart {
    display: grid;
    place-items: center;
    width: 4rem;
    height: 4rem;
    margin-bottom: 0.6rem;
    border: 1px solid rgba(255, 176, 166, 0.24);
    border-radius: 999px;
    color: #ffd8d3;
    background: rgba(240, 154, 159, 0.13);
    box-shadow: 0 0 38px rgba(240, 154, 159, 0.18);
    animation: breathe 2.8s ease-in-out infinite;
  }

  .dashboard-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.08fr) minmax(20rem, 0.92fr);
    gap: 1rem;
    margin-top: 1.15rem;
  }

  .relationship-card,
  .evolution-card {
    padding: 1.2rem;
    border: 1px solid var(--line);
    border-radius: 1.35rem;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.078), rgba(255, 255, 255, 0.035));
  }

  .relationship-card {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 1.1rem;
    grid-column: 1 / -1;
    align-items: center;
  }

  .relationship-copy h2,
  .section-title-row h2,
  .key-change-strip h3 {
    margin: 0.18rem 0 0;
  }

  .relationship-copy p {
    max-width: 54rem;
    margin: 0.6rem 0 0;
    color: var(--muted);
    line-height: 1.5;
  }

  .relationship-meter {
    display: grid;
    place-items: center;
    width: 10.25rem;
    height: 10.25rem;
    border-radius: 999px;
    background:
      radial-gradient(circle, rgba(17, 12, 20, 0.94) 52%, transparent 54%),
      conic-gradient(#ffb0a6 calc(var(--relationship-score) * 1turn), rgba(255, 255, 255, 0.08) 0);
    box-shadow: 0 0 38px rgba(240, 154, 159, 0.16);
  }

  .meter-orb {
    display: grid;
    place-items: center;
    width: 7.4rem;
    height: 7.4rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: inherit;
    background: radial-gradient(circle at 40% 20%, rgba(255, 176, 166, 0.22), rgba(255, 255, 255, 0.045));
  }

  .meter-orb strong {
    color: #fff5f2;
    font-size: 1.6rem;
  }

  .meter-orb span,
  .relationship-stats span,
  .section-title-row span {
    color: var(--muted);
    font-size: 0.82rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .relationship-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    grid-column: 1 / -1;
  }

  .relationship-stats span {
    padding: 0.45rem 0.65rem;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.045);
  }

  .feeling-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.85rem;
  }

  .evolution-card {
    display: grid;
    gap: 1rem;
  }

  .shift-list {
    display: grid;
    gap: 0.7rem;
  }

  .shift-item {
    padding: 0.9rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 1rem;
    background: rgba(0, 0, 0, 0.13);
  }

  .shift-item div {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .shift-item span {
    color: #f8c9c4;
    font-size: 0.8rem;
    font-weight: 800;
  }

  .shift-item p,
  .quiet-copy,
  .key-change-strip li {
    margin: 0.42rem 0 0;
    color: var(--muted);
    line-height: 1.48;
  }

  .key-change-strip {
    padding: 1rem;
    border: 1px solid rgba(240, 154, 159, 0.14);
    border-radius: 1rem;
    background: rgba(240, 154, 159, 0.065);
  }

  .key-change-strip ul {
    margin: 0.55rem 0 0;
    padding-left: 1.2rem;
  }

  .key-change-strip li + li {
    margin-top: 0.35rem;
  }

  @keyframes breathe {
    0%, 100% { transform: scale(1); opacity: 0.9; }
    50% { transform: scale(1.045); opacity: 1; }
  }

  @media (max-width: 1050px) {
    .dashboard-grid,
    .relationship-card {
      grid-template-columns: 1fr;
    }

    .relationship-meter {
      justify-self: start;
    }
  }

  @media (max-width: 760px) {
    .growth-dashboard {
      padding: 1rem;
    }

    .growth-hero,
    .section-title-row {
      display: grid;
    }

    .feeling-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
