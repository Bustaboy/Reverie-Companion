# Skill — Basic Character Creator

**Version:** 1.0  
**Date:** June 14, 2026  
**Use for:** M6 practical character creator, creator draft persistence, M6 field exposure, draft-to-`CharacterBlueprint` mapping, greeting/dialogue previews, first portrait validation, basic character import/export, edit/duplicate/delete flows, and creator-field capability honesty.

---

## 1. Purpose

Milestone 6 builds the honest practical creator. It is not Companion Genesis.

The practical creator exposes only fields Reverie can currently store, consume, preview, validate/correct, and preserve. It should feel warm and companion-native, but it must not pretend deeper runtime systems exist just because a field sounds emotionally shiny. That road leads directly to feature cosplay, and we have enough fog machines in software already.

M6 should turn user-facing answers into durable, versioned runtime data consumed by:

- `CharacterBlueprint`
- `CharacterPromptCompiler`
- `RelationshipState`
- `VisualIdentityProfile`
- `GrowthPolicy`
- `CharacterIntegrityPolicy`
- `MetaConsentAndSafewordPolicy`
- selected-character chat
- Moment Capture / first portrait validation
- character-scoped memory and visual memory writeback

---

## 2. Required Context

Before implementing or reviewing M6 creator work, load:

1. `Reverie_Source_of_Truth.md`
2. `DEVELOPMENT_PLAN.md`
3. `CHARACTER_CREATOR_CAPABILITY_MATRIX.md`
4. `ROLEPLAY_FIRST_CHARACTER_INTEGRITY_POLICY.md`
5. `prompts/GLOBAL_CODING_PROMPT.md`
6. `prompts/skills/character-runtime-creator.md`
7. `prompts/skills/character-quality-evals.md`
8. `prompts/skills/tauri-svelte-ui-patterns.md`
9. `prompts/skills/fastapi-backend-patterns.md`

Load additionally when relevant:

| Task area | Also load |
|---|---|
| Roleplay boundaries, OOC, safeword, adult fantasy policy | `prompts/skills/roleplay-character-integrity.md` |
| First portrait, visual identity, image feedback | `prompts/skills/moment-capture-visual-continuity.md`, `prompts/skills/8gb-vram-optimization.md` |
| Basic import/export and lore-lite fields | `prompts/skills/character-creation-lore.md` |
| Any memory/growth preference work | `prompts/skills/memory-rag-system.md`, `prompts/skills/self-learning-growth.md` |

---

## 3. M6 Scope

M6 may implement:

- creator draft persistence
- draft autosave and resume
- basic identity and companion premise steps
- personality and communication steps with examples and anti-examples
- roleplay policy summary and safeword/OOC controls
- visual identity anchors and current appearance fields
- basic asset/reference attachment metadata
- first portrait validation through Moment Capture
- world/default scene/lore-lite fields
- memory/growth preference baseline
- greeting and dialogue preview engine
- character review/save/edit/duplicate/import/export/delete
- creator field-impact tests and accessibility checks

M6 must not implement:

- immersive Companion Genesis starfield/celestial flow
- cinematic transitions or world-reveal ceremony
- multi-draft Genesis ritual
- real LoRA/image/video training
- proactive agency/planning
- full lorebook/canon store
- typed promise/ritual/milestone lifecycle receipts
- long-session memory/growth eval suite
- packaged target-hardware validation
- backend-synced settings migration
- cloud-required creator services
- hidden adult-fantasy filtering

If a task starts drifting into M7/M8/M9, stop and split it. Scope creep wearing perfume is still scope creep.

---

## 4. Field Exposure Rules

### 4.1 Main M6 creator fields

The main practical creator may expose:

