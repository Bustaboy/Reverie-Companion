# Reverie — Source of Truth

**Version:** 1.2
**Date:** June 13, 2026
**Owner:** Vision Entertainment / Grok (Vision)
**Status:** Milestone 5 complete — Moment Capture & Visual Continuity closed.

---

## 1. Product Promise

Reverie is a local-first desktop AI companion built to make characters feel alive over long periods of interaction. The core promise is simple:

> Characters remember what matters, grow from shared history, remain recognizable, and feel emotionally present — while staying private and smooth on an RTX 4070 8GB mobile-class machine.

Reverie is not a SillyTavern skin and does not depend on SillyTavern as a backend. It is a custom FastAPI + Tauri/Svelte application with local memory, growth, media, and extension foundations designed for future Futa-Vision integration.

### Non-negotiables

- **Local-first:** chat, memory, growth, settings, character data, and media orchestration are designed to work without mandatory hosted services after setup.
- **8GB target:** normal operation must protect the RTX 4070 8GB mobile target by keeping interactive chat responsive, queueing heavyweight media, and gracefully downgrading before OOM.
- **Transparent growth:** memory, reflection, journal entries, training candidates, and adapter artifacts must be inspectable, controllable, reversible, and deletable.
- **Uncensored companion design:** Reverie supports adult roleplay and niche character contexts without hidden moralizing product constraints.
- **Continuity before breadth:** character identity, boundaries, lore, physical facts, promises, and relationship history take priority over adding more disconnected features.
- **Futa-Vision readiness:** media and VN systems expose clean scene, character, prompt, and job metadata seams so reactive image/video features can attach later.

---

## 2. Architecture Overview Through Milestone 5

Milestones 3–5 complete Reverie's first production-grade immersion, character runtime, and visual-continuity stack. They add these major pillars around the Milestone 1/2 chat, memory, and growth foundation:

1. **Visual Novel Foundation:** lightweight sprite/expression mode with reactive emotion state and full-immersive presentation.
2. **Emotional TTS:** local voice profiles, context-aware routing, mood/prosody enrichment, streaming playback, and per-character tuning.
3. **Character Runtime:** versioned `CharacterBlueprint` persistence, selected-character chat, relationship state, visual identity, roleplay-first policy, and character-scoped memory/reflection hooks.
4. **Moment Capture & Visual Continuity:** character-linked capture from chat/VN context, `VisualPromptCompiler`, gallery-as-memory metadata, visual feedback, reviewable `VisualChangeEvent` canon updates, rollback, visual memory writeback, and deterministic evals.
5. **In-Chat Image Generation:** local ComfyUI-oriented job orchestration, prompt enrichment, chat/VN display hooks, and persistent gallery history.
6. **Growth Visibility:** Growth Dashboard, Diary Journal, Memory Browser, Personal LoRA review, and Character Encyclopedia surfaces.
7. **Extensibility:** typed `extension.v1` manifests, declarative settings sections, bounded event history, and backend/frontend contracts.
8. **Settings & Release Polish:** searchable Settings & Control Hub, 8GB performance presets, backup/import/reset controls, onboarding, and documentation.

### High-level runtime flow

```text
User message
  → Chat service builds bounded prompt context
  → Memory retrieval contributes relevant durable recall
  → Assistant response streams immediately
  → Emotion inference runs at completion, not per token
  → VN expression, TTS routing, growth notices, and optional image prompt context read the completed turn
  → Reflection/journal/training candidates run later under throttles and review gates
```

This flow keeps the active conversation path fast. Heavy or durable work is delayed, queued, reviewed, or downgraded instead of blocking the user.

---

## 3. Core Systems

### 3.1 Chat, Memory, and Context Assembly

The chat layer remains the emotional center. It owns the active conversation, streaming response path, memory notices, retry/error recovery, and downstream hooks for voice, VN, image prompts, reflection, and growth.

**Design decisions:**

- Keep token streaming independent from TTS/image/reflection jobs.
- Use bounded memory context rather than unbounded transcript stuffing.
- Prefer durable evidence with provenance over speculative personality rewrites.
- Treat memory influence as visible and editable through trust UI rather than hidden magic.

**Data flow:**

```text
Chat request
  → recent turns + character state + selected memories
  → Ollama/local LLM response stream
  → final assistant message
  → emotion inference + optional media/growth side effects
  → optional Moment Capture records selected character, scene, prompt hash, image job, feedback/review state, and visual memory writeback
```

**Safety mechanisms:**

- Long-term memory can be disabled.
- Context budget presets constrain prompt size.
- Memory pruning modes protect essential facts while allowing leaner recall on constrained systems.
- Deleted/private memory must not feed reflection, training, or global contribution paths.

### 3.2 Visual Novel Foundation

