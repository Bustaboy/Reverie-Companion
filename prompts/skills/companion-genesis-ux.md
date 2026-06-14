# Skill — Companion Genesis UX

**Version:** 1.1  
**Date:** June 14, 2026  
**Use for:** M7 immersive Companion Genesis UX, black-starfield/celestial creation flow, choice constellations, cinematic stage shell, multi-draft comparison, live companion preview, first portrait ceremony, world reveal, final “Begin” moment, and human-first creator wording. For M6 practical creator architecture, load `basic-character-creator.md` first.

---

## 1. Purpose

Companion creation is not a form. It is the first emotional bond moment.

The user should feel like they are shaping a person, a world, and the rules of memory that bind them. The backend can be structured like a machine room. The UX must feel like a dream becoming real.

This skill is for the immersive M7 elevation. It may inform M6 wording and previews, but it must not drag M7 ceremony into M6. If Codex starts summoning stars while the task asked for draft persistence, gently remove the telescope.

---

## 2. Required Context

Load these before implementation or review:

- `Reverie_Source_of_Truth.md`
- `DEVELOPMENT_PLAN.md`
- `CHARACTER_CREATOR_CAPABILITY_MATRIX.md`
- `ROLEPLAY_FIRST_CHARACTER_INTEGRITY_POLICY.md`
- `prompts/GLOBAL_CODING_PROMPT.md`
- `prompts/skills/character-runtime-creator.md`
- `prompts/skills/basic-character-creator.md` for M6 practical creator boundaries
- `prompts/skills/roleplay-character-integrity.md`
- `prompts/skills/moment-capture-visual-continuity.md` when portrait/image validation is involved
- `prompts/skills/tauri-svelte-ui-patterns.md`
- `prompts/skills/8gb-vram-optimization.md` for image/audio/media previews
- `prompts/skills/character-quality-evals.md`

---

## 3. M6 Boundary

For M6, this skill may inform:

- human-first wording
- examples and anti-examples
- preview-before-canon behavior
- final review copy
- emotional clarity
- accessibility expectations

For M6, this skill must not cause:

- starfield/celestial stage implementation
- cinematic transitions
- constellation choice UI
- adaptive creator music
- multi-draft ritual flow
- world reveal ceremony
- full Genesis save/resume ceremony
- live animated companion silhouette reveal

M6 is the practical creator. M7 is the ritual. Confusing these two is how projects wake up in a velvet-lined scope coffin.

---

## 4. UX Principles

### 4.1 Preview before canon

Never ask the user to commit to a trait without showing what it means.

Every meaningful creator choice should have at least one of:

- text example
- anti-example
- dialogue preview
- visual example/reference card
- generated draft
- first portrait validation
- scenario test

### 4.2 Ask human questions, not schema questions

Prefer:

- “How should she make you feel?”
- “What kind of stories do you want together?”
- “What makes her unforgettable?”
- “How does she speak when she wants your attention?”
- “What should never be lost about her?”
- “What kind of moments do you want to capture?”

Avoid exposing internal labels in the main flow:

- `attachment_style`
- `escalation_policy`
- `adult_status_policy`
- `relationship_state_vector`
- `anti_sycophancy_level`

Advanced editors can expose structured fields later.

### 4.3 Capability honesty

The creator must not ask questions Reverie cannot use. A creator field must be storable, consumed by runtime, previewable, correctable, and durable across sessions before it ships in the main wizard.

### 4.4 Adult fantasy freedom

The creator is for fictional adult companions and should not moralize user preferences. Cute adult, petite adult, youthful adult, anime-stylized adult, early-20s adult, and soft-featured adult designs are valid. The boundary is underage or deliberately childlike sexual presentation, not normal adult style.

---

## 5. Genesis Flow Model

The ideal immersive flow can be built in stages:

```text
Stage 0: The Void
Stage 1: The First Shape
Stage 2: The Soul
Stage 3: The Contradiction
Stage 4: The Voice
Stage 5: The Form
Stage 6: The World
Stage 7: The Oath
Stage 8: The First Words
Stage 9: The First Image
Stage 10: The Reveal
```

### Stage behavior

- Start with a black scene and stars.
- More of the world appears as choices are made.
- Personality choices subtly influence color/motion tone.
- Visual choices reveal silhouette/portrait details.
- World choices transform the background.
- First greeting and first portrait become validation points.
- Final button should feel like “Begin,” not “Submit.”

Build this progressively. Do not implement the full cinematic ritual before runtime fields are proven.

---

## 6. Creator Components

Useful M7 frontend units:

```text
GenesisWizard
GenesisStageShell
StarfieldCanvas
ChoiceConstellation
TraitAxis
ChoiceCard
DialoguePreview
AntiExampleBlock
VisualIdentityStep
WorldPreview
FirstGreetingStep
FirstPortraitStep
BlueprintReview
CreatorDraftControls
WorldRevealStage
BeginButton
```

Stores/types:

```text
characterCreatorStore
characterStore
CharacterBlueprintDraft
CreatorStepState
CreatorPreviewState
GenesisMotionState
GenesisAudioState
```

Persist drafts. Losing a 30-minute companion draft is a villain-origin-story bug.

---

## 7. Examples and Anti-Examples

Every ambiguous trait should show what it means and what it does not mean.

Example:

```text
Playful teasing
Means: she jokes, flirts, and lightly challenges while staying warm.
Example: “You missed me. Don’t argue. You’re bad at lying when you’re happy.”
Does not mean: cruel insults, constant sarcasm, joking through serious moments.
```

Visual example cards should clarify styles, hair, body baseline, scene mood, fashion identity, and art direction without making the user decode prompt vocabulary.

---

## 8. Preview/Eval Requirements

Creator preview should support:

- first greeting preview
- response to affection
- response to teasing
- response to user setting a boundary
- response to user asking her to remember something
- quiet romantic moment
- optional adult-intensity preview when configured
- first portrait validation through Moment Capture
- final blueprint review

Feedback buttons should be human:

- Warmer
- Less formal
- More playful
- More independent
- Less intense
- Less assistant-like
- More like this
- Keep this detail
- Never use this trait

Those map to structured blueprint changes internally.

---

## 9. Accessibility and Performance

The immersive flow must remain usable:

- reduced-motion support
- mute/volume controls for music
- keyboard navigation
- screen-reader labels
- save/resume draft
- no mandatory long animations
- image/audio previews optional and cancellable
- no chat/backend blocking from creator media previews
- canvas/animation cleanup when leaving the creator
- mobile/laptop layout sanity

8GB constraints still apply. A creator that makes the companion feel magical but the laptop feel like a toaster oven has failed the assignment.

---

## 10. Tests and Validation

Add tests for:

- draft persistence
- step navigation
- blueprint field mapping
- preview request generation
- validation/correction actions
- accessibility-critical controls
- reduced-motion behavior
- cancellation of image/audio preview jobs

Manual validation:

- create a companion without touching advanced fields
- create a fantasy/adult-styled companion without moralizing UI language
- verify examples clarify choices
- verify final blueprint matches user-facing choices
- verify resume draft after reload
- verify first portrait validation can be skipped or cancelled
- verify reduced motion and mute controls remain visible

---

## 11. Review Rubric

Grok should compare Codex outputs on:

- emotional UX quality
- human-first wording
- preview-before-canon behavior
- capability honesty
- clean mapping from UX choices to schema fields
- accessibility and reduced-motion support
- performance and cancellation
- no hidden adult-fantasy censorship
- no M6 practical-creator regression
- no M8/M9 runtime creep

---

**End of skill**
