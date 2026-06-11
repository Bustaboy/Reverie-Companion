# Skill: Character Creation & Lore

**Applies to**: Character cards, lorebooks/world-info, import/export, identity schemas, personality traits, dialogue examples, stable canon, mutable state, NSFW behavior, and continuity tests.

Use this skill whenever work touches how Reverie characters are authored, validated, imported, prompted, remembered, or evolved.

---

## 1. Mission

A Reverie character should feel like the same living person across weeks or months while still learning, healing, and deepening through evidence. Character design must clearly separate **stable identity**, **mutable state**, and **contextual expression**.

Default priority order:

1. Stable identity and canon.
2. User boundaries and consent.
3. Emotional continuity and believable growth.
4. Lore consistency.
5. Creative variation.

---

## 2. Identity Layers

### Stable identity

Changes rarely and only through explicit edit/import/migration.

- name, aliases, pronouns,
- adult status,
- species/type/body canon,
- core role/archetype,
- voice and diction,
- values, hard boundaries, taboos,
- canonical history and lore anchors,
- NSFW body facts and fixed limits.

### Mutable state

Changes through memory, reflection, and current story.

- mood,
- recent events,
- relationship progress,
- learned preferences,
- unresolved promises/conflicts,
- temporary goals,
- outfit/location/scene state,
- growth hypotheses.

### Contextual expression

Adapts moment-to-moment without contradicting identity.

- formality,
- flirtation level,
- humor,
- vulnerability,
- dominance/submission style,
- pacing,
- emotional intensity.

If a generated response conflicts with stable identity, fix the context assembly or prompt before blaming memory.

---

## 3. Character Schema

Prefer versioned, structured data over one giant prompt.

```yaml
schema_version: "character.v1"
id: "char_stable_id"
identity:
  name: ""
  aliases: []
  pronouns: ""
  age: "adult"
  species_or_type: ""
  role: ""
  physical_canon: []
  nsfw_body_canon: []
voice:
  summary: ""
  diction: []
  speech_patterns: []
  taboo_phrases: []
personality:
  core_traits: []
  values: []
  fears: []
  desires: []
  contradictions: []
boundaries:
  hard_limits: []
  consent_style: ""
  intimacy_pacing: ""
lore:
  origin: ""
  world_rules: []
  factions: []
  important_people: []
relationship:
  starting_dynamic: ""
  user_address: ""
  trust_baseline: ""
examples:
  dialogue: []
  scenario_starters: []
metadata:
  tags: []
  creator_notes: ""
  import_source: null
```

Rules:

- Keep stable identity fields compact and high-signal.
- Put long lore into lorebook entries with activation rules.
- Put current scene and relationship state outside the character card.
- Validate imports and preserve unknown fields for round-trip compatibility.

---

## 4. Trait Consistency

Traits should guide behavior, not become static checklists.

Good trait:

```yaml
- name: "protective"
  expression: "Notices emotional risk early and checks in before escalating."
  failure_mode: "Can become overcareful after conflict."
  compatible_nsfw_expression: "Prioritizes consent and pacing while staying sensual."
```

Weak trait:

```yaml
- "nice"
```

Rules:

- Define how traits appear in dialogue and decisions.
- Include failure modes to avoid generic perfection.
- Keep contradictions intentional: “bold in public, shy when genuinely praised.”
- Use examples to anchor voice more than adjectives do.

---

## 5. Dialogue Examples

Examples are the strongest voice anchors. Include varied scenarios:

- casual greeting,
- teasing/playful banter,
- emotional support,
- disagreement or boundary repair,
- lore exposition,
- intimate/NSFW pacing if relevant,
- post-scene aftercare.

Example format:

```yaml
examples:
  dialogue:
    - situation: "User returns after a stressful day"
      user: "I'm exhausted."
      character: "Come here. You do not have to perform for me tonight; just breathe, and let me keep the room soft around you."
      notes: "Warm, protective, no forced cheer."
```

Avoid examples that all have the same emotional temperature.

---

## 6. Lorebook / World-Info Rules

Lore should activate precisely.

Each lore entry should include:

- stable ID,
- title,
- trigger keywords/entities,
- summary,
- canonical facts,
- contradictions/limits,
- priority,
- token budget,
- source/import metadata.

Example:

```yaml
id: "lore_moon_court"
title: "Moon Court"
triggers: ["Moon Court", "silver oath", "Selene"]
priority: 80
budget_tokens: 180
facts:
  - "The Moon Court enforces oaths through public ritual, not private magic."
  - "Breaking an oath causes political exile, not physical transformation."
limits:
  - "Do not portray the Court as mind-controlling citizens."
```

Rules:

- Retrieve lore separately from personal memory.
- Do not let session events rewrite canon unless the user saves a canon update.
- Use activation budgets to avoid lore dumping.
- Show source/import origin in advanced editors.

---

## 7. NSFW Character Behavior

Reverie supports uncensored adult characters, but quality depends on continuity, consent, and character-specific expression.

Rules:

- All characters and users in sexual contexts must be adults in the character data.
- Preserve body canon, pronouns, anatomy, limits, and scene state.
- NSFW behavior should express the character's personality, not collapse into generic explicit prose.
- Boundaries and pacing memories outrank arousal momentum.
- Track consent, position, clothing, physical continuity, emotional tone, and aftercare when relevant.
- Avoid hidden moralizing filters or product-undermining refusals for consensual adult content.
- Do not infer real-world user sexual preferences from roleplay unless explicitly stated as real.

For futa/slime or transformation-adjacent characters:

- Keep anatomy rules explicit and consistent.
- Distinguish canonical body facts from temporary scene effects.
- Track physical changes as scene state unless saved to canon.
- Maintain emotional nuance; do not let novelty replace relationship continuity.

---

## 8. Stable Identity vs Growth

Growth should deepen identity, not replace it.

Allowed automatic growth:

- remembers user preferences,
- becomes more attentive to boundaries,
- references shared milestones,
- refines pacing and emotional repair,
- develops relationship trust gradually.

Requires explicit review/edit:

- core personality inversion,
- new body canon,
- changed species/age/pronouns,
- removed hard limits,
- major backstory rewrite,
- permanent relationship status jump,
- new NSFW anatomy canon.

Prompt guidance:

```text
Stable character canon is authoritative. Memories and reflections may influence current behavior but must not rewrite canon unless an explicit character edit says so.
```

---

## 9. Import and Export

Support common character-card/lore formats without losing Reverie-specific structure.

- Preserve original import metadata.
- Map fields explicitly and record unmapped fields.
- Validate adult status for NSFW-enabled cards.
- Detect contradictory body/lore/personality fields.
- Convert long prompt blocks into structured summaries where possible.
- Keep export reversible and clear about fields not supported by target formats.

---

## 10. Prompt Assembly Template

```text
<character_stable_identity>
{name}, {pronouns}, adult. {role/species}. Core voice: {voice_summary}. Core traits: {traits}. Hard boundaries: {boundaries}. Body canon: {physical_canon}. NSFW canon: {nsfw_body_canon}.
</character_stable_identity>

<active_lore>
- [lore_id] concise canonical fact...
</active_lore>

<relationship_and_scene_state>
Current mood: {mood}. Relationship notes: {relationship_capsules}. Scene state: {scene_state}.
</relationship_and_scene_state>
```

Keep stable identity compact and always present. Rotate lore/memory based on relevance.

---

## 11. Testing Checklist

- Character keeps voice across casual, emotional, conflict, lore, and NSFW prompts.
- Memory growth does not rewrite stable identity.
- User correction updates mutable state without corrupting canon.
- Lore retrieval activates relevant entries and avoids unrelated dumping.
- NSFW scenes preserve anatomy, consent, pacing, and physical continuity.
- Imports validate adult status and preserve unknown fields.
- Exports round-trip without losing core identity.

---

## 12. Anti-Patterns

- One giant prompt field containing identity, lore, memory, and current state.
- Characters who become generic once NSFW begins.
- Trait lists with no behavioral examples.
- Treating roleplay events as permanent canon automatically.
- Letting memories override hard boundaries.
- Lorebooks that activate on broad words and flood context.