VN mode makes characters visibly reactive without imposing a heavy GPU runtime. It uses Svelte state, expression manifests, placeholder sprite assets, and emotion-driven expression selection.

**Architecture:**

- `ExpressionManager` maps inferred emotional state to expressions and pose choices.
- `visualNovelStore` tracks VN mode, full-immersive mode, current expression, background, and dialogue state.
- VN rendering stays frontend-native and lightweight; it does not keep a Live2D or 3D runtime resident.
- Chat completion events can update expression state after the response has finished streaming.

**8GB strategy:**

- Prefer static sprites, small manifests, and lazy assets over GPU-bound live animation.
- VN remains a presentation layer; it does not trigger model inference on every visual update.
- Full immersive mode hides heavy navigation chrome but does not alter backend resource usage.

**Extensibility hooks:**

- Future character packs can register sprite/background manifests.
- Futa-Vision can consume the same scene/emotion metadata to trigger reactive video clips later.

### 3.3 Emotional TTS and Voice

The TTS system makes replies speakable while preserving chat responsiveness. It layers backend voice synthesis, profile management, context-aware routing, emotion/prosody tags, frontend playback, and user settings.

**Architecture:**

- Backend TTS models support local providers such as Piper-style lightweight fallback and richer Orpheus/XTTS/StyleTTS-class voices.
- Voice profiles store character voice identity, mood defaults, preview metadata, and clone-foundation inputs.
- The context router decides whether to use fast, balanced, or quality routing based on message context, character mood, user settings, and resource pressure.
- The frontend TTS store/player handles playback queueing, streaming audio chunks, retry, stop, and per-message controls.

**8GB strategy:**

- TTS is prioritized above image generation because spoken replies are interactive.
- Fast/Piper-style modes can stay CPU-friendly when GPU is busy.
- Rich voice models are optional and can be unloaded before exclusive image work.
- Speech synthesis is not placed inside the token streaming path.

**Safety and trust:**

- Voice cloning remains explicit and profile-scoped.
- Users can disable TTS, autoplay, or mood shaping.
- Per-character mood settings are visible rather than silently inferred forever.

### 3.4 In-Chat Image Generation and Moment Capture

Image generation is an optional local media layer tied to chat and VN context. It enriches scene prompts with character, memory, mood, and conversation metadata, then queues generation through an 8GB-aware service.

**Architecture:**

- Image prompt engine builds positive/negative prompt context from chat, character state, and optional VN scene state.
- Image generation service coordinates jobs, status, cancellation, history, and gallery metadata.
- Frontend gallery/job cards show progress, completed assets, retry/reuse actions, and local history.
- Chat and VN can display generated images without making image generation mandatory.
- Moment Capture wraps image generation in a character/session workflow: selected `character_id`, scene state, visual identity snapshot, relationship phase, source message, prompt hash, job status, feedback state, review state, and saved asset metadata stay linked.
- Visual feedback actions can create reviewable `VisualChangeEvent`s. Approved changes update `VisualIdentityProfile` with provenance and rollback metadata; rejected/rolled-back changes stay out of positive prompts.
- Looks-right/favorite-style feedback can create character-scoped visual memory artifacts. Generated visual feedback is not training data unless future explicit opt-in flows are built.
- The visual consistency eval harness checks identity anchors, rejected traits, scene mutability, distinct-character prompts, feedback/canon review, visual memory scoping, and 8GB queue behavior without calling external image services.

**8GB strategy:**

- Default preset is preview-first for RTX 4070 8GB-class machines.
- Only one exclusive image generation job runs at a time.
- ComfyUI/Flux GGUF workflows are expected to run with low-VRAM/offload settings.
- The resource coordinator can pause or preempt image work when TTS or chat needs priority.
- Automatic downgrade explanations are user-facing rather than silent.
- Capture jobs preserve metadata across retry, cancellation, waiting, downgrade, and safe failure states.

**Futa-Vision readiness:**

- Prompt context, scene metadata, character IDs, and gallery outputs are structured so future video/clip generation can reuse them.

### 3.5 Growth System and Self-Learning Visibility

Milestone 2 built the durable growth loop; Milestone 3 makes it visible, controllable, and emotionally legible.

**Core loop:**

```text
Conversation evidence
  → memory extraction + provenance
  → reflection scheduling
  → journal entry / insight draft
  → optional memory promotion
  → optional training candidate
  → user review
  → Personal LoRA/adapters only after approval
```

**Milestone 3 surfaces:**

- **Growth Dashboard:** relationship pulse, recent insights, trust copy, and transparent status.
- **Diary Journal:** first-person reflection reader with privacy labels and pinned entries.
- **Memory Browser:** editable long-term recall with search and deletion controls.
- **Personal LoRA Panel:** approval queue and conservative local training posture.
- **Character Encyclopedia:** living character bible/life summary assembled from memory and journal state.

**Design decisions:**

