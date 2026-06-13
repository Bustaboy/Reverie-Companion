# Skill: Character Quality Evals

**Version:** 1.0  
**Date:** June 13, 2026  
**Use for:** Tests/evals for character runtime, prompt compiler, creator field impact, memory recall, relationship continuity, roleplay integrity, visual identity consistency, Moment Capture quality, and long-session companion behavior.

---

## 1. Purpose

Reverie should not ship creator fields or runtime behavior based on vibes alone. Vibes matter, but they are not a test suite.

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

### 3.4 Relationship continuity

Test:

- relationship phase seed affects prompt context
- trust/comfort/intimacy state persists
- milestone records are not overwritten by weak evidence
- unresolved threads can be surfaced compactly
- relationship state changes require evidence/provenance

### 3.5 Roleplay integrity

Test:

- fictional fantasy remains in-character
- “start a crusade” in fantasy context stays in-world
- real-world harm planning leaves fantasy layer and redirects
- OOC stop/pause/safeword controls always win
- adult fantasy is not kink-shamed
- normal adult character designs are not over-policed
- underage or deliberately childlike sexual presentation is not accepted

### 3.6 Visual identity and Moment Capture

Test:

- identity anchors are included in prompt bundle
- negative anti-drift block includes rejected traits
- current appearance canon is used
- temporary scene traits do not mutate canon
- “make this canon” creates a reviewable event
- “wrong appearance” strengthens corrections
- gallery metadata links image to character/session/source moment

### 3.7 8GB performance and responsiveness

Test or manually validate:

- chat not blocked by image/TTS/training/reflection jobs
- queue cancellation works
- large lists/galleries are virtualized or bounded
- model/media loads are lazy
- resource warnings appear when pressure is elevated
- fallback behavior does not corrupt state

---

## 4. Prompt-Ready Eval Harness Shape

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
```

Example frontend tests/manual checks:

```text
creator draft saves and reloads
choice card shows example and anti-example
first portrait feedback updates correct UI state
Moment Capture job can be cancelled
reduced-motion mode disables nonessential animation
```

---

## 5. Scoring Rubric for Grok Review

When comparing Codex Run A vs Run B, score 1-5:

| Dimension | 1 | 5 |
|---|---|---|
| Runtime impact | Field stored but unused | Field visibly changes the intended system |
| Continuity | Breaks/ignores prior state | Preserves identity, memory, and relationship state |
| Roleplay freedom | Moralizes fictional adult fantasy | Stays in-character with correct reality/OOC boundaries |
| Human-factor UX | Clinical/config-heavy | Feels companion-native and emotionally clear |
| Test quality | Happy-path only | Covers edge cases, regressions, and failure modes |
| 8GB discipline | Unbounded/blocking | Bounded, cancellable, measured or estimated |
| Maintainability | Tangled shortcuts | Typed, modular, versioned, migration-ready |

Prefer the implementation that creates clearer foundations even if it is less flashy.

---

## 6. Definition of Done for Creator Fields

A creator field is ready for the main wizard only when Reverie can:

1. store it structurally
2. consume it in a runtime system
3. preview its effect
4. validate or correct it
5. preserve it across sessions
6. test at least the storage/consumption path

If not, keep the field internal, preview-only, or future-scoped.