| Area | Fields |
|---|---|
| Basic identity | display name, pronouns, adult age range, species/type, tags |
| Companion premise | companion mode, relationship dynamic, starting relationship phase, user desired experience |
| Pacing and intimacy | default intimacy level, romantic pacing, NSFW pacing, relationship pacing, safeword/OOC controls |
| Personality | personality summary, core traits, warmth, boldness, playfulness, tenderness, intensity, independence baseline |
| Communication | style notes, avoid-style rules, initiative, first message, alternate greetings, example dialogues |
| Visual identity | identity anchors, current appearance, evolving traits, scene-mutable traits, rejected traits, adult visual baseline |
| World/default scene | default setting, genre frame, compact scenario, one shaping backstory note |
| Memory/growth | memory enabled summary, remember categories, never-remember categories, growth pace, approval required for major changes |
| Validation | greeting preview, dialogue preview, first portrait validation, final blueprint review |

### 4.2 Hidden, internal, or advanced-only in M6

These may be stored or shown in advanced review, but should not become big main-flow promises:

- `attachment_style`
- `healthy_bond_runtime_guardrails`
- `relationship_state_vector`
- raw `adult_only_policy`
- raw `escalation_policy`
- raw `disagreement_style`
- `active_goals`
- full milestone/promise/ritual receipt lifecycle
- lorebook entries
- custom lore files
- real trainer settings
- backend sync settings

### 4.3 M7/M8/M9 fields

| Field group | Later milestone |
|---|---|
| Immersive Genesis UX, starfield, ceremony, constellation choices | M7 |
| Full lorebook/canon store | M8/M9 |
| Relationship timeline receipts for milestones, promises, rituals, unresolved threads | M8 |
| Long-session memory/growth evals | M8 |
| Packaged Tauri target-hardware validation | M8 |
| Active goals, planning, proactive initiative | M9 |
| Real LoRA/adapter trainer | M9 |
| Advanced visual evolution beyond M5 review flow | M9 |

---

## 5. Creator Draft Model

Use a draft model rather than writing incomplete character data directly into the durable character library.

Recommended shape:

```text
CharacterCreatorDraft
  draft_id
  schema_version
  current_step
  completed_steps
  identity
  premise
  personality
  communication
  roleplay
  visual_identity
  world
  memory_growth
  previews
  validation_notes
  source_import
  created_at
  updated_at
```

Rules:

- Drafts may be incomplete.
- Saved characters must validate as full `CharacterBlueprint` objects.
- Drafts should autosave locally.
- Drafts should be resumable after app reload.
- Drafts should not pollute the main character list until the user saves.
- Drafts should store user-facing choices and the mapped internal fields.

Losing a 30-minute companion draft is a villain-origin-story bug. Do not create villain-origin-story bugs.

---

## 6. Draft-to-Blueprint Mapping Rules

Every main-flow field must map to a current runtime field or remain preview-only.

Examples:

| User-facing answer | Runtime target |
|---|---|
| “Her name is Aria.” | `identity.display_name` |
| “She uses she/her.” | `identity.pronouns` |
| “Clearly adult, early 20s.” | `identity.adult_age_range`, `visual_identity.adult_only_policy` |
| “Slow-burn romantic companion.” | `relationship.relationship_dynamic`, `relationship.starting_relationship_phase`, `relationship.relationship_pacing` |
| “Warm, playful, lightly teasing.” | `personality.core_traits`, `communication.style_notes` |
| “Never sound like a customer support bot.” | `communication.avoid_style_rules` |
| “Safeword is red.” | `meta_consent_policy.safeword`, `pause_commands` |
| “Amber eyes, warm brown skin, same face.” | `visual_identity.identity_anchors` |
| “Long black-violet hair.” | `visual_identity.current_appearance` or `evolving_traits` |
| “Rainy neon apartment.” | draft world/default scene metadata and preview context |
| “Remember boundaries, preferences, favorite images.” | `memory_policy`, `growth_policy`, and M6 memory preference baseline |

Mapping code should be deterministic and tested. If two Codex runs map the same answer to wildly different fields, the prompt was not ready. A tragedy, but the kind we can prevent.

---

## 7. Preview Requirements

Every major creator step needs a preview or correction loop.

Required M6 previews:

1. **Summary preview** — what the creator thinks the user chose.
2. **Greeting preview** — first message in character voice.
3. **Dialogue preview** — scenario response using draft fields.
4. **Avoid-style preview** — anti-example or regression cue for “do not sound like this.”
5. **Visual identity preview** — compact canonical visual summary.
6. **First portrait validation** — optional Moment Capture path using draft/selected character data.
7. **Final blueprint review** — what will actually be saved.

Recommended dialogue scenarios:

- first greeting
- user had a bad day
- user flirts lightly
- user teases her
- user sets a boundary
- user asks her to remember something
- quiet romantic moment
- conflict repair
- optional adult-intensity/pacing check when adult mode is enabled

Preview output must not permanently change character canon unless the user saves or approves.

---

## 8. First Portrait Validation

M6 may use M5 Moment Capture for first portrait validation.

Rules:

- Use the real Moment Capture API/service path, not generic image generation.
- Use selected/draft `character_id`.
- Use the draft `VisualIdentityProfile` snapshot.
- Preserve `prompt_hash`, scene state, capture metadata, and feedback state.
- First portrait feedback can propose visual changes, but generated images are evidence, not automatic truth.
- Identity anchors must remain protected.
- Rejected traits must feed negative prompt guidance.
- If local image generation is unavailable, show a non-blocking fallback and allow creator save without portrait validation.

M6 first portrait validation should feel like: “Does this feel like her?” not “prompt seed 814xCFG nightmare settings.” We are building a companion, not a slot machine with cheekbones.

---

## 9. Basic Import/Export Rules

M6 owns basic per-character import/export. Full backup/export/import belongs to M8.

M6 import/export should:

- export a single character blueprint with supported fields
- include visual identity and relationship state
- include first message / alternate greetings / example dialogue once M6 adds them
- include character asset manifest references where available
- preserve safe unknown fields under metadata or preserved import payloads
- reject invalid adult baseline
- never require cloud services
- avoid copying large binaries unless explicitly requested
- report what was imported, skipped, preserved, or unsupported

M6 must not implement:

- full app backup
- encrypted sync
- plugin marketplace packages
- full lorebook import runtime
- real training dataset export

---

## 10. Tests and Evals

Required backend tests:

- draft model validation/defaults
- draft-to-`CharacterBlueprint` mapping
- invalid adult baseline rejected
- first message / alternate greetings / example dialogues persist
- roleplay/OOC/safeword controls persist and compile
- memory/growth preferences map correctly
- basic import/export round trip preserves supported fields
- unsupported/deferred fields are preserved or reported without pretending runtime support

Required frontend tests/checks:

- draft autosaves and reloads
- step navigation works
- examples and anti-examples render
- greeting/dialogue preview request state renders
- first portrait validation can be queued/cancelled or gracefully unavailable
- final review displays saved fields accurately
- accessibility labels and keyboard navigation are present

Required evals/manual checks:

- two distinct draft characters produce distinct preview prompts
- avoid-style rules affect preview context
- roleplay-first policy does not moralize fictional adult fantasy
- OOC stop/safeword controls are visible and stored
- first portrait uses Moment Capture metadata
- imported character can be edited and exported again

---

## 11. Review Rubric

Grok should score M6 creator implementations on:

| Dimension | What to check |
|---|---|
| Capability honesty | Does every visible field have storage, runtime consumption, preview, correction, and persistence? |
| Mapping correctness | Do user-facing answers map cleanly into existing runtime schemas? |
| UX warmth | Does the creator feel companion-native rather than clinical/config-heavy? |
| Roleplay freedom | Does it preserve adult fictional fantasy without moralizing? |
| Trust/control | Are previews, corrections, import/export, and delete flows clear? |
| 8GB discipline | Are image/audio previews optional, cancellable, and non-blocking? |
| Accessibility | Keyboard, labels, reduced motion, and readable states. |
| Scope control | Does it avoid M7/M8/M9 work? |
| Tests | Are storage, mapping, preview, import/export, and field impact covered? |

Winner is not the flashiest creator. Winner is the one that tells the truth and makes the runtime stronger.

---

**End of skill**