- Growth deepens identity; it must not casually rewrite core character facts.
- Training data is opt-in, reviewable, and rollback-friendly.
- Growth notices are rare and contextual so they feel meaningful, not noisy.
- Private/deleted/disallowed data stays out of memory promotion and training.

### 3.6 Extensibility Foundation

Milestone 3 introduces a lightweight extensibility contract without running arbitrary plugin code.

**Architecture:**

- `extension.v1` manifests define panels, commands, setting sections, voice hooks, image workflows, growth modifiers, import helpers, VN state hooks, and memory capabilities.
- Backend Pydantic models validate manifests and expose extension endpoints.
- Frontend TypeScript contracts mirror backend schemas.
- Extension settings render declaratively in the Settings Hub and persist under extension-scoped keys.
- Bad manifests are isolated and reported without crashing the app.

**Why declarative first:**

- Keeps 8GB overhead near zero.
- Avoids unsafe arbitrary code execution during early alpha foundations.
- Gives future extension authors a stable target before richer runtimes arrive.

### 3.7 Settings & Control Hub

Settings is now the unified control surface for local behavior, media, growth, memory, performance, extensions, and portability.

**Key sections:**

- General
- What’s New in Milestone 3
- Appearance
- TTS & Voice
- Image Generation
- Growth & Self-Learning
- Memory
- Performance & 8GB
- Extensibility
- Import / Export / Backup

**Release polish:**

- Settings are searchable and keyboard-friendly.
- Save status is local and visible.
- 8GB impact is explained before quality increases.
- Backup exports include metadata and scoped local storage keys.
- Imports require confirmation and only restore trusted Reverie-scoped local keys.
- Reset requires an explicit phrase.
- A first-run Milestone 3 welcome panel guides users to What’s New and VN mode.

---

## 4. 8GB Resource Strategy

The 8GB strategy is product architecture, not a late optimization pass.

### Priority order under pressure

1. Active chat streaming and UI responsiveness.
2. Interactive TTS playback/synthesis.
3. Memory retrieval and lightweight context assembly.
4. Image generation jobs.
5. Reflection, journal promotion, embedding backfills, and training prep.
6. Personal LoRA training / future heavier jobs.

### Guardrails

- Keep normal operation below roughly 7.5-7.8 GB VRAM where practical.
- Treat reported free VRAM as advisory, not guaranteed allocatable memory.
- Use conservative defaults: preview image quality, one background task, gentle/balanced context, fast/balanced TTS.
- Queue exclusive GPU jobs rather than running image, rich TTS, and training simultaneously.
- Pause, preempt, or cancel background jobs when higher-priority interactive work starts.
- Surface downgrade and pause/resume explanations to users.
- Release locks, temp files, and model residency after cancellation/failure.

### Settings presets

- **8GB Safe:** strongest guardrails, preview images, gentle context, speed-oriented TTS, one background task.
- **Balanced:** default-feeling experience with bounded context and preview media safety.
- **Quality:** richer context and media defaults, still guarded; intended for users who accept slower jobs and more pressure.

---

## 5. Safety, Privacy, and User Control

Reverie must be intimate without being opaque.

### Required user controls

- Enable/disable long-term memory.
- Search, inspect, edit, and delete memory.
- Review journal entries and growth insights.
- Approve/edit/reject training examples before Personal LoRA use.
- Export/import/reset local control data.
- Disable or tune TTS, image automation, reflection frequency, and growth notifications.
- See resource warnings and downgrade explanations.

### Data boundaries

- Local data stays local unless the user explicitly exports or opts into future sharing.
- Debug logs should prefer IDs, job metadata, and aggregate performance data over raw private content.
- Extension contracts must request capabilities explicitly.
- Global model improvement remains a future opt-in path, not an implicit upload.

---

## 6. Developer Architecture Map

### Backend

- **FastAPI app:** routes for chat, memory, journal, growth, TTS, voices, images, resources, and extensions.
- **Services:** chat assembly, memory browser, TTS, voice management, image generation, prompt enrichment, resource coordination.
- **Core modules:** memory, reflection, growth, emotion, LoRA, extensions, config, Ollama client.
- **Tests:** pytest coverage for chat, memory, reflection, journal, growth, TTS, voices, image generation, resources, extensions, and Personal LoRA foundations.

### Frontend

- **Tauri/Svelte shell:** sidebar navigation, app boundary recovery, chat, VN, growth, journal, memory, image gallery, settings.
- **Stores:** chat, settings, VN, TTS, image generation, resources, memory, journal, growth.
- **API clients:** typed service wrappers for backend boundaries.
- **Extensions:** shared contracts, registry, event bus, declarative settings rendering.

### Documentation

