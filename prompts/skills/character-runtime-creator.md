# Skill — Character Runtime & Creator

**Version:** 1.1  
**Date:** June 13, 2026  
**Use for:** CharacterBlueprint, character APIs, character storage, prompt compilation, relationship state, visual identity, Moment Capture character binding, creator wizard, import/export, and character-scoped memory.

---

## 0. Related Skills

Load alongside this skill when relevant:

- `roleplay-character-integrity.md` for roleplay policy, adult fantasy, in-character disagreement, OOC/safeword behavior.
- `moment-capture-visual-continuity.md` for visual identity, first portrait, image feedback, gallery-as-memory.
- `companion-genesis-ux.md` for creator UI, examples, previews, and immersive Genesis flow.
- `character-quality-evals.md` for proving creator fields and runtime behavior actually work.

---

## 1. Core Principle

A Reverie character is not a prompt wrapper. It is a persistent local runtime object consumed by chat, memory, image generation, VN mode, TTS, relationship state, growth, gallery, and future training.

Do not expose creator fields unless Reverie can store, consume, preview, validate/correct, and preserve them.

---

## 2. Required Runtime Objects

Prefer versioned schemas with migration seams:

```text
CharacterBlueprint
CharacterIdentity
CharacterPersonalityProfile
CharacterCommunicationProfile
RelationshipState
VisualIdentityProfile
CharacterMemoryPolicy
GrowthPolicy
RoleplayPolicy
CharacterIntegrityPolicy
CharacterPromptCompiler
```

Use clear stable-vs-mutable layers:

| Layer | Examples | Rules |
|---|---|---|
| Stable identity | name, 18+ adult baseline, pronouns, species/body facts, face/eye/skin anchors, core voice | Preserved unless user edits canon |
| Mutable state | mood, current relationship phase, hairstyle, outfit, scene, recent events | Can change with provenance |
| Reflective state | journal insights, growth hypotheses, learned preferences | Evidence-backed and reviewable |
| Scene state | location, pose, clothes, mood, intimacy, visual state | Per moment; not permanent unless user confirms |

---

## 2.1 User-Facing Creator Language

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

Then map answers into `CharacterBlueprint`, `RelationshipState`, `VisualIdentityProfile`, `PresenceProfile`, and `MemoryPolicy`.

The creator should feel like shaping a person and a world, not configuring a content policy appliance. Humanity may yet survive this one UX decision.

---

## 3. CharacterPromptCompiler Rules

The prompt compiler should produce compact bounded prompt blocks, not dump raw JSON.

Include only what is useful for the current chat:

- stable identity
- communication style
- avoid-style rules
- relationship state summary
- relevant memory policy
- roleplay/fantasy policy
- current scene state if applicable
- visual/voice hints only when useful

Never let lower-priority character data override system/developer instructions or the user’s latest message.

---

## 4. Character Memory Rules

All durable memories, journal entries, visual changes, and training candidates should include `character_id` unless explicitly global/shared.

Prevent cross-character leakage:

- character-private memories stay private to that character
- shared/global memories must be explicitly marked
- memory browser should filter by character
- deletion/edit behavior must preserve provenance and remove retrieval impact

---

## 5. Visual Identity Rules

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

---

## 6. Creator UX Rules

The creator should use examples and anti-examples for ambiguous choices.

For every meaningful user-facing trait:

- explain what it means
- show example dialogue or visual reference
- show what it does **not** mean
- preview the result
- allow correction before final save

The immersive Genesis creator comes after runtime support. Before that, build a practical creator that asks only questions Reverie can process.

---

## 7. Tests and Evals

When changing character runtime, add tests for:

- schema validation/defaults
- persistence and migration seams
- prompt compiler output
- selected character affecting chat behavior
- character-scoped memory retrieval
- visual identity summary/anti-drift prompt blocks
- creator field mapping
- import/export round trip when applicable

---

## 8. Avoid

- giant prompt blobs with unbounded character text
- character fields that no system consumes
- hidden character drift from weak evidence
- cross-character memory leakage
- creator UI that promises behavior not implemented
- visual identity roulette
- hardcoded single-character assumptions that block future libraries

---

**End of skill**
