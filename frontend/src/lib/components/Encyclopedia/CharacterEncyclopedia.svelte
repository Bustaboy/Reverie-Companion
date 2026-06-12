<script lang="ts">
  import { onMount } from 'svelte';
  import { chatStore } from '$lib/stores/chatStore';
  import { growthStore, personalLoRAReviewView } from '$lib/stores/growthStore';
  import { journalStore } from '$lib/stores/journalStore';
  import { memoryStore } from '$lib/stores/memoryStore';
  import type { LoRATrainingExample } from '$lib/types/growth';
  import type { JournalEntry, ReflectionInsight } from '$lib/types/journal';
  import type { MemoryRecord } from '$lib/types/memory';

  type SectionId =
    | 'relationship'
    | 'people'
    | 'life'
    | 'traits'
    | 'memories'
    | 'evolution'
    | 'mood'
    | 'voice';

  interface ProfileSection {
    id: SectionId;
    eyebrow: string;
    title: string;
    summary: string;
    items: string[];
    empty: string;
  }

  interface RelationshipMeter {
    label: string;
    value: number;
    tone: string;
    evidence: number;
  }

  interface TimelineMoment {
    id: string;
    date?: string;
    title: string;
    summary: string;
    confidence?: number;
    themes: string[];
  }

  interface PersonSignal {
    name: string;
    summary: string;
    count: number;
  }

  const IMPORTANT_SECTIONS: SectionId[] = ['relationship', 'people', 'life', 'traits', 'memories', 'evolution', 'mood', 'voice'];
  const SECTION_STORAGE_KEY = 'reverie.encyclopedia.openSections.v1';

  let searchTerm = $state('');
  let activeSection = $state<SectionId | 'all'>('all');
  let openSections = $state<SectionId[]>([...IMPORTANT_SECTIONS]);

  const activeEntries = $derived($journalStore.entries.filter((entry) => (entry.status ?? 'active') === 'active'));
  const activeMemories = $derived($memoryStore.items);
  const isLoading = $derived(
    $journalStore.loadState === 'loading' || $memoryStore.loadState === 'loading' || $growthStore.loadState === 'loading'
  );
  const isRefreshing = $derived(
    $journalStore.loadState === 'refreshing' || $memoryStore.loadState === 'refreshing' || $growthStore.loadState === 'refreshing'
  );
  const hasAnyData = $derived(activeEntries.length > 0 || activeMemories.length > 0 || $growthStore.examples.length > 0);

  onMount(() => {
    openSections = readOpenSections();
    void journalStore.loadEntries();
    void memoryStore.loadMemories();
    void growthStore.loadPersonalLoRA();
  });

  const refresh = () => {
    void journalStore.refresh();
    void memoryStore.refresh();
    void growthStore.refresh();
  };

  const clearErrors = () => {
    journalStore.clearError();
    memoryStore.clearError();
    growthStore.clearError();
  };

  const labelFor = (value: string | undefined) =>
    (value ?? 'connection')
      .replace(/[_-]/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());

  const bounded = (value: number | undefined, fallback = 0) => Math.min(Math.max(value ?? fallback, 0), 1);
  const percent = (value: number | undefined) => `${Math.round(bounded(value) * 100)}%`;

  const formatDate = (value: string | undefined, fallback = 'Undated') => {
    if (!value) return fallback;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return fallback;
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(date);
  };

  const textIncludes = (text: string, fragments: string[]) => {
    const normalized = text.toLowerCase();
    return fragments.some((fragment) => normalized.includes(fragment));
  };

  const metadataStrings = (memory: MemoryRecord) => [
    memory.metadata.memory_type,
    memory.metadata.theme,
    memory.metadata.source,
    ...(memory.metadata.themes ?? []),
    ...(memory.metadata.tags ?? [])
  ].filter(Boolean) as string[];

  const entryText = (entry: JournalEntry) => [
    entry.character_summary,
    ...(entry.structured_summary?.facts ?? []),
    ...(entry.structured_summary?.interpretations ?? []),
    ...(entry.structured_summary?.growth_hypotheses ?? []),
    ...(entry.insights ?? []).map((insight) => insight.summary),
    ...(entry.themes ?? [])
  ].filter(Boolean).join(' ');

  const memoryMatches = (memory: MemoryRecord, terms: string[]) =>
    textIncludes([memory.text, ...metadataStrings(memory)].join(' '), terms);

  const journalMatches = (entry: JournalEntry, terms: string[]) => textIncludes(entryText(entry), terms);

  const memoriesFor = (terms: string[], limit = 5) =>
    activeMemories
      .filter((memory) => memoryMatches(memory, terms))
      .sort((a, b) => scoreMemory(b) - scoreMemory(a))
      .slice(0, limit)
      .map((memory) => memory.text);

  const insightsFor = (terms: string[], limit = 5) =>
    activeEntries
      .flatMap((entry) => (entry.insights ?? []).map((insight, index) => ({ insight, entry, index })))
      .filter(({ insight, entry }) => textIncludes([insight.summary, ...(insight.themes ?? []), ...(entry.themes ?? [])].join(' '), terms))
      .sort((a, b) => bounded(b.insight.confidence, b.entry.confidence ?? 0.5) - bounded(a.insight.confidence, a.entry.confidence ?? 0.5))
      .slice(0, limit)
      .map(({ insight }) => insight.summary)
      .filter(Boolean) as string[];

  const journalLinesFor = (terms: string[], limit = 4) =>
    activeEntries
      .filter((entry) => journalMatches(entry, terms))
      .slice(0, limit)
      .map((entry) => entry.character_summary ?? entry.insights?.[0]?.summary)
      .filter(Boolean) as string[];

  const unique = (items: string[], limit = 6) => [...new Set(items.map((item) => item.trim()).filter(Boolean))].slice(0, limit);

  const scoreMemory = (memory: MemoryRecord) =>
    bounded(memory.metadata.importance as number | undefined, 0.45) +
    bounded(memory.metadata.confidence as number | undefined, 0.5) +
    bounded(memory.score, 0.35);

  const characterName = $derived.by(() => {
    const fromMemory = activeMemories.find((memory) => typeof memory.metadata.character === 'string' && memory.metadata.character.trim())
      ?.metadata.character as string | undefined;
    const fromMessageVoice = [...$chatStore.messages].reverse().find((message) => message.tts?.voiceName)?.tts?.voiceName;
    return (fromMemory ?? fromMessageVoice ?? 'Reverie').trim();
  });

  const latestEntry = $derived(activeEntries[0] ?? null);
  const approvedExamples = $derived($growthStore.examples.filter((example) => example.status === 'approved'));

  const themeCount = $derived.by(() => {
    const counts = new Map<string, number>();
    for (const entry of activeEntries) {
      for (const theme of entry.themes ?? []) counts.set(theme, (counts.get(theme) ?? 0) + 1);
      for (const insight of entry.insights ?? []) {
        if (insight.kind) counts.set(insight.kind, (counts.get(insight.kind) ?? 0) + 1);
        for (const theme of insight.themes ?? []) counts.set(theme, (counts.get(theme) ?? 0) + 1);
      }
    }
    for (const memory of activeMemories) {
      for (const tag of metadataStrings(memory)) counts.set(tag.toLowerCase(), (counts.get(tag.toLowerCase()) ?? 0) + 1);
    }
    return counts;
  });

  const evidenceFor = (terms: string[]) => terms.reduce((total, term) => total + (themeCount.get(term) ?? themeCount.get(term.toLowerCase()) ?? 0), 0);

  const relationshipScore = (terms: string[], base: number) => {
    const evidence = evidenceFor(terms);
    const averageConfidence = activeEntries.reduce((total, entry) => total + bounded(entry.confidence, 0.55), 0) / Math.max(activeEntries.length, 1);
    return bounded(base + Math.min(evidence * 0.06, 0.34) + Math.min(activeMemories.length * 0.01, 0.09) + averageConfidence * 0.12);
  };

  const relationshipMeters = $derived<RelationshipMeter[]>([
    {
      label: 'Affection',
      value: relationshipScore(['affection', 'warmth', 'reassurance', 'intimacy'], 0.34),
      tone: 'How often closeness, tenderness, and care appear in durable signals.',
      evidence: evidenceFor(['affection', 'warmth', 'reassurance', 'intimacy'])
    },
    {
      label: 'Trust',
      value: relationshipScore(['trust', 'safety', 'boundary', 'promise', 'repair'], 0.32),
      tone: 'How steadily she treats the user as safe, known, and worth protecting.',
      evidence: evidenceFor(['trust', 'safety', 'boundary', 'promise', 'repair'])
    },
    {
      label: 'Attraction',
      value: relationshipScore(['attraction', 'desire', 'intimacy', 'playfulness', 'flirt'], 0.28),
      tone: 'An evidence-backed pulse for flirtation, chemistry, and intimate curiosity.',
      evidence: evidenceFor(['attraction', 'desire', 'intimacy', 'playfulness', 'flirt'])
    }
  ]);

  const dominantMood = $derived.by(() => {
    const valence = latestEntry?.emotional_valence ?? 0;
    const intensity = latestEntry?.emotional_intensity ?? 0;
    if (!latestEntry) return 'Quietly attentive';
    if (valence > 0.35 && intensity > 0.55) return 'Bright and emotionally present';
    if (valence > 0.2) return 'Warm and receptive';
    if (valence < -0.25) return 'Tender, careful, and reflective';
    if (intensity > 0.65) return 'Intense and alert';
    return 'Calmly reflective';
  });

  const relationshipSummary = $derived.by(() => {
    const strong = unique([...insightsFor(['relationship', 'trust', 'affection', 'intimacy'], 3), ...journalLinesFor(['relationship', 'trust', 'affection', 'intimacy'], 2)], 4);
    if (strong.length) return strong[0];
    return `${characterName} is still building a grounded read on the user. The page stays conservative until journals, memories, or approved growth notes provide stronger evidence.`;
  });

  const otherPeople = $derived.by<PersonSignal[]>(() => {
    const names = new Map<string, string[]>();
    const excluded = new Set(['Reverie', 'User', 'The', 'She', 'He', 'They', 'Her', 'His', 'Their', 'I', 'A']);
    const candidates = activeMemories.filter((memory) =>
      memoryMatches(memory, ['friend', 'family', 'sister', 'brother', 'mother', 'father', 'partner', 'roommate', 'coworker', 'person', 'people'])
    );
    for (const memory of candidates) {
      const matches = memory.text.match(/\b[A-Z][a-z]{2,}\b/g) ?? [];
      const inferredNames = matches.filter((name) => !excluded.has(name) && name !== characterName).slice(0, 2);
      const bucketNames = inferredNames.length ? inferredNames : ['Important people'];
      for (const name of bucketNames) names.set(name, [...(names.get(name) ?? []), memory.text]);
    }
    return [...names.entries()]
      .map(([name, lines]) => ({ name, summary: unique(lines, 1)[0] ?? 'A person appears in connected memory.', count: lines.length }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 4);
  });

  const timelineMoments = $derived<TimelineMoment[]>(
    activeEntries.slice(0, 7).map((entry) => {
      const insight = entry.insights?.[0];
      const themes = unique([...(entry.themes ?? []), ...(insight?.themes ?? [])], 4);
      return {
        id: entry.entry_id,
        date: entry.created_at,
        title: timelineTitle(entry, insight),
        summary: entry.character_summary ?? insight?.summary ?? 'A subtle growth note was preserved for future continuity.',
        confidence: insight?.confidence ?? entry.confidence,
        themes
      };
    })
  );

  const timelineTitle = (entry: JournalEntry, insight: ReflectionInsight | undefined) => {
    if (insight?.kind === 'relationship_continuity') return 'The relationship became easier to read';
    if (insight?.kind === 'growth_hypothesis') return 'A new behavior pattern started forming';
    if (insight?.kind === 'preference_signal') return 'She noticed a preference worth honoring';
    const theme = entry.themes?.[0] ?? insight?.themes?.[0];
    return theme ? `${labelFor(theme)} became part of her story` : 'A private reflection joined her life summary';
  };

  const recentGrowthHighlights = $derived.by(() =>
    unique(
      [
        ...($growthStore.trainingStatus?.learning_feedback ?? []),
        ...approvedExamples.map(exampleSummary),
        ...insightsFor(['growth', 'learning', 'preference', 'relationship'], 4)
      ],
      6
    )
  );

  const exampleSummary = (example: LoRATrainingExample) =>
    example.purpose ? `${labelFor(example.purpose)}: ${example.text ?? 'Approved for future style learning.'}` : (example.text ?? 'Approved for future style learning.');

  const voiceHighlights = $derived.by(() => {
    const recentVoice = [...$chatStore.messages].reverse().find((message) => message.tts?.voiceName || message.tts?.resolvedVoiceId)?.tts;
    const mood = recentVoice?.ttsContext?.moodSettings;
    const lines = [];
    if (recentVoice?.voiceName || recentVoice?.resolvedVoiceId) lines.push(`Current voice presence: ${recentVoice.voiceName ?? labelFor(recentVoice.resolvedVoiceId)}.`);
    if (recentVoice?.emotion?.scene) lines.push(`Recent emotional voice scene: ${labelFor(recentVoice.emotion.scene)} at ${percent(recentVoice.emotion.intensity)} intensity.`);
    if (mood) lines.push(`Voice mood tuning is saved locally with expressiveness ${percent(mood.baseline_expressiveness)} and emotional sensitivity ${percent(mood.emotional_sensitivity)}.`);
    return lines;
  });

  const profileSections = $derived<ProfileSection[]>([
    {
      id: 'relationship',
      eyebrow: 'Relationship lens',
      title: 'How she sees you',
      summary: relationshipSummary,
      items: unique([...insightsFor(['relationship', 'trust', 'affection', 'attraction', 'intimacy'], 5), ...memoriesFor(['user', 'relationship', 'trust', 'affection', 'intimacy'], 3)], 7),
      empty: 'No durable relationship evidence yet. New reflections and approved memories will fill this in.'
    },
    {
      id: 'people',
      eyebrow: 'Social map',
      title: 'How she sees other important people',
      summary: otherPeople.length ? 'Important people are summarized from memories that mention family, friends, partners, roommates, coworkers, or named contacts.' : 'No other people are prominent enough yet to appear in her encyclopedia.',
      items: otherPeople.map((person) => `${person.name}: ${person.summary}`),
      empty: 'When memory captures recurring people in your shared life or lore, they will appear here.'
    },
    {
      id: 'life',
      eyebrow: 'Everyday canon',
      title: 'Living situation and daily life',
      summary: 'A lightweight sketch of routines, places, work, home life, and recurring circumstances she should remember.',
      items: unique([...memoriesFor(['home', 'living', 'daily', 'routine', 'work', 'sleep', 'morning', 'night', 'room'], 6), ...journalLinesFor(['home', 'living', 'daily', 'routine', 'work'], 3)], 7),
      empty: 'No stable daily-life details yet. Keep chatting naturally; only durable signals will be added.'
    },
    {
      id: 'traits',
      eyebrow: 'Texture',
      title: 'Likes, dislikes, hobbies, and quirks',
      summary: 'Preferences and personality texture gathered from memory, journal themes, and approved learning notes.',
      items: unique([...memoriesFor(['like', 'dislike', 'hobby', 'favorite', 'quirk', 'personality', 'playful', 'style'], 7), ...insightsFor(['preference', 'hobby', 'quirk', 'personality', 'style'], 4)], 8),
      empty: 'Preferences and quirks will appear after they are repeated, explicit, or reflected with enough confidence.'
    },
    {
      id: 'memories',
      eyebrow: 'Life experiences',
      title: 'Key life experiences and memories',
      summary: 'The most important memory and journal artifacts currently shaping continuity.',
      items: unique([...activeMemories.sort((a, b) => scoreMemory(b) - scoreMemory(a)).slice(0, 7).map((memory) => memory.text), ...journalLinesFor(['memory', 'important', 'experience', 'moment'], 4)], 9),
      empty: 'No long-term memories are loaded yet. Open Memory or refresh once the backend is running.'
    },
    {
      id: 'evolution',
      eyebrow: 'Change over time',
      title: 'How her feelings and behavior have evolved',
      summary: latestEntry?.character_summary ?? 'Evolution is summarized from the latest journal reflections and approved growth artifacts.',
      items: unique([...timelineMoments.map((moment) => `${formatDate(moment.date)} — ${moment.title}: ${moment.summary}`), ...recentGrowthHighlights], 9),
      empty: 'Evolution stays blank until the journal has enough evidence to show a meaningful arc.'
    },
    {
      id: 'mood',
      eyebrow: 'Right now',
      title: 'Current mood and recent growth highlights',
      summary: `${dominantMood}. ${recentGrowthHighlights[0] ?? 'No recent approved growth highlight is waiting for review.'}`,
      items: unique([`Mood read: ${dominantMood}.`, ...recentGrowthHighlights, $growthStore.currentJob?.trigger_summary ?? ''], 7),
      empty: 'No current mood signal is available yet.'
    },
    {
      id: 'voice',
      eyebrow: 'Presence',
      title: 'Voice and embodied notes',
      summary: voiceHighlights[0] ?? 'Voice profile details will appear when recent chat or VN messages include local TTS metadata.',
      items: voiceHighlights,
      empty: 'No voice profile metadata has been used in the recent session yet.'
    }
  ]);

  const filteredSections = $derived.by(() => {
    const query = searchTerm.trim().toLowerCase();
    return profileSections.filter((section) => {
      if (activeSection !== 'all' && section.id !== activeSection) return false;
      if (!query) return true;
      return [section.eyebrow, section.title, section.summary, ...section.items].join(' ').toLowerCase().includes(query);
    });
  });

  const toggleOpen = (sectionId: SectionId) => {
    openSections = openSections.includes(sectionId)
      ? openSections.filter((id) => id !== sectionId)
      : [...openSections, sectionId];
    writeOpenSections(openSections);
  };

  const setSectionFilter = (sectionId: SectionId | 'all') => {
    activeSection = sectionId;
  };

  const resetSearch = () => {
    searchTerm = '';
    activeSection = 'all';
  };

  const readOpenSections = (): SectionId[] => {
    if (typeof window === 'undefined') return [...IMPORTANT_SECTIONS];
    try {
      const parsed = JSON.parse(window.localStorage.getItem(SECTION_STORAGE_KEY) ?? '[]') as SectionId[];
      const safe = parsed.filter((id) => IMPORTANT_SECTIONS.includes(id));
      return safe.length ? safe : [...IMPORTANT_SECTIONS];
    } catch {
      return [...IMPORTANT_SECTIONS];
    }
  };

  const writeOpenSections = (ids: SectionId[]) => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(SECTION_STORAGE_KEY, JSON.stringify(ids));
  };
