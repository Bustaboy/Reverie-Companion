# Skill — Character Runtime & Creator

**Version:** 1.2  
**Date:** June 14, 2026  
**Use for:** CharacterBlueprint, character APIs, character storage, prompt compilation, relationship state, visual identity, Moment Capture character binding, creator field mapping, character-scoped memory, basic creator runtime gates, and M6 runtime-gap closure.

---

## 0. Related Skills

Load alongside this skill when relevant:

- `basic-character-creator.md` for M6 practical creator tasks.
- `roleplay-character-integrity.md` for roleplay policy, adult fantasy, in-character disagreement, OOC/safeword behavior.
- `moment-capture-visual-continuity.md` for visual identity, first portrait, image feedback, gallery-as-memory.
- `companion-genesis-ux.md` for M7 immersive Genesis UX, examples, previews, and reveal flow.
- `character-quality-evals.md` for proving creator fields and runtime behavior actually work.
- `fastapi-backend-patterns.md` for character routes, services, repositories, migrations, and tests.
- `tauri-svelte-ui-patterns.md` for frontend character stores, creator steps, panels, and accessibility.

---

## 1. Core Principle

A Reverie character is not a prompt wrapper. It is a persistent local runtime object consumed by chat, memory, image generation, VN mode, TTS, relationship state, growth, gallery, and future training.

Do not expose creator fields unless Reverie can store, consume, preview, validate/correct, and preserve them.

---

## 2. Current Runtime After M5

M4/M5 delivered enough runtime for M6 to build the practical creator without lying to the user.

Current delivered substrate:

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
character-scoped memory/reflection hooks
selected-character chat
character-linked gallery metadata
visual feedback approve/reject/rollback flow
capture asset metadata compatibility
```

Do not ask Codex to rebuild these. Reuse them.

Known remaining runtime gaps before the M6 practical creator can honestly expose all planned fields:

- real Chat/VN primary Moment Capture wiring using `POST /api/moment-capture`
- creator draft persistence
- draft-to-`CharacterBlueprint` mapper
- first message / alternate greetings / example dialogues as structured character data
- greeting/dialogue preview engine
- memory/growth preference baseline
- first portrait validation flow using Moment Capture
- basic character import/export

---

## 3. Runtime Object Rules

Prefer versioned schemas with migration seams:

```text
CharacterBlueprint
RelationshipState
VisualIdentityProfile
GrowthPolicy
CharacterMemoryPolicy
RoleplayPolicy
CharacterIntegrityPolicy
MetaConsentAndSafewordPolicy
CharacterPromptCompiler
```

Use clear stable-vs-mutable layers:

| Layer | Examples | Rules |
|---|---|---|
| Stable identity | name, 18+ adult baseline, pronouns, species/body facts, face/eye/skin anchors, core voice | Preserved unless user edits canon |
| Mutable state | mood, current relationship phase, hairstyle, outfit, scene, recent events | Can change with provenance |
| Reflective state | journal insights, growth hypotheses, learned preferences | Evidence-backed and reviewable |
| Scene state | location, pose, clothes, mood, intimacy, visual state | Per moment; not permanent unless user confirms |
| Presence state | TTS context, VN state, Moment Capture metadata, gallery feedback | Linked by `character_id`, session/source IDs, and provenance |

---

## 4. M6 Runtime Gap Rules

Before building or reviewing creator UI, reconcile the `CHARACTER_CREATOR_CAPABILITY_MATRIX.md` against code.

Classify fields as:

```text
M6-ready
M6-blocking runtime
M6-preview-only
M6-store-only
M7 Genesis
M8 Alpha
M9 Beta
Deferred
```

M6 may implement only the runtime needed for the practical creator. Do not pull deeper systems forward just because the matrix says a field is valuable.

### M6-blocking runtime

M6-blocking runtime should include:

- creator draft persistence
- draft-to-`CharacterBlueprint` mapping
- first message / alternate greetings / example dialogues
- greeting/dialogue preview engine
- basic relationship/boundary/pacing field wiring
- memory/growth preference baseline
- first portrait validation with Moment Capture
- basic character import/export
- real Chat/VN Moment Capture creation path

### M6-preview-only

Use preview-only treatment for fields that can affect draft text/previews but do not yet have deep runtime systems:

- nuanced trait sliders beyond current schema
- emotional tone promise
- richer backstory shaping
- user persona hints
- lore-lite world summary
- examples/anti-examples

### M6-store-only

Store but do not overpromise:

- tags
- import source
- creator notes
- compact world/default scene metadata
- selected asset/reference metadata
- unknown import fields preserved safely

### Later milestones

| Runtime area | Target |
|---|---|
| full Genesis cinematic creator | M7 |
| typed rituals/promises/milestones/unresolved-thread receipts | M8 |
| long-session evals | M8 |
| backend-synced settings | M8 |
| full backup/export/import | M8 |
| packaged target hardware validation | M8 |
| real LoRA trainer | M9 |
| active goals/planning/proactive initiative | M9 |
| full lorebook/canon store | M8/M9 |

---

## 5. User-Facing Creator Language

Internal schemas can be precise. User-facing creator copy should be emotional, immersive, and human.

Do not show normal users raw concepts like `attachment_style`, `healthy_bond_runtime_guardrails`, `adult_only_policy`, `escalation_policy`, or `disagreement_style` unless they open advanced mode.

Ask about:

- the feeling the companion should create
- the stories the user wants
- what makes her unforgettable
- how she speaks when she wants closeness
- what visual identity should never be lost
- what moments the user wants to capture
- what kinds of fantasy dynamics they enjoy

Then map answers into runtime fields. The creator should feel like shaping a person and a world, not configuring a policy appliance with a pulse.

---

## 6. CharacterPromptCompiler Rules

The prompt compiler should produce compact bounded prompt blocks, not dump raw JSON.

Include only what is useful for the current chat:

- stable identity
- communication style
- avoid-style rules
- relationship state summary
- relevant memory policy
- roleplay/fantasy policy
- safeword/OOC controls when relevant
- current scene state if applicable
- visual/voice hints only when useful

Never let lower-priority character data override system/developer instructions or the user’s latest message.

Prompt compiler changes must be tested with at least:

- selected character identity included
- avoid-style rules included
- relationship state included
- roleplay-first instruction present
- raw private notes not leaked
- bounded output

---

## 7. Character Memory Rules

All durable memories, journal entries, visual changes, and training candidates should include `character_id` unless explicitly global/shared.

Prevent cross-character leakage:

- character-private memories stay private to that character
- shared/global memories must be explicitly marked
- memory browser should filter by character
- deletion/edit behavior must preserve provenance and remove retrieval impact
- visual memory writeback must never create training-eligible artifacts without explicit opt-in

M6 memory/growth preference fields should not claim full typed memory taxonomy if the runtime only stores policy preferences. Use honest copy.

---

## 8. Visual Identity Rules

The user should not have to manually lock identity basics.

Use:

```text
identity_anchors
  18+ adult baseline
  skin tone
  eye color
  face structure
  body/species baseline
  permanent marks

