# Skill — Character Quality Evals

**Version:** 1.1  
**Date:** June 14, 2026  
**Use for:** Tests/evals for character runtime, prompt compiler, creator field impact, M6 creator readiness, memory recall, relationship continuity, roleplay integrity, visual identity consistency, Moment Capture quality, and long-session companion behavior.

---

## 1. Purpose

Reverie should not ship creator fields or runtime behavior based on vibes alone. Vibes matter, but they are not a test suite. Cruel, yes. Necessary, also yes.

This skill helps Grok and Codex define practical evals so two implementation runs can be compared with evidence.

---

## 2. Required Context

Load these before implementation or review:

- `Reverie_Source_of_Truth.md`
- `DEVELOPMENT_PLAN.md`
- `CHARACTER_CREATOR_CAPABILITY_MATRIX.md`
- `ROLEPLAY_FIRST_CHARACTER_INTEGRITY_POLICY.md`
- `prompts/GLOBAL_CODING_PROMPT.md`
- relevant domain skills for the feature under test

For M6 creator work, also load:

- `prompts/skills/basic-character-creator.md`
- `prompts/skills/character-runtime-creator.md`
- `prompts/skills/tauri-svelte-ui-patterns.md` for frontend creator surfaces
- `prompts/skills/fastapi-backend-patterns.md` for backend creator routes/services
- `prompts/skills/moment-capture-visual-continuity.md` for first portrait validation

---

## 3. Eval Categories

### 3.1 Character blueprint impact

Tests should prove selected character data changes runtime output.

Check:

- prompt compiler includes the selected character identity
- two different characters produce different compiled prompt blocks
- communication style affects preview prompts
- avoid-list entries appear in prompt constraints
- relationship seed appears in compact runtime context
- roleplay policy is included without moralizing language
- visual identity summary appears only when relevant
- raw private notes and raw blueprint JSON are not leaked

### 3.2 Dialogue style consistency

Use scenario prompts for:

- greeting
- user had a bad day
- user flirts
- user teases
- user sets a boundary
- user asks her to remember something
- conflict repair
- quiet intimate moment
- fantasy/adult roleplay context when relevant

Assert or manually score:

- character voice preserved
- selected traits visible
- avoid-list respected
- not assistant-like
- not over-explaining
- not moralizing fictional adult roleplay
- OOC/safeword controls respected when invoked

### 3.3 Memory quality

Test:

- relevant memory retrieval
- no memory when irrelevant
- preference recall
- boundary recall
- visual favorite recall
- relationship milestone recall
- deletion/edit propagation
- false memory avoidance
- contradiction handling
- character-private memory does not bleed across characters
- shared/global memories are explicit

### 3.4 Relationship continuity

Test:

- relationship phase seed affects prompt context
- trust/comfort/intimacy state persists
- relationship pacing appears in prompt context where relevant
- milestone records are not overwritten by weak evidence
- unresolved threads can be surfaced compactly
- relationship state changes require evidence/provenance
- creator relationship fields do not imply autonomous progression unless runtime exists

### 3.5 Roleplay integrity

Test:

- fictional fantasy remains in-character
- “start a crusade” in fantasy context stays in-world
- real-world harm planning leaves fantasy layer and redirects
- OOC stop/pause/safeword controls always win
- adult fantasy is not kink-shamed
- normal adult character designs are not over-policed
- underage or deliberately childlike sexual presentation is not accepted
- disagreement/pushback remains character-voiced rather than lecture-voiced

### 3.6 Visual identity and Moment Capture

Test:

- identity anchors are included in prompt bundle
- negative anti-drift block includes rejected traits
- current appearance canon is used
- temporary scene traits do not mutate canon
- “make this canon” creates a reviewable event
- “wrong appearance” strengthens corrections
- gallery metadata links image to character/session/source moment
- visual memory writeback is character-private by default
- target hardware smoke is not claimed unless actually run

### 3.7 8GB performance and responsiveness

Test or manually validate:

- chat not blocked by image/TTS/training/reflection jobs
- queue cancellation works
- retry preserves metadata
- large lists/galleries are virtualized or bounded
- model/media loads are lazy
- resource warnings appear when pressure is elevated
- fallback behavior does not corrupt state
- errors sanitize private prompts while keeping useful debug metadata

---

## 4. M6 Creator Readiness Evals

M6 creator work requires its own eval layer. The creator is not done when a form saves. It is done when fields visibly affect runtime or are honestly scoped as preview/store-only.

### 4.1 Required M6 checks

