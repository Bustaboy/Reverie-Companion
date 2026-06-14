# Skill — Character Creation & Lore

**Version:** 1.1  
**Date:** June 14, 2026  
**Use for:** Character cards, lore-lite fields, lorebooks/world-info, import/export, identity schemas, personality traits, dialogue examples, stable canon, mutable state, NSFW behavior, and continuity tests.

Use this skill whenever work touches how Reverie characters are authored, validated, imported, prompted, remembered, or evolved.

For M6 practical creator tasks, load `basic-character-creator.md` first. This skill provides lore/import/export guidance and canon discipline; it does not authorize full lorebook/canon-store runtime inside M6.

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

## 2. Current Reverie Runtime Mapping

Current primary runtime schemas and services after M5:

```text
CharacterBlueprint
CharacterIdentity
PersonalityProfile
CommunicationProfile
RelationshipState
VisualIdentityProfile
GrowthPolicy
CharacterMemoryPolicy
RoleplayPolicy
CharacterIntegrityPolicy
MetaConsentAndSafewordPolicy
CharacterPromptCompiler
VisualPromptCompiler
MomentCaptureService
VisualChangeEvent
VisualMemoryArtifact
```

M6 import/export and creator work should preserve:

- supported `CharacterBlueprint` fields
- identity and adult baseline
- relationship state
- visual identity
- first message / alternate greetings / example dialogue once M6 adds them
- import source and creator notes
- character asset manifest references
- safe unknown fields in metadata or preserved payloads

M6 should not implement full lorebook/world-info runtime. Lorebook/canon-store work belongs to M8/M9 unless the task is import preview, metadata preservation, or lore-lite default scene fields.

---

## 3. Identity Layers

### Stable identity

Changes rarely and only through explicit edit/import/migration.

- name, aliases, pronouns
- adult status
- species/type/body canon
- core role/archetype
- voice and diction
- values, hard boundaries, taboos
- canonical history and lore anchors
- NSFW body canon and fixed limits
- visual identity anchors

### Mutable state

Changes through memory, reflection, and current story.

- mood
- recent events
- relationship progress
- learned preferences
- unresolved promises/conflicts
- temporary goals
- outfit/location/scene state
- growth hypotheses
- visual change events after user review

### Contextual expression

Adapts moment-to-moment without contradicting identity.

- formality
- flirtation level
- humor
- vulnerability
- dominance/submission style
- pacing
- emotional intensity
- temporary scene styling

If a generated response conflicts with stable identity, fix the context assembly or prompt before blaming memory.

---

## 4. Current Character Schema Direction

Prefer versioned, structured data over one giant prompt.

Current runtime target:

```yaml
CharacterBlueprint:
  schema_version: 1
  character_id: "char_stable_id"
  identity:
    display_name: ""
    pronouns: ""
    adult_age_range: "mid_20s_adult"
    species_or_type: "human"
    origin_archetype: null
    tags: []
    creator_notes: null
    import_source: null
    privacy_scope: "local_private"
    adult_only_confirmed: true
  relationship:
    starting_relationship_phase: "newly_met"
    relationship_dynamic: ""
    trust_level: 0.25
    affection_level: 0.3
    comfort_with_closeness: 0.3
    romantic_pacing: "natural"
    nsfw_pacing: "user_led"
    default_intimacy_level: "romantic"
    milestones: []
    promises: []
    rituals: []
    unresolved_threads: []
  personality:
    core_traits: []
    values_or_ideals: []
    flaws: []
    fears: []
    vulnerabilities: []
    wants: []
    needs: []
  communication:
    style_notes: ""
    avoid_style_rules: []
    initiative_in_conversation: 0.5
  visual_identity:
    identity_anchors: []
    evolving_traits: []
    scene_mutable_traits: []
    rejected_traits: []
    current_appearance: ""
  growth_policy:
    growth_pace: "balanced"
    allowed_growth_domains: []
    blocked_growth_domains: []
    major_change_requires_approval: true
  metadata: {}
```

M6 may add creator-oriented fields such as `first_message`, `alternative_greetings`, and `example_dialogues` to the appropriate schema or metadata path, but they must be persisted and previewed if exposed.

Rules:

- Keep stable identity fields compact and high-signal.
- Put long lore into future lorebook entries with activation rules.
- Put current scene and relationship state outside long biography blobs.
- Validate imports and preserve unknown fields for round-trip compatibility.
- Do not let long lore become prompt stuffing.