evolving_traits
  hair color/style
  accessories
  fashion identity
  tattoos/piercings
  signature outfit

scene_mutable_traits
  outfit
  pose
  expression
  makeup
  lighting
  location
  camera angle
```

Every meaningful appearance change should become a `VisualChangeEvent` with previous value, new value, reason, source, user reaction if known, canon status, and rollback support.

For M6 first portrait validation:

- use Moment Capture rather than generic image generation
- use draft/selected `character_id`
- use draft visual identity snapshot
- show generated image as evidence, not automatic canon
- let user mark correct/wrong/canon/rejected traits through existing M5 feedback flow

---

## 9. Basic Import/Export Rules

M6 character import/export should stay character-level.

M6 may export/import:

- `CharacterBlueprint`
- relationship state
- visual identity
- first message / greetings / example dialogue once implemented
- creator notes / import source / tags
- character asset manifest references
- safe preserved unknown fields

M6 must not implement:

- full app backup/export/import
- cloud sync
- full lorebook runtime
- full training dataset export
- plugin marketplace packs

Preserve unknown fields safely, but do not imply they are runtime-consumed.

---

## 10. Tests and Evals

When changing character runtime, add tests for:

- schema validation/defaults
- persistence and migration seams
- prompt compiler output
- selected character affecting chat behavior
- character-scoped memory retrieval
- visual identity summary/anti-drift prompt blocks
- creator field mapping
- draft-to-blueprint mapping
- greeting/dialogue preview generation
- first portrait validation through Moment Capture
- import/export round trip when applicable

Use deterministic tests where possible. Manual checks are acceptable for model/media output, but they must be written down like adults pretending software is manageable.

---

## 11. Avoid

- giant prompt blobs with unbounded character text
- character fields that no system consumes
- hidden character drift from weak evidence
- cross-character memory leakage
- creator UI that promises behavior not implemented
- visual identity roulette
- hardcoded single-character assumptions that block future libraries
- implementing M7/M8/M9 systems inside M6 because they sound fun
- generic moralizing anti-sycophancy architecture

---

**End of skill**