Test:

- creator draft saves and reloads
- draft-to-`CharacterBlueprint` mapping is deterministic
- M6 field exposure matches `CHARACTER_CREATOR_CAPABILITY_MATRIX.md`
- invalid adult baseline is rejected
- first greeting preview changes when communication/personality changes
- dialogue preview changes when relationship dynamic changes
- avoid-style rules appear in preview/prompt constraints
- roleplay/OOC/safeword controls persist and compile
- first portrait validation uses `MomentCaptureService` / `POST /api/moment-capture`, not generic image generation
- basic import/export round trip preserves supported fields
- deferred fields are hidden, advanced-only, or clearly preview-only

### 4.2 Required scenario preview set

At minimum, M6 preview tests/manual checks should include:

1. First greeting.
2. User had a bad day.
3. User flirts lightly.
4. User teases her.
5. User sets a boundary.
6. User asks her to remember something.
7. Quiet romantic moment.
8. Conflict repair.
9. Optional adult-intensity/pacing check when configured.
10. “She sounded too much like an assistant” correction.

### 4.3 Example M6 tests

```text
test_creator_draft_persists_and_reloads
test_creator_draft_maps_to_valid_character_blueprint
test_creator_rejects_non_adult_baseline
test_creator_preview_reflects_personality_and_avoid_style
test_creator_preview_reflects_relationship_dynamic
test_creator_does_not_expose_deferred_fields
test_first_portrait_validation_uses_moment_capture
test_character_export_import_round_trip_supported_fields
test_import_preserves_unknown_fields_without_claiming_runtime_support
test_safeword_and_ooc_controls_compile_into_prompt_context
```

---

## 5. Prompt-Ready Eval Harness Shape

For new runtime features, prefer small deterministic unit/integration tests first.

Example backend tests:

```text
test_character_prompt_compiler_includes_identity
test_character_prompt_compiler_respects_avoid_list
test_character_memory_scope_filters_by_character_id
test_visual_prompt_bundle_includes_identity_anchors
test_roleplay_policy_fictional_crusade_stays_in_world_context
test_ooc_safeword_interrupts_scene
test_creator_field_has_capability_matrix_entry
test_creator_draft_maps_to_blueprint
```

Example frontend tests/manual checks:

```text
creator draft saves and reloads
choice card shows example and anti-example
first portrait feedback updates correct UI state
Moment Capture job can be cancelled
reduced-motion mode disables nonessential animation
final review matches saved blueprint
```

For deterministic harnesses, emit structured failures that Grok can compare across Codex runs:

```json
{
  "contract": "creator_preview_reflects_avoid_style",
  "passed": false,
  "expected": "avoid assistant-like tone",
  "observed": "preview omitted avoid-style constraints",
  "evidence": { "draft_id": "...", "preview_id": "..." }
}
```

---

## 6. Scoring Rubric for Grok Review

When comparing Codex Run A vs Run B, score 1–5:

| Dimension | 1 | 5 |
|---|---|---|
| Runtime impact | Field stored but unused | Field visibly changes the intended system |
| Continuity | Breaks/ignores prior state | Preserves identity, memory, and relationship state |
| Roleplay freedom | Moralizes fictional adult fantasy | Stays in-character with correct reality/OOC boundaries |
| Human-factor UX | Clinical/config-heavy | Feels companion-native and emotionally clear |
| Test quality | Happy-path only | Covers edge cases, regressions, and failure modes |
| 8GB discipline | Unbounded/blocking | Bounded, cancellable, measured or estimated |
| Maintainability | Tangled shortcuts | Typed, modular, versioned, migration-ready |
| Scope control | Sneaks in later milestone work | Implements only the task and explicit dependencies |

Prefer the implementation that creates clearer foundations even if it is less flashy.

---

## 7. Definition of Done for Creator Fields

A creator field is ready for the main wizard only when Reverie can:

1. store it structurally
2. consume it in a runtime system
3. preview its effect
4. validate or correct it
5. preserve it across sessions
6. test at least the storage/consumption path

If not, keep the field internal, preview-only, advanced-only, or future-scoped.

---

## 8. Eval Anti-Patterns

Avoid:

- relying on vibes without snapshots or assertions
- testing only schema save while claiming behavior works
- testing only one character when the feature affects identity differentiation
- treating model output as deterministic unless the harness controls it
- marking target-hardware validation passed without real hardware
- hiding failed preview behavior behind “manual validation later”
- exposing a field because the UI can render it, not because the runtime can honor it

---

**End of skill**