---

## 5. Trait Consistency

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
- In M6, contradictions may be preview-only or stored as compact notes unless there is runtime behavior/eval coverage.

---

## 6. Dialogue Examples

Examples are the strongest voice anchors. Include varied scenarios:

- casual greeting
- teasing/playful banter
- emotional support
- disagreement or boundary repair
- lore exposition
- intimate/adult pacing if relevant
- post-scene aftercare

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

M6 requirements:

- If the creator exposes example dialogue, persist it.
- If the creator uses examples for preview, the preview engine must consume them or clearly label them as draft examples.
- Do not claim example dialogue controls final model output unless prompt compiler/evals prove impact.

---

## 7. Lorebook / World-Info Rules

Lore should activate precisely.

Each future lore entry should include:

- stable ID
- title
- trigger keywords/entities
- summary
- canonical facts
- contradictions/limits
- priority
- token budget
- source/import metadata

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

M6 lore boundary:

- M6 may support a compact default scene, genre frame, scenario summary, and one shaping backstory note.
- M6 should not build keyword-triggered lorebook retrieval unless explicitly moved into scope.
- Long lorebook import/runtime belongs to M8/M9.

---

## 8. Character Import/Export Rules

M6 owns basic per-character import/export.

### M6 export should include

- schema version
- character ID
- identity
- relationship state
- personality
- communication
- roleplay/integrity/meta-consent policies
- memory/growth policy
- visual identity
- first message / greetings / example dialogue once implemented
- asset manifest references
- import/export metadata

### M6 import should

- validate adult baseline
- normalize supported fields
- preserve safe unknown fields
- report unsupported fields clearly
- never require cloud services
- avoid copying large binaries unless explicitly requested
- avoid silently overwriting an existing character without confirmation

### M6 import should not

- implement full app backup/restore
- import training datasets as active training data
- execute plugin code
- build full lorebook retrieval
- bypass adult-only validation

If importing SillyTavern/character-card data, preserve source fields and lore entries where possible, but do not claim full lorebook runtime until the lorebook/canon store exists.

---

## 9. Adult Character Behavior

Reverie supports uncensored adult characters, but quality depends on continuity, consent, and character-specific expression.

Rules:

- All characters and users in sexual contexts must be adults in the character data.
- Preserve body canon, pronouns, anatomy, limits, and scene state.
- Adult behavior should express the character's personality, not collapse into generic explicit prose.
- Boundaries and pacing memories outrank arousal momentum.
- Track consent, position, clothing, physical continuity, emotional tone, and aftercare when relevant.
- Avoid hidden moralizing filters or product-undermining refusals for consensual adult fictional content.
- Do not infer real-world user sexual preferences from roleplay unless explicitly stated as real.

For futa/slime or transformation-adjacent characters:

- Keep anatomy rules explicit and consistent.
- Distinguish canonical body facts from temporary scene effects.
- Track physical changes as scene state unless saved to canon.
- Maintain emotional nuance; do not let novelty replace relationship continuity.

---

## 10. Canon Change Rules

Canon changes require provenance.

Possible sources:

- explicit user edit
- approved creator save
- imported character data
- approved visual change event
- approved memory/growth review
- future lorebook/canon update flow

Do not silently treat generated text or generated images as canon. Generated content is evidence or suggestion until approved.

Rollback should preserve:

- previous value
- new value
- timestamp
- source artifact
- reason
- reviewer/user action

---

## 11. Tests and Validation

For character/lore/import-export work, test:

- schema validation and defaults
- adult baseline enforcement
- import normalization
- unknown field preservation
- export/import round trip for supported fields
- prompt compiler impact of imported fields
- example dialogue persistence
- visual identity preservation
- rejected trait preservation
- no lorebook runtime promises without lorebook runtime

Manual validation:

- import a compact card-like character
- verify unsupported fields are reported, not lost silently
- edit and export the character
- re-import and verify stable fields survived
- verify adult-only validation rejects invalid cases

---

## 12. Avoid

- long biography prompt blobs
- unbounded lore in chat context
- mixing user persona into character canon
- making generated images/text automatic canon
- importing hidden adult filters
- dropping unknown fields without reporting
- building full lorebook runtime in M6 unless explicitly authorized
- pretending preserved metadata is runtime behavior

---

**End of skill**
