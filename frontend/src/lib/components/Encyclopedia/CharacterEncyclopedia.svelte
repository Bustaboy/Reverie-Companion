<script lang="ts">
  import { onMount } from 'svelte';
  import { growthStore } from '$lib/stores/growthStore';
  import { journalStore } from '$lib/stores/journalStore';
  import { memoryStore } from '$lib/stores/memoryStore';
  import { voiceService, type VoiceProfile } from '$lib/api/voiceService';
  import type { JournalEntry, ReflectionInsight } from '$lib/types/journal';
  import type { LoRATrainingExample } from '$lib/types/growth';
  import type { MemoryRecord } from '$lib/types/memory';

  type SectionId = 'relationship' | 'people' | 'daily' | 'traits' | 'memories' | 'evolution' | 'mood';
  type MeterKey = 'affection' | 'trust' | 'attraction';

  interface ProfileSection {
    id: SectionId;
    title: string;
    kicker: string;
    empty: string;
    items: string[];
  }

  interface Meter {
    key: MeterKey;
    label: string;
    value: number;
    note: string;
  }

  interface TimelinePoint {
    id: string;
    date?: string;
    title: string;
    summary: string;
    source: string;
  }

  interface ImportantPerson {
    name: string;
    description: string;
    evidenceCount: number;
  }

  const DEFAULT_OPEN_SECTIONS: SectionId[] = ['relationship', 'mood', 'memories', 'evolution'];
  const CHARACTER_KEYS = ['character_name', 'character', 'character_id'];
  const IMPORTANT_PERSON_KEYS = ['people', 'person', 'persons', 'important_people', 'relationships', 'entities'];
  const SECTION_KEYWORDS: Record<SectionId, string[]> = {
    relationship: ['user', 'relationship', 'affection', 'trust', 'attraction', 'intimacy', 'bond', 'partner', 'closeness'],
    people: ['friend', 'family', 'sibling', 'mother', 'father', 'rival', 'mentor', 'ex', 'coworker', 'neighbor'],
    daily: ['home', 'living', 'room', 'daily', 'routine', 'morning', 'night', 'work', 'job', 'school', 'apartment', 'house'],
    traits: ['like', 'dislike', 'hobby', 'quirk', 'personality', 'favorite', 'enjoy', 'prefer', 'habit', 'style'],
    memories: ['memory', 'remember', 'experience', 'promise', 'important', 'turning point', 'first', 'meaningful'],
    evolution: ['growth', 'changed', 'change', 'learned', 'evolution', 'became', 'more comfortable', 'repair', 'boundary'],
    mood: ['mood', 'recent', 'today', 'now', 'feeling', 'current', 'valence', 'highlight']
  };

  let searchTerm = $state('');
  let openSections = $state<SectionId[]>(DEFAULT_OPEN_SECTIONS);
  let voiceProfiles = $state<VoiceProfile[]>([]);
  let voiceLoadState = $state<'idle' | 'loading' | 'loaded' | 'error'>('idle');

  const activeJournalEntries = $derived($journalStore.entries.filter((entry) => (entry.status ?? 'active') === 'active'));
  const activeMemories = $derived($memoryStore.items);
  const approvedExamples = $derived($growthStore.examples.filter((example) => example.status === 'approved'));
  const recentExamples = $derived($growthStore.examples.slice(0, 6));
  const isLoading = $derived(
    $journalStore.loadState === 'loading' || $memoryStore.loadState === 'loading' || $growthStore.loadState === 'loading'
  );
  const isRefreshing = $derived(
    $journalStore.loadState === 'refreshing' || $memoryStore.loadState === 'refreshing' || $growthStore.loadState === 'refreshing'
  );
  const characterName = $derived(resolveCharacterName(activeJournalEntries, activeMemories, voiceProfiles));
  const filteredEntries = $derived(filterForCharacter(activeJournalEntries, characterName));
  const filteredMemories = $derived(filterMemoriesForCharacter(activeMemories, characterName));
  const allEvidenceText = $derived([...filteredEntries.map(summaryForEntry), ...filteredMemories.map((memory) => memory.text)]);
  const evidenceCountByKeyword = $derived.by(() => buildKeywordCounts(allEvidenceText));
  const relationshipMeters = $derived<Meter[]>(buildRelationshipMeters(evidenceCountByKeyword, filteredEntries));
  const people = $derived(buildImportantPeople(filteredEntries, filteredMemories));
  const profileSections = $derived(buildProfileSections(filteredEntries, filteredMemories, approvedExamples, people));
  const timeline = $derived(buildTimeline(filteredEntries, filteredMemories, recentExamples));
  const currentMood = $derived(describeMood(filteredEntries[0]));
  const recentGrowthHighlights = $derived(buildGrowthHighlights(filteredEntries, recentExamples));
  const visibleSections = $derived(filterSections(profileSections, searchTerm));

  onMount(() => {
    void journalStore.loadEntries();
    void memoryStore.loadMemories();
    void growthStore.loadPersonalLoRA();
    void loadVoiceProfiles();
  });

  const loadVoiceProfiles = async () => {
    voiceLoadState = 'loading';
    try {
      voiceProfiles = await voiceService.listVoices();
      voiceLoadState = 'loaded';
    } catch {
      voiceProfiles = [];
      voiceLoadState = 'error';
    }
  };

  const refresh = () => {
    void journalStore.refresh();
    void memoryStore.refresh();
    void growthStore.refresh();
    void loadVoiceProfiles();
  };

  const toggleSection = (sectionId: SectionId) => {
    openSections = openSections.includes(sectionId)
      ? openSections.filter((id) => id !== sectionId)
      : [...openSections, sectionId];
  };

  const isOpen = (sectionId: SectionId) => openSections.includes(sectionId);

  const clearSearch = () => {
    searchTerm = '';
  };

  function resolveCharacterName(entries: JournalEntry[], memories: MemoryRecord[], voices: VoiceProfile[]): string {
    for (const entry of entries) {
      const metadataName = firstStringFromRecord(entry.metadata, CHARACTER_KEYS);
      if (metadataName) return labelFor(metadataName);
    }

    for (const memory of memories) {
      const metadataName = firstStringFromRecord(memory.metadata, CHARACTER_KEYS);
      if (metadataName) return labelFor(metadataName);
    }

    const characterVoice = voices.find((voice) => voice.type === 'character');
    if (characterVoice?.name) return characterVoice.name;

    return 'Reverie';
  }

  function filterForCharacter(entries: JournalEntry[], name: string): JournalEntry[] {
    const needle = name.toLowerCase();
    return entries.filter((entry) => {
      const metadataName = firstStringFromRecord(entry.metadata, CHARACTER_KEYS);
      if (!metadataName || name === 'Reverie') return true;
      return metadataName.toLowerCase() === needle || labelFor(metadataName).toLowerCase() === needle;
    });
  }

  function filterMemoriesForCharacter(memories: MemoryRecord[], name: string): MemoryRecord[] {
    const needle = name.toLowerCase();
    return memories.filter((memory) => {
      const metadataName = firstStringFromRecord(memory.metadata, CHARACTER_KEYS);
      if (!metadataName || name === 'Reverie') return true;
      return metadataName.toLowerCase() === needle || labelFor(metadataName).toLowerCase() === needle;
    });
  }

  function buildKeywordCounts(texts: string[]): Map<string, number> {
    const counts = new Map<string, number>();
    const corpus = texts.join('\n').toLowerCase();
    for (const keywords of Object.values(SECTION_KEYWORDS)) {
      for (const keyword of keywords) {
        const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const matches = corpus.match(new RegExp(`\\b${escaped}\\b`, 'g'));
        if (matches?.length) counts.set(keyword, matches.length);
      }
    }
    return counts;
  }

  function buildRelationshipMeters(counts: Map<string, number>, entries: JournalEntry[]): Meter[] {
    const averageConfidence = average(entries.map((entry) => entry.confidence ?? 0.58), 0.58);
    const score = (keywords: string[], base: number) => {
      const evidence = keywords.reduce((total, keyword) => total + (counts.get(keyword) ?? 0), 0);
      return clamp(base + Math.min(evidence * 0.055, 0.32) + averageConfidence * 0.14 + Math.min(entries.length * 0.014, 0.12));
    };

    return [
      {
        key: 'affection',
        label: 'Affection',
        value: score(['affection', 'intimacy', 'bond', 'closeness'], 0.36),
        note: 'Warmth, softness, and remembered care toward the user.'
      },
      {
        key: 'trust',
        label: 'Trust',
        value: score(['trust', 'promise', 'boundary', 'repair'], 0.4),
        note: 'How safe she feels being honest, vulnerable, and consistent.'
      },
      {
        key: 'attraction',
        label: 'Attraction',
        value: score(['attraction', 'intimacy', 'partner', 'closeness'], 0.3),
        note: 'Romantic or intimate pull, kept evidence-based rather than assumed.'
      }
    ];
  }

  function buildImportantPeople(entries: JournalEntry[], memories: MemoryRecord[]): ImportantPerson[] {
    const peopleMap = new Map<string, { snippets: string[]; count: number }>();
    const addPerson = (rawName: unknown, snippet: string) => {
      if (typeof rawName !== 'string' || rawName.trim().length < 2) return;
      const name = labelFor(rawName.trim());
      if (name.toLowerCase() === 'user' || name.toLowerCase() === 'reverie') return;
      const existing = peopleMap.get(name) ?? { snippets: [], count: 0 };
      existing.count += 1;
      if (snippet && existing.snippets.length < 2) existing.snippets.push(snippet);
      peopleMap.set(name, existing);
    };

    for (const memory of memories) {
      for (const value of valuesFromMetadata(memory.metadata, IMPORTANT_PERSON_KEYS)) addPerson(value, memory.text);
    }

    for (const entry of entries) {
      for (const value of valuesFromMetadata(entry.metadata, IMPORTANT_PERSON_KEYS)) addPerson(value, summaryForEntry(entry));
      for (const theme of entry.themes ?? []) {
        if (SECTION_KEYWORDS.people.includes(theme.toLowerCase())) addPerson(theme, summaryForEntry(entry));
      }
    }

    return [...peopleMap.entries()]
      .sort((a, b) => b[1].count - a[1].count)
      .slice(0, 5)
      .map(([name, evidence]) => ({
        name,
        description: evidence.snippets[0] ?? 'Mentioned in local memory or reflection evidence.',
        evidenceCount: evidence.count
      }));
  }

  function buildProfileSections(
    entries: JournalEntry[],
    memories: MemoryRecord[],
    examples: LoRATrainingExample[],
    importantPeople: ImportantPerson[]
  ): ProfileSection[] {
    const snippetsBySection = new Map<SectionId, string[]>();
    for (const sectionId of Object.keys(SECTION_KEYWORDS) as SectionId[]) snippetsBySection.set(sectionId, []);

    const addSnippet = (sectionId: SectionId, snippet: string | undefined) => {
      const cleaned = cleanSnippet(snippet);
      if (!cleaned) return;
      const snippets = snippetsBySection.get(sectionId) ?? [];
      if (!snippets.some((existing) => existing.toLowerCase() === cleaned.toLowerCase())) snippets.push(cleaned);
      snippetsBySection.set(sectionId, snippets.slice(0, 5));
    };

    for (const memory of memories) {
      const themes = lowerList([memory.metadata.theme, ...(memory.metadata.themes ?? []), ...(memory.metadata.tags ?? [])]);
      for (const sectionId of Object.keys(SECTION_KEYWORDS) as SectionId[]) {
        if (matchesSection(memory.text, themes, sectionId)) addSnippet(sectionId, memory.text);
      }
    }

    for (const entry of entries) {
      const summary = summaryForEntry(entry);
      const themes = lowerList([...(entry.themes ?? []), ...(entry.insights ?? []).flatMap((insight) => insight.themes ?? [])]);
      for (const sectionId of Object.keys(SECTION_KEYWORDS) as SectionId[]) {
        if (matchesSection(summary, themes, sectionId)) addSnippet(sectionId, summary);
      }

      for (const fact of entry.structured_summary?.facts ?? []) addSnippet('memories', fact);
      for (const interpretation of entry.structured_summary?.interpretations ?? []) addSnippet('relationship', interpretation);
      for (const hypothesis of entry.structured_summary?.growth_hypotheses ?? []) addSnippet('evolution', hypothesis);
      for (const insight of entry.insights ?? []) addInsight(insight, addSnippet);
    }

    for (const example of examples) {
      addSnippet('evolution', example.text ?? example.purpose ?? example.themes?.join(', '));
    }

    if (importantPeople.length) {
      snippetsBySection.set(
        'people',
        importantPeople.map((person) => `${person.name}: ${cleanSnippet(person.description) ?? 'important person'}`)
      );
    }

    return [
      {
        id: 'relationship',
        title: 'How she sees you',
        kicker: 'Relationship summary',
        empty: 'As memories and journal reflections accumulate, Reverie will summarize affection, trust, attraction, and the shape of your bond here.',
        items: snippetsBySection.get('relationship') ?? []
      },
      {
        id: 'people',
        title: 'Other important people',
        kicker: 'Social constellation',
        empty: 'No recurring people have enough evidence yet. When friends, family, rivals, or mentors matter, they will gather here.',
        items: snippetsBySection.get('people') ?? []
      },
      {
        id: 'daily',
        title: 'Living situation & daily life',
        kicker: 'Home, routines, and ordinary days',
        empty: 'Daily-life details will appear after they are saved as memory or reflected on in the journal.',
        items: snippetsBySection.get('daily') ?? []
      },
      {
        id: 'traits',
        title: 'Likes, dislikes, hobbies & quirks',
        kicker: 'Texture that keeps her recognizable',
        empty: 'Preferences, hobbies, and personality quirks will appear here once Reverie has reliable local evidence.',
        items: snippetsBySection.get('traits') ?? []
      },
      {
        id: 'memories',
        title: 'Key life experiences & memories',
        kicker: 'Prominent continuity anchors',
        empty: 'Important memories will surface here as the Memory Browser and reflection journal gather stronger evidence.',
        items: snippetsBySection.get('memories') ?? []
      },
      {
        id: 'evolution',
        title: 'Evolution over time',
        kicker: 'How feelings and behavior have changed',
        empty: 'Growth signals will appear here after repeated evidence, approved learning notes, or journal-backed shifts.',
        items: snippetsBySection.get('evolution') ?? []
      },
      {
        id: 'mood',
        title: 'Current mood & recent growth',
        kicker: 'Latest emotional weather',
        empty: 'Recent reflections and training review will create a living mood and growth snapshot.',
        items: snippetsBySection.get('mood') ?? []
      }
    ];
  }

  function addInsight(insight: ReflectionInsight, addSnippet: (sectionId: SectionId, snippet: string | undefined) => void) {
    const themes = lowerList(insight.themes ?? []);
    for (const sectionId of Object.keys(SECTION_KEYWORDS) as SectionId[]) {
      if (matchesSection(insight.summary ?? '', themes, sectionId)) addSnippet(sectionId, insight.summary);
    }
  }

  function buildTimeline(entries: JournalEntry[], memories: MemoryRecord[], examples: LoRATrainingExample[]): TimelinePoint[] {
    const journalPoints = entries.slice(0, 5).map((entry) => ({
      id: entry.entry_id,
      date: entry.created_at,
      title: titleForEntry(entry),
      summary: summaryForEntry(entry),
      source: 'Journal'
    }));

    const memoryPoints = memories.slice(0, 4).map((memory) => ({
      id: memory.id,
      date: memory.updated_at ?? memory.created_at,
      title: labelFor(String(memory.metadata.theme ?? memory.metadata.memory_type ?? 'Memory anchor')),
      summary: memory.text,
      source: 'Memory'
    }));

    const growthPoints = examples.slice(0, 3).map((example) => ({
      id: example.item_id,
      date: example.updated_at ?? example.created_at,
      title: labelFor(example.purpose ?? 'Practice note'),
      summary: example.text ?? example.themes?.join(', ') ?? 'Approved growth material waiting for future training.',
      source: 'Growth'
    }));

    return [...journalPoints, ...memoryPoints, ...growthPoints]
      .filter((point) => cleanSnippet(point.summary))
      .sort((a, b) => dateValue(b.date) - dateValue(a.date))
      .slice(0, 8);
  }

  function describeMood(entry: JournalEntry | undefined): string {
    if (!entry) return 'Quiet and gathering herself — no recent reflection has been written yet.';
    const valence = entry.emotional_valence ?? 0;
    const intensity = entry.emotional_intensity ?? 0.35;
    const tone = valence > 0.28 ? 'warm' : valence < -0.28 ? 'tender and unsettled' : 'thoughtful';
    const energy = intensity > 0.66 ? 'vividly felt' : intensity > 0.36 ? 'present but steady' : 'soft and low-lit';
    return `She feels ${tone}, with ${energy} emotional energy around ${titleForEntry(entry).toLowerCase()}.`;
  }

  function buildGrowthHighlights(entries: JournalEntry[], examples: LoRATrainingExample[]): string[] {
    const highlights = [
      ...entries.flatMap((entry) => entry.structured_summary?.growth_hypotheses ?? []),
      ...entries.flatMap((entry) => (entry.insights ?? []).filter((insight) => insight.memory_worthy).map((insight) => insight.summary ?? '')),
      ...examples.flatMap((example) => example.themes ?? []),
      ...examples.map((example) => example.text ?? example.purpose ?? '')
    ];
    return uniqueClean(highlights).slice(0, 4);
  }

  function filterSections(sections: ProfileSection[], query: string): ProfileSection[] {
    const needle = query.trim().toLowerCase();
    if (!needle) return sections;
    return sections
      .map((section) => ({
        ...section,
        items: section.items.filter((item) => `${section.title} ${section.kicker} ${item}`.toLowerCase().includes(needle))
      }))
      .filter((section) => `${section.title} ${section.kicker}`.toLowerCase().includes(needle) || section.items.length > 0);
  }

  function matchesSection(text: string, themes: string[], sectionId: SectionId): boolean {
    const lowerText = text.toLowerCase();
    return SECTION_KEYWORDS[sectionId].some((keyword) => lowerText.includes(keyword) || themes.includes(keyword));
  }

  function firstStringFromRecord(record: Record<string, unknown> | undefined, keys: string[]): string | null {
    if (!record) return null;
    for (const key of keys) {
      const value = record[key];
      if (typeof value === 'string' && value.trim()) return value.trim();
    }
    return null;
  }

  function valuesFromMetadata(record: Record<string, unknown> | undefined, keys: string[]): string[] {
    if (!record) return [];
    const values: string[] = [];
    for (const key of keys) collectStrings(record[key], values);
    return values;
  }

  function collectStrings(value: unknown, values: string[]) {
    if (typeof value === 'string') values.push(value);
    else if (Array.isArray(value)) value.forEach((item) => collectStrings(item, values));
    else if (value && typeof value === 'object') {
      const candidate = value as Record<string, unknown>;
      collectStrings(candidate.name ?? candidate.label ?? candidate.id, values);
    }
  }

  function summaryForEntry(entry: JournalEntry): string {
    return (
      entry.character_summary ??
      entry.insights?.[0]?.summary ??
      entry.structured_summary?.interpretations?.[0] ??
      entry.structured_summary?.facts?.[0] ??
      'A quiet reflection without a written summary yet.'
    );
  }

  function titleForEntry(entry: JournalEntry): string {
    const theme = entry.themes?.[0] ?? entry.insights?.[0]?.themes?.[0];
    return theme ? labelFor(theme) : 'Recent reflection';
  }

  function labelFor(value: string): string {
    return value.replace(/[_-]/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function cleanSnippet(value: string | undefined): string | null {
    if (!value) return null;
    const compact = value.replace(/\s+/g, ' ').trim();
    if (!compact) return null;
    return compact.length > 210 ? `${compact.slice(0, 207).trim()}…` : compact;
  }

  function uniqueClean(values: string[]): string[] {
    const seen = new Set<string>();
    const output: string[] = [];
    for (const value of values) {
      const cleaned = cleanSnippet(value);
      if (!cleaned) continue;
      const key = cleaned.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      output.push(cleaned);
    }
    return output;
  }

  function lowerList(values: Array<string | undefined>): string[] {
    return values.filter((value): value is string => typeof value === 'string').map((value) => value.toLowerCase());
  }

  function average(values: number[], fallback: number): number {
    const valid = values.filter((value) => Number.isFinite(value));
    if (!valid.length) return fallback;
    return valid.reduce((total, value) => total + value, 0) / valid.length;
  }

  function clamp(value: number): number {
    return Math.min(Math.max(value, 0), 1);
  }

  function percent(value: number): string {
    return `${Math.round(clamp(value) * 100)}%`;
  }

  function dateValue(value: string | undefined): number {
    if (!value) return 0;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? 0 : date.getTime();
  }

  function formatDate(value: string | undefined): string {
    if (!value) return 'Undated';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Undated';
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(date);
  }
</script>

<section class="encyclopedia" aria-label="Character encyclopedia">
  <header class="encyclopedia-hero">
    <div class="hero-copy">
      <p class="eyebrow">Character encyclopedia</p>
      <h1>{characterName}'s living profile</h1>
      <p class="subtitle">
        A searchable, evidence-aware character bible drawn from memory, journal reflections, growth review, and voice profile context.
      </p>
    </div>

    <div class="hero-card" aria-label="Profile evidence summary">
      <span class="hero-orbit">✦</span>
      <strong>{filteredMemories.length + filteredEntries.length}</strong>
      <small>local evidence points</small>
      <button type="button" onclick={refresh} disabled={isLoading || isRefreshing}>{isRefreshing ? 'Refreshing…' : 'Refresh'}</button>
    </div>
  </header>

  <div class="encyclopedia-toolbar">
    <label class="profile-search">
      <span>Search the profile</span>
      <input bind:value={searchTerm} type="search" placeholder="Try affection, home, hobbies, promises…" />
    </label>
    {#if searchTerm}
      <button class="ghost-button" type="button" onclick={clearSearch}>Clear</button>
    {/if}
  </div>

  {#if $journalStore.error || $memoryStore.error || $growthStore.error}
    <div class="soft-notice" role="status">
      <strong>Some local sources could not be reached.</strong>
      <span>The encyclopedia will still render from whatever memory, journal, growth, or voice data is available.</span>
    </div>
  {/if}

  <div class="profile-grid">
    <aside class="profile-sidebar" aria-label="Relationship and mood snapshot">
      <div class="portrait-card">
        <div class="portrait-glow" aria-hidden="true"></div>
        <div class="portrait-initial">{characterName.slice(0, 1)}</div>
        <p>Active character</p>
        <h2>{characterName}</h2>
        <span>{voiceLoadState === 'loaded' ? `${voiceProfiles.length} voice profile source${voiceProfiles.length === 1 ? '' : 's'}` : 'Voice profile optional'}</span>
      </div>

      <div class="meter-card">
        <p class="mini-heading">Relationship meter</p>
        {#each relationshipMeters as meter}
          <div class="meter-row">
            <div class="meter-label">
              <strong>{meter.label}</strong>
              <span>{percent(meter.value)}</span>
            </div>
            <div class="meter-track" aria-label={`${meter.label} ${percent(meter.value)}`}>
              <div class={`meter-fill ${meter.key}`} style={`width: ${percent(meter.value)}`}></div>
            </div>
            <small>{meter.note}</small>
          </div>
        {/each}
      </div>

      <div class="mood-card">
        <p class="mini-heading">Current mood</p>
        <strong>{currentMood}</strong>
        {#if recentGrowthHighlights.length}
          <ul>
            {#each recentGrowthHighlights as highlight}
              <li>{highlight}</li>
            {/each}
          </ul>
        {:else}
          <span>Growth highlights will appear after journal-backed changes or approved practice notes.</span>
        {/if}
      </div>
    </aside>

    <div class="profile-main">
      {#if isLoading}
        <div class="empty-state" aria-live="polite">
          <div>✧</div>
          <h2>Gathering the living profile…</h2>
          <p>Reverie is collecting lightweight local summaries from memory, journal, growth, and voice sources.</p>
        </div>
      {:else if !filteredMemories.length && !filteredEntries.length && !recentExamples.length}
        <div class="empty-state">
          <div>♡</div>
          <h2>No encyclopedia evidence yet</h2>
          <p>Chat, reflect, and save memories; the character bible will become richer as local evidence accumulates.</p>
        </div>
      {:else}
        <div class="section-stack">
          {#each visibleSections as section}
            <article class="profile-section" class:open={isOpen(section.id)}>
              <button class="section-toggle" type="button" onclick={() => toggleSection(section.id)} aria-expanded={isOpen(section.id)}>
                <span>
                  <small>{section.kicker}</small>
                  <strong>{section.title}</strong>
                </span>
                <em>{section.items.length ? `${section.items.length} notes` : 'waiting for evidence'}</em>
                <b aria-hidden="true">{isOpen(section.id) ? '−' : '+'}</b>
              </button>

              {#if isOpen(section.id)}
                <div class="section-body">
                  {#if section.items.length}
                    <ul class="note-list">
                      {#each section.items as item}
                        <li>{item}</li>
                      {/each}
                    </ul>
                  {:else}
                    <p class="empty-copy">{section.empty}</p>
                  {/if}
                </div>
              {/if}
            </article>
          {/each}
        </div>

        <section class="timeline-card" aria-label="Character timeline highlights">
          <div class="timeline-header">
            <div>
              <p class="eyebrow">Timeline highlights</p>
              <h2>Recent continuity anchors</h2>
            </div>
            <span>{timeline.length} moments</span>
          </div>

          {#if timeline.length}
            <ol class="timeline-list">
              {#each timeline as point}
                <li>
                  <div class="timeline-dot" aria-hidden="true"></div>
                  <div>
                    <p>{formatDate(point.date)} · {point.source}</p>
                    <h3>{point.title}</h3>
                    <span>{cleanSnippet(point.summary)}</span>
                  </div>
                </li>
              {/each}
            </ol>
          {:else}
            <p class="empty-copy">Timeline moments will appear once journal entries, memories, or approved growth examples exist.</p>
          {/if}
        </section>
      {/if}
    </div>
  </div>
</section>

<style>
  .encyclopedia {
    display: grid;
    grid-template-rows: auto auto auto minmax(0, 1fr);
    gap: 1rem;
    height: 100%;
    overflow: hidden;
    color: var(--text);
  }

  .encyclopedia-hero,
  .encyclopedia-toolbar,
  .profile-sidebar > *,
  .profile-section,
  .timeline-card,
  .soft-notice,
  .empty-state {
    border: 1px solid var(--line);
    background: linear-gradient(145deg, rgba(36, 28, 44, 0.92), rgba(24, 20, 31, 0.86));
    box-shadow: var(--shadow);
    backdrop-filter: blur(24px);
  }

  .encyclopedia-hero {
    position: relative;
    display: flex;
    align-items: stretch;
    justify-content: space-between;
    gap: 1rem;
    overflow: hidden;
    padding: 1.35rem;
    border-radius: 1.8rem;
  }

  .encyclopedia-hero::before {
    content: '';
    position: absolute;
    inset: -45% auto auto 30%;
    width: 28rem;
    height: 28rem;
    border-radius: 999px;
    background: radial-gradient(circle, rgba(240, 154, 159, 0.18), transparent 62%);
    pointer-events: none;
  }

  .hero-copy,
  .hero-card {
    position: relative;
    z-index: 1;
  }

  .hero-copy {
    max-width: 54rem;
  }

  .hero-card {
    display: grid;
    place-items: center;
    min-width: 13rem;
    padding: 1rem;
    border: 1px solid rgba(240, 154, 159, 0.22);
    border-radius: 1.4rem;
    background: rgba(240, 154, 159, 0.075);
    text-align: center;
  }

  .hero-orbit {
    display: grid;
    place-items: center;
    width: 2rem;
    height: 2rem;
    border-radius: 999px;
    background: rgba(255, 176, 166, 0.14);
    color: var(--accent-strong);
  }

  .hero-card strong {
    margin-top: 0.35rem;
    font-size: 2.3rem;
    line-height: 1;
  }

  .hero-card small,
  .mini-heading,
  .meter-row small,
  .mood-card span,
  .timeline-header span,
  .timeline-list p,
  .empty-copy {
    color: var(--muted);
  }

  .hero-card button,
  .ghost-button {
    margin-top: 0.8rem;
    padding: 0.62rem 0.86rem;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.07);
    color: var(--text);
    font-weight: 800;
  }

  .hero-card button:disabled,
  .ghost-button:disabled {
    cursor: wait;
    opacity: 0.62;
  }

  .encyclopedia-toolbar {
    display: flex;
    align-items: end;
    gap: 0.8rem;
    padding: 0.85rem;
    border-radius: 1.35rem;
  }

  .profile-search {
    display: grid;
    flex: 1;
    gap: 0.4rem;
  }

  .profile-search span {
    color: var(--muted);
    font-size: 0.78rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .profile-search input {
    width: 100%;
    padding: 0.82rem 0.95rem;
    border: 1px solid var(--line);
    border-radius: 1rem;
    outline: none;
    background: rgba(255, 255, 255, 0.055);
    color: var(--text);
    font: inherit;
  }

  .profile-search input:focus {
    border-color: rgba(240, 154, 159, 0.45);
    box-shadow: 0 0 0 3px rgba(240, 154, 159, 0.1);
  }

  .soft-notice {
    display: grid;
    gap: 0.25rem;
    padding: 0.85rem 1rem;
    border-radius: 1rem;
  }

  .profile-grid {
    display: grid;
    grid-template-columns: minmax(18rem, 22rem) minmax(0, 1fr);
    gap: 1rem;
    min-height: 0;
    overflow: hidden;
  }

  .profile-sidebar,
  .profile-main {
    min-height: 0;
    overflow-y: auto;
    scrollbar-color: rgba(255, 255, 255, 0.22) transparent;
  }

  .profile-sidebar {
    display: grid;
    align-content: start;
    gap: 1rem;
  }

  .portrait-card,
  .meter-card,
  .mood-card {
    border-radius: 1.45rem;
    padding: 1rem;
  }

  .portrait-card {
    position: relative;
    display: grid;
    min-height: 13rem;
    justify-items: center;
    overflow: hidden;
    text-align: center;
  }

  .portrait-glow {
    position: absolute;
    inset: -30% 10% auto;
    height: 10rem;
    border-radius: 999px;
    background: radial-gradient(circle, rgba(255, 176, 166, 0.2), transparent 68%);
  }

  .portrait-initial {
    position: relative;
    display: grid;
    place-items: center;
    width: 5rem;
    height: 5rem;
    margin: 0.3rem 0 0.75rem;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 1.55rem;
    background: linear-gradient(135deg, rgba(240, 154, 159, 0.92), rgba(122, 74, 132, 0.9));
    font-size: 2rem;
    font-weight: 900;
  }

  .portrait-card p,
  .portrait-card h2,
  .portrait-card span,
  .mini-heading,
  .timeline-header h2,
  .timeline-list h3,
  .mood-card ul {
    margin: 0;
  }

  .portrait-card p,
  .mini-heading {
    color: var(--accent-strong);
    font-size: 0.76rem;
    font-weight: 900;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  .portrait-card h2 {
    margin-top: 0.2rem;
  }

  .portrait-card span {
    margin-top: 0.35rem;
    color: var(--muted);
    font-size: 0.86rem;
  }

  .meter-card,
  .mood-card {
    display: grid;
    gap: 0.9rem;
  }

  .meter-row {
    display: grid;
    gap: 0.35rem;
  }

  .meter-label {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .meter-track {
    height: 0.55rem;
    overflow: hidden;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.08);
  }

  .meter-fill {
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--accent), var(--accent-strong));
  }

  .meter-fill.trust {
    background: linear-gradient(90deg, #9dddc7, #f8cfa0);
  }

  .meter-fill.attraction {
    background: linear-gradient(90deg, #c98cf4, #ff9aaa);
  }

  .mood-card strong {
    line-height: 1.45;
  }

  .mood-card ul {
    display: grid;
    gap: 0.45rem;
    padding-left: 1.1rem;
    color: var(--muted);
  }

  .profile-main {
    display: grid;
    align-content: start;
    gap: 1rem;
    padding-right: 0.2rem;
  }

  .section-stack {
    display: grid;
    gap: 0.8rem;
  }

  .profile-section {
    overflow: hidden;
    border-radius: 1.35rem;
  }

  .profile-section.open {
    border-color: rgba(240, 154, 159, 0.22);
  }

  .section-toggle {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto auto;
    align-items: center;
    gap: 0.85rem;
    width: 100%;
    padding: 1rem;
    background: transparent;
    color: var(--text);
    text-align: left;
  }

  .section-toggle small,
  .section-toggle strong {
    display: block;
  }

  .section-toggle small {
    margin-bottom: 0.2rem;
    color: var(--accent-strong);
    font-size: 0.72rem;
    font-weight: 900;
    letter-spacing: 0.09em;
    text-transform: uppercase;
  }

  .section-toggle strong {
    font-size: 1.05rem;
  }

  .section-toggle em {
    color: var(--muted);
    font-size: 0.84rem;
    font-style: normal;
  }

  .section-toggle b {
    display: grid;
    place-items: center;
    width: 1.85rem;
    height: 1.85rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.07);
    color: var(--accent-strong);
  }

  .section-body {
    padding: 0 1rem 1rem;
  }

  .note-list {
    display: grid;
    gap: 0.65rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .note-list li {
    position: relative;
    padding: 0.85rem 0.9rem 0.85rem 2.1rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 1rem;
    background: rgba(255, 255, 255, 0.045);
    color: #f8eff6;
    line-height: 1.5;
  }

  .note-list li::before {
    content: '✦';
    position: absolute;
    left: 0.82rem;
    top: 0.88rem;
    color: var(--accent-strong);
  }

  .timeline-card {
    display: grid;
    gap: 1rem;
    border-radius: 1.45rem;
    padding: 1rem;
  }

  .timeline-header {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 1rem;
  }

  .timeline-list {
    display: grid;
    gap: 0.9rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .timeline-list li {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 0.8rem;
  }

  .timeline-dot {
    width: 0.8rem;
    height: 0.8rem;
    margin-top: 0.35rem;
    border-radius: 999px;
    background: var(--accent-strong);
    box-shadow: 0 0 0 0.38rem rgba(255, 176, 166, 0.12);
  }

  .timeline-list p {
    margin: 0 0 0.15rem;
    font-size: 0.8rem;
  }

  .timeline-list h3 {
    font-size: 1rem;
  }

  .timeline-list span {
    display: block;
    margin-top: 0.28rem;
    color: var(--muted);
    line-height: 1.45;
  }

  .empty-state {
    display: grid;
    place-items: center;
    min-height: 22rem;
    padding: 2rem;
    border-radius: 1.6rem;
    text-align: center;
  }

  .empty-state div {
    display: grid;
    place-items: center;
    width: 4rem;
    height: 4rem;
    border-radius: 1.35rem;
    background: rgba(240, 154, 159, 0.1);
    color: var(--accent-strong);
    font-size: 2rem;
  }

  .empty-state h2 {
    margin: 0.9rem 0 0.2rem;
  }

  .empty-state p {
    max-width: 34rem;
    margin: 0;
    color: var(--muted);
  }

  @media (max-width: 980px) {
    .profile-grid {
      grid-template-columns: 1fr;
      overflow-y: auto;
    }

    .profile-sidebar,
    .profile-main {
      overflow: visible;
    }
  }

  @media (max-width: 760px) {
    .encyclopedia {
      overflow-y: auto;
    }

    .encyclopedia-hero,
    .encyclopedia-toolbar,
    .timeline-header {
      display: grid;
    }

    .hero-card {
      min-width: 0;
    }

    .section-toggle {
      grid-template-columns: minmax(0, 1fr) auto;
    }

    .section-toggle em {
      display: none;
    }
  }
</style>
