# Skill — Moment Capture & Visual Continuity

**Version:** 1.1  
**Date:** June 14, 2026  
**Use for:** Moment Capture, local image generation, visual identity consistency, first portrait validation, gallery-as-memory, visual feedback, ComfyUI prompt bundles, visual change events, image-generation UX tied to character/memory/scene state, and M6 first portrait validation.

---

## 1. Purpose

Image generation in Reverie is not a disconnected media toy. It is a core companion-presence system.

The target loop is:

```text
chat -> remember -> capture the moment -> save it into shared history -> let that history shape future moments
```

Generic image generation is prompt gambling. Moment Capture is embodied memory. Build the second one.

---

## 2. Required Context

Load these before implementation or review:

- `Reverie_Source_of_Truth.md`
- `DEVELOPMENT_PLAN.md`
- `CHARACTER_CREATOR_CAPABILITY_MATRIX.md`
- `ROLEPLAY_FIRST_CHARACTER_INTEGRITY_POLICY.md`
- `prompts/GLOBAL_CODING_PROMPT.md`
- `prompts/skills/character-runtime-creator.md`
- `prompts/skills/basic-character-creator.md` for M6 first portrait validation or creator workflows
- `prompts/skills/8gb-vram-optimization.md`
- `prompts/skills/8gb-local-ai-patterns.md`
- `prompts/skills/tauri-svelte-ui-patterns.md` for frontend work
- `prompts/skills/fastapi-backend-patterns.md` for backend work
- `prompts/skills/character-quality-evals.md` for validation/evals

---

## 3. Product Rules

### 3.1 Moment Capture, not generic generation

User-facing language should prefer:

- “Capture this moment”
- “Save this scene”
- “Make this part of your shared history”
- “Does this feel like her?”

Avoid making the main path feel like a raw prompt editor. Advanced prompt editing can exist, but the default experience should feel companion-native.

For character-linked moments, call the Moment Capture path. Do not route primary Chat/VN capture through generic `/api/images/generate` and then pretend it is memory-linked. That is not Moment Capture. That is prompt gambling with a nicer hat.

### 3.2 Character identity must stay recognizable

Every generation that includes a character should preserve:

- identity anchors: adult baseline, skin tone, eye color, face structure, body/species baseline, permanent marks
- current appearance canon: current hair, signature traits, major active visual changes
- rejected traits: visual mistakes the user marked wrong
- style constraints: chosen art style, preferred framing, visual mood

The user should not have to manually lock obvious identity basics. The system should do that.

### 3.3 Adult creator freedom without over-policing

Do not add hidden censorship around fictional adult imagery or character style. Cute adult, petite adult, youthful adult, anime-stylized adult, early-20s adult, and soft-featured adult characters are valid. The line is underage or deliberately childlike sexual presentation, not normal adult character design.

Follow `ROLEPLAY_FIRST_CHARACTER_INTEGRITY_POLICY.md`.

---

## 4. Current Delivered M5 Concepts

M5 delivered the visual continuity foundation:

```text
VisualPromptCompiler
VisualPromptBundle
SceneState
MomentCaptureRequest
MomentCaptureRecord
VisualFeedbackAction
VisualChangeEvent
VisualMemoryArtifact
character-linked gallery metadata
visual feedback submit/review endpoints
approve/reject/rollback flow
character-scoped visual memory writeback
capture asset metadata compatibility
8GB capture scheduling/failure UX
```

Future work should reuse these instead of creating parallel systems.

---

## 5. Core Data Concepts

Preserve clean boundaries for:

```text
VisualIdentityProfile
  identity_anchors
  current_appearance
  evolving_traits
  scene_mutable_traits
  rejected_traits
  adult_only_policy

VisualChangeEvent
  changed_trait
  previous_value
  new_value
  reason
  feedback_action
  canon_status
  rollback_available
  rollback_id

MomentCaptureRequest
  character_id
  conversation_id
  session_id
  source_message_id
  source_turn_index
  scene_state
  relationship_phase_snapshot
  visual_identity_snapshot
  visual_identity_version
  visual_identity_updated_at
  prompt_hash
  quality_preset
  relevant_visual_memories

MomentCaptureRecord
  capture_id
  image_job_id
  output_paths
  feedback_state
  review_state
  visual_memory_artifacts
  rollback_id
  metadata
```

Use versioned schemas and migration seams for persisted artifacts.

---

## 6. Prompt Bundle Rules

Do not pass a single unstructured prompt blob around the app. Assemble a prompt bundle with clear sections:

```text
character_identity_block
current_appearance_block
scene_block
emotion_and_relationship_block
style_block
negative_identity_drift_block
user_preferences_block
resource_preset_block
```

Positive identity anchors and negative anti-drift prompts should be generated together.

Example anti-drift intent:

```text
Preserve amber eyes, warm brown skin, same face, same adult character, current black-violet hair.
Avoid blue eyes, pale skin, different person, childlike proportions, unintended hair color, unintended style.
```

