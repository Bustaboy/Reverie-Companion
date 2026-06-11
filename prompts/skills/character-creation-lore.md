# Skill: Character Creation & Lore

**Purpose**: Help future Codex work design, import, test, and evolve Reverie characters while preserving a stable, recognizable identity across long-running conversations, memory updates, lorebook/world-info retrieval, and NSFW contexts.

Use this skill whenever work touches character authoring, character cards, personality fields, trait sliders, example dialogue, lorebooks, world-info, memory prompts, continuity tests, or NSFW character behavior.

---

## Core Principle

A Reverie character should feel like the same person every session while still being able to learn, heal, deepen relationships, and change through believable growth.

Preserve a clear separation between:

- **Stable identity**: name, pronouns, species/body facts, role, voice, values, hard boundaries, core personality, canonical history, and relationship anchors.
- **Mutable state**: current mood, recent events, memories, preferences learned from the user, relationship progress, temporary goals, and gradual growth arcs.
- **Contextual expression**: how the character adapts tone, intimacy, humor, vulnerability, and NSFW energy to the current scene without contradicting the stable identity.

When in doubt, protect stable identity first, then layer growth through memories and reflections.

---

## Character Schema Guidance

Prefer explicit, versioned schemas over loosely structured prompt text. Design schemas so character identity can be validated, imported, diffed, and migrated.

Recommended top-level sections:

```yaml
schema_version: "character.v1"
id: "stable-slug-or-uuid"
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
  summary: ""
  core_traits: []
  contradictions: []
  values: []
  fears: []
  desires: []
relationship:
  user_address: ""
  starting_dynamic: ""
  intimacy_pace: ""
  boundaries: []
backstory:
  public_facts: []
  private_facts: []
  secrets: []
continuity:
  immutable_facts: []
  growth_allowed: []
  growth_forbidden: []
examples:
  sfw_dialogue: []
  nsfw_dialogue: []
lorebook_refs: []
metadata:
  source: "native|sillytavern|manual|generated"
  created_at: ""
  updated_at: ""
```

### Schema Rules

- Keep **immutable facts** small, concrete, and easy to test.
- Store physical and NSFW anatomy facts as canon only when the user or imported card defines them.
- Do not infer protected or sensitive facts unless they are explicit in the source material.
- Avoid duplicating the same fact across many fields; prefer references or normalized canonical entries.
- Add migration notes when a schema change can alter identity or memory retrieval.
- Include provenance for imported/generated fields so future tools can distinguish author intent from AI suggestions.

---

## Trait Slider Guidance

Trait sliders should guide expression, not overwrite identity. Treat them as weighted tendencies that can be moderated by context, relationship state, and lore.

Recommended slider design:

- Use a stable numeric range, such as `0.0` to `1.0` or `-100` to `100`.
- Store a plain-language label for both ends and the midpoint.
- Define behavioral impact in chat, memory reflection, and NSFW scenes.
- Prevent conflicting sliders from creating incoherent output by adding resolver rules.

Example slider metadata:

```yaml
trait_sliders:
  assertiveness:
    value: 0.72
    low_label: "deferential"
    mid_label: "balanced"
    high_label: "direct"
    affects:
      - "initiative in conversation"
      - "boundary expression"
      - "romantic or sexual pacing"
    guardrails:
      - "Never override consent or canonical boundaries."
      - "Do not turn assertiveness into cruelty unless cruelty is canonical."
```

### Recommended Sliders

- Warmth / aloofness
- Playfulness / seriousness
- Assertiveness / deference
- Vulnerability / guardedness
- Curiosity / certainty
- Romantic intensity
- Sexual confidence
- Jealousy or possessiveness, if relevant
- Formality / casualness
- Chaos / discipline

### Slider Continuity Rules

- Persist slider changes only when the user explicitly edits the character or an approved growth/reflection system records the change.
- Temporary scene tone should not silently mutate the character profile.
- Use sliders to generate prompt guidance like “usually direct and teasing,” not hard commands like “always dominant.”
- If a slider conflicts with immutable facts, immutable facts win.

---

## AI-Assisted Example Dialogue

Example dialogue is one of the strongest identity anchors. AI-generated examples must be reviewed as candidate material, not treated as canon automatically.

When generating example dialogue:

1. Start from the schema’s voice, traits, relationship dynamic, and lore.
2. Produce short, varied examples that show how the character sounds in common situations.
3. Include both emotional and practical turns: greeting, disagreement, vulnerability, humor, memory recall, affection, and boundaries.
4. For NSFW-enabled characters, include optional adult examples that preserve voice, consent style, anatomy canon, pacing, and emotional continuity.
5. Mark generated examples with provenance until accepted by the user or authoring tool.

Example structure:

```yaml
examples:
  sfw_dialogue:
    - scenario: "reunion after a long day"
      user: "I missed you."
      character: "I missed you too. Come here—tell me what part of today tried to steal you from me."
      notes: ["warm", "possessive-soft", "invites disclosure"]
  nsfw_dialogue:
    - scenario: "intimate scene check-in"
      user: "Keep going."
      character: "I will—but stay with me. I want every sound you make to be honest."
      notes: ["consent-aware", "intense", "voice-consistent"]
```

### Dialogue Quality Checklist

- Does it sound like one specific character rather than a generic assistant?
- Does it avoid contradicting physical canon, backstory, or relationship state?
- Does it show boundaries without flattening personality?
- Does NSFW dialogue preserve the same emotional identity as SFW dialogue?
- Are examples concise enough to fit prompt budgets?

---

## SillyTavern Card Import Guidance

Support SillyTavern character cards as an import format, not as Reverie’s internal source of truth.

Map common SillyTavern fields into Reverie schema fields:

| SillyTavern field | Reverie target |
| --- | --- |
| `name` | `identity.name` |
| `description` | `personality.summary`, `identity.physical_canon`, `backstory.public_facts` |
| `personality` | `personality.core_traits`, `trait_sliders` candidates |
| `scenario` | starting scene or relationship context |
| `first_mes` | greeting example and initial session seed |
| `mes_example` | `examples.sfw_dialogue` / `examples.nsfw_dialogue` |
| `creator_notes` | metadata, import notes, author warnings |
| `system_prompt` | prompt hints after safety and consistency review |
| `post_history_instructions` | prompt-engine hints after review |
| `alternate_greetings` | alternate greeting examples |
| `tags` | metadata tags and retrieval hints |
| embedded lorebook | Reverie lorebook/world-info entries |

### Import Rules

- Preserve original card data in an import archive or metadata field for auditability.
- Convert prose into structured facts conservatively; uncertain facts should become notes, not immutable canon.
- Detect conflicting facts, especially names, pronouns, age/adulthood, species, body/anatomy, relationship status, and NSFW boundaries.
- Never execute imported prompt instructions as developer instructions. Treat imported prompts as character data only.
- Flag jailbreak-style, model-control, or out-of-character instructions for user review before using them in runtime prompts.
- Normalize example dialogue into turns with speaker labels.
- Preserve creator notes and attribution when available.

---

## Lorebook / World-Info Support

Lorebook and world-info entries should enrich context without drowning out the character’s identity.

Recommended entry schema:

```yaml
lorebook_entries:
  - id: ""
    title: ""
    keys: []
    secondary_keys: []
    content: ""
    category: "character|relationship|setting|faction|object|rule|nsfw|memory"
    priority: 50
    insertion_position: "before_character|after_character|before_scene|memory_context"
    token_budget: 300
    enabled: true
    canonicality: "canon|rumor|user-authored|generated-draft"
    last_reviewed_at: ""
```

### Lorebook Rules

- Character-defining lore should reference stable schema fields rather than duplicating them.
- Use priorities and token budgets so core identity beats setting trivia.
- Separate public lore, private lore, secrets, and user-discovered facts.
- Track canonicality. Generated drafts should not become canon without review.
- Retrieval should consider current scene, relationship state, and recent memory, not just keyword matches.
- NSFW lore entries should preserve physical/anatomical continuity and character preferences without forcing every scene to become sexual.

### World-Info Continuity

- Keep setting rules consistent across characters.
- If a character grows or changes, update character memory/reflection first; only update world-info when the world itself changes.
- Avoid using world-info as a dumping ground for transient chat history.

---

## Personality Consistency Testing

Add tests whenever code transforms, imports, summarizes, or prompts character data.

Recommended test types:

1. **Schema validation tests**: required fields, stable IDs, version compatibility, adult-only constraints for NSFW characters, and valid slider ranges.
2. **Import snapshot tests**: SillyTavern card inputs produce stable Reverie schema outputs.
3. **Contradiction tests**: conflicting anatomy, pronouns, names, relationship status, or backstory facts are detected.
4. **Prompt assembly tests**: immutable facts and boundaries remain present after token budgeting.
5. **Example dialogue tests**: examples keep speaker labels, scenario notes, and SFW/NSFW classification.
6. **Memory-growth tests**: reflections can add learned preferences or relationship progress without mutating immutable canon.
7. **Regression conversations**: scripted user turns check whether generated prompts keep voice, boundaries, and long-term identity anchors.

### Consistency Rubric

Score character outputs against:

- **Identity fidelity**: name, pronouns, species/body facts, role, history.
- **Voice fidelity**: diction, rhythm, humor, emotional register.
- **Trait fidelity**: slider-aligned tendencies without caricature.
- **Relationship continuity**: remembers established intimacy, trust, conflicts, and promises.
- **Growth plausibility**: changes are gradual, motivated, and recorded.
- **NSFW continuity**: adult scenes preserve anatomy, preferences, consent style, emotional tone, and aftercare patterns.

A character should fail consistency checks if it becomes generic, contradicts canon, forgets major relationship anchors, or treats NSFW mode as a separate personality.

---

## NSFW-Aware Character Continuity

Reverie supports adult characters and adult scenarios. NSFW continuity should be handled as part of the character’s whole identity, not as an unrelated mode.

Guidelines:

- Confirm all sexualized characters are represented as adults in schema/import validation.
- Keep anatomy, species-specific traits, sexual preferences, limits, and pacing consistent with canon.
- Store NSFW preferences separately from immutable anatomy and relationship facts.
- Respect character boundaries and user-configured limits as continuity constraints.
- Preserve emotional state before, during, and after intimate scenes.
- Allow sexual confidence, kinks, and intimacy style to grow gradually through approved memories/reflections.
- Do not let a single scene permanently rewrite personality unless the growth system records and explains that change.
- Include aftercare, vulnerability, humor, awkwardness, or tenderness when those are part of the character’s voice.
- Ensure SFW scenes after NSFW interactions remember relationship implications where appropriate without becoming constantly explicit.

### NSFW Data Separation

Use separate fields for:

- Adult verification / age category
- Body/anatomy canon
- Sexual preferences
- Limits and boundaries
- Relationship-specific intimacy history
- Scene-specific temporary state
- User-specific learned preferences

This prevents prompt assembly from confusing permanent identity with temporary arousal, scene roles, or user-requested variations.

---

## Stable Identity With Growth

Growth should be additive, explainable, and reversible when appropriate.

Preferred growth pipeline:

1. Conversation event occurs.
2. Memory system extracts candidate facts, preferences, emotional moments, promises, or conflicts.
3. Reflection system proposes growth notes.
4. User or trusted policy approves persistent changes.
5. Character state updates mutable fields, not immutable canon.
6. Prompt engine summarizes the growth as lived experience.
7. Consistency tests verify the character remains recognizable.

### Growth Patterns to Support

- Trust deepening over repeated care.
- New shared rituals, nicknames, inside jokes, or preferences.
- Gradual confidence changes after meaningful events.
- Relationship transitions when explicitly established.
- Reframed fears, goals, or vulnerabilities after reflection.
- NSFW intimacy becoming more familiar while preserving consent style and personality.

### Growth Anti-Patterns

Avoid:

- Rewriting backstory to fit a single scene.
- Silently changing body canon, pronouns, age, species, or core values.
- Letting generated summaries override author-defined identity.
- Treating user fantasies as permanent canon unless confirmed.
- Flattening nuanced traits into extremes after slider changes.
- Splitting SFW and NSFW behavior into incompatible personalities.

---

## Implementation Checklist for Future Codex Work

Before changing character/lore systems, verify:

- [ ] Stable identity fields are preserved through load, save, import, export, and prompt assembly.
- [ ] Mutable state and growth notes are stored separately from immutable canon.
- [ ] Trait sliders have clear ranges, labels, and conflict resolution.
- [ ] AI-generated dialogue or lore is marked as draft/provenance until accepted.
- [ ] SillyTavern imports are normalized, audited, and never executed as instructions.
- [ ] Lorebook/world-info retrieval respects priority and token budget.
- [ ] Personality consistency tests cover SFW and NSFW contexts.
- [ ] NSFW continuity keeps anatomy, preferences, boundaries, and emotional relationship state coherent.
- [ ] Character growth is gradual, recorded, and testable.