- `Reverie_Source_of_Truth.md`: product and architecture authority.
- `DEVELOPMENT_PLAN.md`: milestone sequencing and current plan status.
- `RESEARCH_Milestone3.md`: tool choices and local AI implementation notes.
- `docs/extensions/README.md`: extension manifest and capability guide.
- `backend/README.md` and `frontend/README.md`: subsystem setup notes.

---

## 7. Milestone Status

### Milestone 1 — Foundation: Complete

- Repository, backend shell, frontend shell, basic chat path, and initial documentation.

### Milestone 2 — Memory & Self-Learning: Complete

- Long-term memory context, reflection scheduling, journal entries, growth orchestration, growth notifications, Settings/Journal/Training UI, and Personal LoRA review foundation.

### Milestone 3 — Immersion & Production Foundations: Complete

Milestone 3 is now fully complete as of June 12, 2026.

**What was achieved:**

- Added a lightweight Visual Novel foundation with reactive expressions and immersive mode.
- Built emotional TTS foundations: provider abstraction, voice profiles, context routing, mood/prosody shaping, playback UI, streaming/clone foundations, and per-character polish.
- Added local in-chat image generation foundations: backend job queue, prompt enrichment, ComfyUI/Flux-oriented 8GB safety, frontend gallery, chat/VN display, history, and controls.
- Expanded the growth system into user-facing surfaces: Growth Dashboard, Diary Journal, Memory Browser, Personal LoRA review, and Character Encyclopedia.
- Added performance/reliability infrastructure: resource coordinator, status endpoint, VRAM pressure states, TTS-vs-image priority, pause/preempt behavior, and settings-facing warnings.
- Established extensibility foundations with typed backend/frontend contracts, declarative manifests, isolated settings, docs, and error handling.
- Rebuilt Settings as a searchable Control Hub with media, growth, memory, performance, extension, backup, reset, and What’s New sections.
- Completed final release polish with onboarding, clearer 8GB explanations, documentation reorganization, small cleanup, and Milestone 3 completion status.

**Milestone 3 release posture:** Alpha-foundation ready. Reverie now has a coherent local companion loop where the character can converse, remember, reflect, speak, appear visually, generate scene imagery, expose growth state, protect 8GB hardware, and offer stable extension seams for future work.

### Milestone 4 — Character Runtime & Capability Alignment: Complete

Milestone 4 delivered the runtime substrate required before creator choices can honestly affect the app:

- Versioned local `CharacterBlueprint` storage and APIs.
- Selected-character chat with prompt compiler grounding.
- Character-scoped memory/reflection/growth seams.
- Relationship state, visual identity, growth policy, and roleplay-first character integrity schemas.
- Minimal frontend character selector and quick-create shell.

### Milestone 5 — Moment Capture & Visual Continuity: Complete

Milestone 5 delivered character-aware visual presence:

- `VisualPromptCompiler` and deterministic visual consistency evals.
- Moment Capture API/service using selected character, scene state, relationship phase, prompt hash, and existing image queue/resource coordinator.
- Character-linked gallery metadata and deletion-aware history.
- Quick/detailed visual feedback actions.
- Reviewable `VisualChangeEvent` approve/reject/rollback flow.
- Character-scoped visual memory writeback with no automatic training eligibility.
- 8GB-safe capture scheduling with TTS priority, queue status, cancellation, retry metadata preservation, preview downgrade, and safe failure payloads.
- Capture asset metadata compatible with later M6 character portability and M8 backup/export work.

Real target-hardware smoke on RTX 4070 8GB mobile or equivalent remains Pending M8-P09 and must use the recorded M5 checklist.

---

## 8. Future Milestones

### Milestone 6 — Basic Character Creator Foundation

Build a practical creator that exposes only fields Reverie can already store, consume, preview, validate, and preserve.

### Milestone 7 — Companion Genesis Immersive Creator

Wrap the proven M6 creator in the immersive Companion Genesis experience.

### Milestone 8 — Alpha Hardening & Local Productization

Persistent sessions, setup wizard, backup/export/import, packaged Tauri validation, performance dashboard, long-session evals, and real target-hardware smoke.

### Milestone 9 — Beta Deep Growth & Real Personalization

Real Personal LoRA/adapter training, relationship evolution, lorebook/canon store, proactive initiative, advanced roleplay controls, and deeper visual evolution.

### Milestone 10 — Launch & Monetization Foundations

- Tiered model packaging, contribution flows, broader QA, installer polish, privacy reviews, and public beta readiness.

---

## 9. Quality Gates Going Forward

Every future feature must answer:

1. Does it preserve character continuity and user trust?
2. Does it stay local-first by default?
3. Does it degrade gracefully on 8GB hardware?
4. Does it expose durable growth and training data for review?
5. Does it avoid blocking chat with heavy media or background work?
6. Does it connect cleanly to future Futa-Vision scene/video hooks?
7. Is it documented enough for the next engineer to extend safely?