Do not hardcode one art style or one image backend. ComfyUI/Flux/SD details belong behind an adapter/service boundary.

---

## 7. Feedback Loop Rules

Every generated image should be reviewable with lightweight user actions:

- Looks right
- Wrong appearance
- Make this canon
- Use this outfit again
- This was just this scene
- Never use this trait/style again
- Favorite
- Delete

Feedback should update durable local state only when appropriate:

- identity corrections strengthen `VisualIdentityProfile`
- favorites can become visual memories
- “make canon” creates a `VisualChangeEvent`
- wrong/rejected traits update `rejected_traits`
- deletion propagates to gallery metadata and any future training queues

Do not silently mutate character canon from a generated image without user confirmation.

---

## 8. M6 First Portrait Validation

M6 may use Moment Capture for first portrait validation.

Rules:

- Use `POST /api/moment-capture` or `MomentCaptureService`, not generic `/api/images/generate`.
- Require selected/draft `character_id`.
- Use the draft or selected `VisualIdentityProfile` snapshot.
- Include relationship phase snapshot and scene state.
- Preserve `prompt_hash`, capture ID, source draft/message/session metadata, and quality preset.
- First portrait validation should be optional and cancellable.
- If local image generation, ComfyUI, or target resources are unavailable, allow creator save without portrait validation and explain the limitation clearly.
- First portrait output is evidence, not automatic canon.
- User feedback can propose canon updates through the existing `VisualChangeEvent` flow.
- Rejected traits must feed future negative prompt guidance.

Recommended M6 first portrait scene defaults:

```text
neutral portrait scene
clear face and identity anchors
current appearance visible
simple background
adult presentation preserved
no user face visible unless explicitly requested
```

Manual validation:

- Create draft character with distinct anchors.
- Capture first portrait.
- Mark wrong appearance.
- Confirm rejected trait enters negative prompt guidance.
- Mark make canon.
- Approve canon change.
- Confirm visual identity changes only after approval.
- Roll back if available.

---

## 9. Chat/VN Capture Wiring Rule

For M6-P00/M5 follow-up work:

- Chat primary image action should say “Capture this moment.”
- VN primary scene image action should say “Capture this scene” or “Capture this moment.”
- These primary actions should call Moment Capture, not generic image generation.
- Generic image generation may remain as a secondary/advanced/legacy action.
- The created job/gallery item must have `moment_capture_id`, `character_id`, `session_id`, `source_message_id`, and `prompt_hash` metadata.

Tests should prove the primary Chat/VN action creates a Moment Capture-backed image job.

---

## 10. 8GB Performance Rules

Moment Capture must not block chat.

Required behavior:

- queue image jobs
- one heavy image job at a time by default
- respect resource coordinator pressure
- pause/deprioritize image work while TTS/chat are active when needed
- support preview/balanced/high presets
- persist job status and error states
- allow cancellation
- preserve metadata across retry/cancel/failure
- store thumbnails/metadata without loading full images into memory-heavy UI lists

When adding or changing image workloads, document expected peak/steady VRAM impact or why it cannot be measured yet.

Target-hardware checks remain M8 unless actually run on the target machine. Do not mark them passed in CI just because the code looks confident.

---

## 11. Frontend UX Rules

Default flow:

1. User clicks “Capture this moment.”
2. UI shows what scene/character/mood will be captured in plain language.
3. Image job runs with progress and graceful resource warnings.
4. Result appears with “Does this feel like her?” feedback.
5. User can favorite, make canon, reject, regenerate, or continue scene.

Gallery should feel like shared history, not a file dump:

- character
- date/session
- linked chat moment
- prompt summary
- mood/scene tags
- favorite/canon/rejected state
- continue/capture-again actions

Use accessible motion, reduced-motion support, keyboard navigation, and virtualized large galleries.

---

## 12. Tests and Validation

For backend work, add tests for:

- prompt bundle assembly from visual identity + scene state
- identity anchors included in positive prompts
- anti-drift negatives included
- feedback updates correct state
- canon changes require explicit action
- job errors do not break chat
- deletion/rollback behavior
- Moment Capture metadata preservation
- character-scoped visual memory writeback

For frontend work, add tests where practical for:

- primary Chat/VN capture calls Moment Capture path
- feedback actions
- job state rendering
- resource warning rendering
- gallery metadata display
- review panel approve/reject/rollback controls

Manual validation should include:

- same character generated multiple times preserves identity anchors
- rejected eye/skin/hair traits do not reappear in prompt bundle
- favorite image creates reviewable memory/metadata when enabled
- image generation remains queued and cancellable on 8GB preset
- first portrait validation can be skipped or retried

---

## 13. Review Rubric

Grok should compare Codex outputs on:

- character identity consistency
- memory/scene integration
- user feedback and correction quality
- local-first persistence and deletion behavior
- clean service boundaries
- 8GB-safe queue behavior
- human-first UX language
- no hidden adult-fantasy censorship
- tests and migration readiness
- no duplicate image/capture abstraction

---

**End of skill**