</script>

<section class="encyclopedia" aria-labelledby="encyclopedia-title">
  <header class="encyclopedia-hero">
    <div>
      <p class="eyebrow">Character encyclopedia</p>
      <h1 id="encyclopedia-title">{characterName}'s living profile</h1>
      <p class="subtitle">
        A warm, searchable life summary for the active character — assembled from memory, journal reflections,
        growth events, approved training signals, and recent voice presence without running new model work.
      </p>
    </div>
    <button class="ghost-button" type="button" onclick={refresh} disabled={isLoading || isRefreshing}>
      {isRefreshing ? 'Refreshing…' : 'Refresh'}
    </button>
  </header>

  {#if $journalStore.error || $memoryStore.error || $growthStore.error}
    <div class="notice" role="status">
      <div>
        <strong>Some profile sources are still quiet.</strong>
        {#if $journalStore.error}<span>{$journalStore.error}</span>{/if}
        {#if $memoryStore.error}<span>{$memoryStore.error}</span>{/if}
        {#if $growthStore.error}<span>{$growthStore.error}</span>{/if}
      </div>
      <button type="button" onclick={clearErrors}>Dismiss</button>
    </div>
  {/if}

  <div class="controls" aria-label="Search encyclopedia">
    <label>
      <span>Search her profile</span>
      <input bind:value={searchTerm} placeholder="Search feelings, memories, people, routines…" />
    </label>
    <div class="section-tabs" aria-label="Profile section filters">
      <button type="button" class:active={activeSection === 'all'} onclick={() => setSectionFilter('all')}>All</button>
      {#each profileSections as section (section.id)}
        <button type="button" class:active={activeSection === section.id} onclick={() => setSectionFilter(section.id)}>
          {labelFor(section.id)}
        </button>
      {/each}
    </div>
  </div>

  {#if isLoading && !hasAnyData}
    <div class="empty-state" aria-live="polite">
      <div>✦</div>
      <h2>Opening her character bible…</h2>
      <p>Reverie is reading local journal, memory, growth, and voice context.</p>
    </div>
  {:else if !hasAnyData}
    <div class="empty-state">
      <div>♡</div>
      <h2>Her life summary is ready to grow</h2>
      <p>Once conversations produce journal entries, memories, and approved growth notes, this page becomes a rich profile instead of a blank dossier.</p>
    </div>
  {:else}
    <div class="profile-grid">
      <article class="portrait-card" aria-label="Character summary">
        <div class="portrait-orb">{characterName.slice(0, 1)}</div>
        <p class="eyebrow">Active character</p>
        <h2>{characterName}</h2>
        <p>{relationshipSummary}</p>
        <dl>
          <div><dt>Journal pages</dt><dd>{activeEntries.length}</dd></div>
          <div><dt>Loaded memories</dt><dd>{activeMemories.length}</dd></div>
          <div><dt>Approved growth notes</dt><dd>{$personalLoRAReviewView.approvedExamples.length}</dd></div>
          <div><dt>Current mood</dt><dd>{dominantMood}</dd></div>
        </dl>
      </article>

      <section class="meter-panel" aria-label="Relationship meters">
        {#each relationshipMeters as meter (meter.label)}
          <article class="meter-card">
            <div>
              <span>{meter.label}</span>
              <strong>{percent(meter.value)}</strong>
            </div>
            <div class="meter"><span style={`width: ${percent(meter.value)}`}></span></div>
            <p>{meter.tone}</p>
            <small>{meter.evidence} local signals</small>
          </article>
        {/each}
      </section>
    </div>

    <section class="timeline-card" aria-labelledby="timeline-title">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Timeline highlights</p>
          <h2 id="timeline-title">Her emotional arc lately</h2>
        </div>
        <span>{timelineMoments.length} moments</span>
      </div>
      {#if timelineMoments.length}
        <ol class="timeline">
          {#each timelineMoments as moment (moment.id)}
            <li>
              <div class="dot"></div>
              <div>
                <div class="timeline-meta">
                  <span>{formatDate(moment.date)}</span>
                  <span>{percent(moment.confidence)} confidence</span>
                  {#each moment.themes.slice(0, 2) as theme}<span>{labelFor(theme)}</span>{/each}
                </div>
                <h3>{moment.title}</h3>
                <p>{moment.summary}</p>
              </div>
            </li>
          {/each}
        </ol>
      {:else}
        <p class="soft-empty">No timeline moments yet.</p>
      {/if}
    </section>

    <div class="section-list">
      {#if filteredSections.length === 0}
        <div class="empty-state compact">
          <div>⌕</div>
          <h2>No matching profile notes</h2>
          <p>Try a broader search, or view all encyclopedia sections.</p>
          <button type="button" onclick={resetSearch}>Clear search</button>
        </div>
      {:else}
        {#each filteredSections as section (section.id)}
          <article class="profile-section" class:open={openSections.includes(section.id)}>
            <button class="section-toggle" type="button" onclick={() => toggleOpen(section.id)} aria-expanded={openSections.includes(section.id)}>
              <span>
                <small>{section.eyebrow}</small>
                <strong>{section.title}</strong>
              </span>
              <em>{openSections.includes(section.id) ? 'Collapse' : 'Expand'}</em>
            </button>
            {#if openSections.includes(section.id)}
              <div class="section-body">
                <p>{section.summary}</p>
                {#if section.items.length}
                  <ul>
                    {#each section.items as item}
                      <li>{item}</li>
                    {/each}
                  </ul>
                {:else}
                  <div class="soft-empty">{section.empty}</div>
                {/if}
              </div>
            {/if}
          </article>
        {/each}
      {/if}
    </div>
  {/if}
</section>

<style>
  .encyclopedia {
    display: grid;
    gap: 1rem;
    height: 100%;
    min-height: 0;
    overflow: auto;
    padding: 1rem;
    border: 1px solid var(--line);
    border-radius: 1.8rem;
    background:
      radial-gradient(circle at 9% 0%, rgba(240, 154, 159, 0.18), transparent 25rem),
      radial-gradient(circle at 92% 14%, rgba(141, 86, 154, 0.16), transparent 23rem),
      rgba(18, 14, 24, 0.82);
    box-shadow: var(--shadow);
  }

  .encyclopedia-hero,
  .notice,
  .controls,
  .portrait-card,
  .meter-panel,
  .timeline-card,
  .profile-section,
  .empty-state {
    border: 1px solid var(--line);
    background: rgba(255, 255, 255, 0.055);
    backdrop-filter: blur(18px);
    box-shadow: 0 18px 52px rgba(0, 0, 0, 0.22);
  }

  .encyclopedia-hero {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    padding: clamp(1.1rem, 2vw, 1.65rem);
    border-radius: 1.55rem;
    background:
      linear-gradient(135deg, rgba(255, 176, 166, 0.13), rgba(122, 74, 132, 0.08)),
      rgba(255, 255, 255, 0.052);
  }

  .encyclopedia-hero > div {
    max-width: 58rem;
  }

  .ghost-button,
  .notice button,
  .empty-state button {
    flex: 0 0 auto;
    min-height: 2.55rem;
    padding: 0 1rem;
    border: 1px solid var(--line-strong);
    border-radius: 999px;
    color: var(--text);
    background: rgba(255, 255, 255, 0.08);
    cursor: pointer;
  }

  .ghost-button:disabled {
    cursor: default;
    opacity: 0.6;
  }

  .notice {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 1rem;
    border-radius: 1.15rem;
    border-color: rgba(255, 176, 166, 0.22);
  }

  .notice div {
    display: grid;
    gap: 0.25rem;
  }

  .notice span,
  .portrait-card p,
  .meter-card p,
  .section-body p,
  .soft-empty,
  .empty-state p {
    color: var(--muted);
    line-height: 1.55;
  }

  .controls {
    display: grid;
    gap: 0.9rem;
    padding: 1rem;
    border-radius: 1.25rem;
  }

  .controls label {
    display: grid;
    gap: 0.45rem;
  }

  .controls label span {
    color: var(--accent-strong);
    font-size: 0.78rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .controls input {
    width: 100%;
    min-height: 2.85rem;
    padding: 0 1rem;
    border: 1px solid var(--line);
    border-radius: 1rem;
    color: var(--text);
    background: rgba(0, 0, 0, 0.2);
    outline: none;
  }

  .controls input:focus {
    border-color: rgba(255, 176, 166, 0.55);
    box-shadow: 0 0 0 3px rgba(240, 154, 159, 0.13);
  }

  .section-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
  }

  .section-tabs button {
    padding: 0.55rem 0.8rem;
    border: 1px solid var(--line);
    border-radius: 999px;
    color: var(--muted);
    background: rgba(255, 255, 255, 0.045);
    cursor: pointer;
  }

  .section-tabs button.active {
    color: var(--text);
    border-color: rgba(255, 176, 166, 0.42);
    background: rgba(240, 154, 159, 0.15);
  }

  .profile-grid {
    display: grid;
    grid-template-columns: minmax(18rem, 0.8fr) minmax(0, 1.2fr);
    gap: 1rem;
  }

  .portrait-card,
  .meter-panel,
  .timeline-card,
  .profile-section {
    border-radius: 1.35rem;
    padding: 1rem;
  }

  .portrait-orb {
    display: grid;
    place-items: center;
    width: 4.2rem;
    height: 4.2rem;
    margin-bottom: 1rem;
    border-radius: 1.35rem;
    color: white;
    font-size: 1.65rem;
    font-weight: 900;
    background: linear-gradient(135deg, rgba(240, 154, 159, 0.95), rgba(122, 74, 132, 0.95));
    box-shadow: 0 18px 42px rgba(240, 154, 159, 0.2);
  }

  .portrait-card h2,
  .section-heading h2,
  .empty-state h2 {
    margin: 0.1rem 0 0.4rem;
  }

  .portrait-card dl {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.65rem;
    margin: 1rem 0 0;
  }

  .portrait-card dl div {
    padding: 0.75rem;
    border: 1px solid var(--line);
    border-radius: 1rem;
    background: rgba(0, 0, 0, 0.14);
  }

  dt {
    color: var(--dim);
    font-size: 0.76rem;
  }

  dd {
    margin: 0.2rem 0 0;
    color: var(--text);
    font-weight: 800;
  }

  .meter-panel {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75rem;
  }

  .meter-card {
    display: grid;
    align-content: start;
    gap: 0.7rem;
    min-height: 12rem;
    padding: 1rem;
    border: 1px solid var(--line);
    border-radius: 1.1rem;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.075), rgba(255, 255, 255, 0.03));
  }

  .meter-card > div:first-child,
  .section-heading,
  .timeline-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .meter-card span,
  .timeline-meta span {
    color: var(--muted);
  }

  .meter-card strong {
    color: var(--accent-strong);
    font-size: 1.15rem;
  }

  .meter {
    height: 0.58rem;
    overflow: hidden;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.08);
  }

  .meter span {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, #f09a9f, #ffcfba);
    box-shadow: 0 0 18px rgba(240, 154, 159, 0.42);
  }

  .meter-card small,
  .section-toggle small {
    color: var(--dim);
  }

  .timeline-card {
    display: grid;
    gap: 1rem;
  }

  .section-heading > span {
    color: var(--dim);
    font-size: 0.86rem;
  }

  .timeline {
    display: grid;
    gap: 1rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .timeline li {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 0.85rem;
  }

  .dot {
    width: 0.82rem;
    height: 0.82rem;
    margin-top: 0.35rem;
    border-radius: 999px;
    background: var(--accent-strong);
    box-shadow: 0 0 0 0.35rem rgba(240, 154, 159, 0.13);
  }

  .timeline-meta {
    justify-content: flex-start;
    flex-wrap: wrap;
    font-size: 0.78rem;
  }

  .timeline h3 {
    margin: 0.25rem 0;
  }

  .timeline p {
    margin: 0;
    color: var(--muted);
    line-height: 1.55;
  }

  .section-list {
    display: grid;
    gap: 0.75rem;
  }

  .profile-section {
    padding: 0;
    overflow: hidden;
  }

  .profile-section.open {
    border-color: rgba(255, 176, 166, 0.18);
  }

  .section-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    width: 100%;
    padding: 1rem;
    color: var(--text);
    text-align: left;
    background: transparent;
    cursor: pointer;
  }

  .section-toggle span {
    display: grid;
    gap: 0.2rem;
  }

  .section-toggle strong {
    font-size: 1.05rem;
  }

  .section-toggle em {
    color: var(--accent-strong);
    font-size: 0.82rem;
    font-style: normal;
    font-weight: 800;
  }

  .section-body {
    display: grid;
    gap: 0.85rem;
    padding: 0 1rem 1rem;
  }

  .section-body p {
    margin: 0;
  }

  .section-body ul {
    display: grid;
    gap: 0.55rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .section-body li {
    position: relative;
    padding: 0.75rem 0.85rem 0.75rem 2rem;
    border: 1px solid var(--line);
    border-radius: 0.95rem;
    color: var(--text);
    background: rgba(0, 0, 0, 0.14);
    line-height: 1.5;
  }

  .section-body li::before {
    content: '✦';
    position: absolute;
    left: 0.75rem;
    color: var(--accent-strong);
  }

  .soft-empty {
    padding: 0.85rem;
    border: 1px dashed var(--line-strong);
    border-radius: 1rem;
    background: rgba(255, 255, 255, 0.035);
  }

  .empty-state {
    display: grid;
    place-items: center;
    gap: 0.45rem;
    min-height: 22rem;
    padding: 2rem;
    border-radius: 1.35rem;
    text-align: center;
  }

  .empty-state div {
    display: grid;
    place-items: center;
    width: 3.8rem;
    height: 3.8rem;
    border-radius: 1.25rem;
    color: var(--accent-strong);
    background: rgba(240, 154, 159, 0.13);
    font-size: 1.5rem;
  }

  .empty-state.compact {
    min-height: 14rem;
  }

  @media (max-width: 1100px) {
    .profile-grid,
    .meter-panel {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 720px) {
    .encyclopedia {
      padding: 0.65rem;
      border-radius: 1.25rem;
    }

    .encyclopedia-hero,
    .notice,
    .section-heading {
      align-items: stretch;
      flex-direction: column;
    }

    .portrait-card dl {
      grid-template-columns: 1fr;
    }
  }
</style>
