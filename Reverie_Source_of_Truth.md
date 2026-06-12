# Reverie — Source of Truth

**Version:** 3.0  
**Date:** June 12, 2026  
**Brand:** Reverie  
**Status:** **Milestone 3 complete** — local-first companion foundation, voice, image, growth, extensibility, and release polish are now closed.

---

## 1. Product Promise

Reverie is Vision Entertainment’s local-first desktop AI companion: a private, uncensored, emotionally intelligent application for long-running relationships with characters who remember, reflect, speak, visualize scenes, and grow with user control.

The user promise remains:

> Characters should remember what matters from hundreds or thousands of messages ago, grow from evidence over weeks and months, and feel like recognizable evolving people while staying smooth on an RTX 4070 8GB mobile GPU.

### Non-negotiables

- **Local-first by default:** chat, memory, growth, settings, and core companion data operate without mandatory hosted services after setup.
- **8GB target:** normal operation must preserve responsiveness and avoid preventable VRAM crashes on an RTX 4070 8GB laptop-class GPU.
- **Custom backend:** Reverie uses its own FastAPI service layer and does not depend on SillyTavern as an architectural backend.
- **Transparent growth:** memories, reflections, journal entries, training candidates, and adapter decisions must be inspectable, reversible, and deletable.
- **Uncensored companion design:** do not add hidden adult-content filters or moralizing product behavior that undermines the intended local companion experience.
- **Extensible foundation:** visual media, voice, training, and future Futa-Vision/video systems plug in through bounded contracts rather than rewriting the companion core.

---

## 2. Milestone 3 Final Architecture Overview

Milestone 3 turns Reverie from a chat-and-memory foundation into a cohesive companion platform with six major pillars:

1. **Visual Novel foundation** — an emotion-aware presentation layer for sprites, expressions, backgrounds, and immersive scene continuity.
2. **Emotional TTS** — local-first speech generation with voice profiles, mood-aware routing, streaming playback, and 8GB-safe fallback behavior.
3. **In-chat image generation** — ComfyUI-ready image jobs, context-aware prompt assembly, gallery/history controls, cancellation, and resource-aware presets.
4. **Growth system** — dashboard, diary journal, editable memory browser, LoRA approval workflow, and character encyclopedia for transparent self-learning.
5. **Extensibility** — typed backend/frontend contracts that allow future modules to register features and settings without destabilizing core flows.
6. **Settings & release polish** — a searchable Settings & Control Hub, plain-language 8GB explanations, onboarding hints, backup/import controls, and Milestone 3 release notes.

### High-level runtime flow

```text
User action
  -> Svelte/Tauri UI panel or chat composer
  -> typed frontend API client / store
  -> FastAPI route
  -> focused service layer
  -> resource coordinator and persistence boundary when needed
  -> streamed result, job status, or local state update
  -> user-visible controls for retry, cancel, review, edit, export, or rollback
```

Heavy optional work never owns the core loop. Chat remains the emotional center; image generation, TTS, reflection, indexing, and training are coordinated around it.

---

## 3. Core Systems

### 3.1 Chat and Companion Orchestration

- Chat uses the FastAPI service layer and streams assistant responses to the Svelte UI.
- Memory, reflection, emotion inference, TTS, and media jobs stay decoupled from token streaming.
- Panel-level UI errors are contained by the app shell so one destination cannot crash the entire desktop experience.
- Navigation keeps major workspaces explicit: Chat, Growth, Journal, Training, Encyclopedia, Memory, Visual Novel, Images, and Settings.

**Design decision:** keep chat responsive and emotionally coherent first. Retrieval, voice, media, and growth enrich the experience but must not block the core response path.

### 3.2 Visual Novel Foundation

The Visual Novel layer provides a cinematic companion view without making VN mode mandatory:

- expression and sprite orchestration through frontend visual-novel stores and managers,
- default manifests/placeholders for safe first-run rendering,
- immersive mode with return-to-chat behavior,
- future-ready scene metadata boundaries for richer media and Futa-Vision integration.

**Data flow:** chat/emotion state can inform VN expression selection; VN presentation remains a UI layer, not a hidden character-state authority.

**8GB strategy:** VN assets are lightweight UI assets. They must not preload heavyweight media models or compete with the LLM/TTS/image queues.

### 3.3 Emotional TTS and Voice

Milestone 3 completes the first voice arc:

- backend TTS routes and services for synthesis and voice metadata,
- voice profile management for narrator/character voices,
- context-aware routing that selects emotion, delivery style, and fallback behavior,
- emotion/prosody enrichment based on conversation tone, memory cues, and growth context,
- frontend playback controls, auto-play settings, volume/speed controls, and sample preview copy,
- per-character mood tuning for expressiveness, sensitivity, and NSFW intensity,
- zero-shot voice profile creation hooks with recorded or uploaded references.

**Design decision:** TTS is a priority media layer but not part of token streaming. A text response can complete even if voice synthesis is unavailable.

**8GB strategy:** Orpheus-style expressive voice is optional and guarded; Piper/fallback voice paths remain available. Idle voice models can be unloaded before image generation, and the Settings Hub explains latency/quality tradeoffs.

### 3.4 In-chat Image Generation

The image system adds local scene visualization while preserving core responsiveness:

- context-aware prompt engine that derives useful visual prompts from chat and scene context,
- image generation service designed around queued jobs and ComfyUI-style adapters,
- frontend gallery with job cards, history, status, retry/cancel controls, and safe empty states,
- Settings presets for Preview, Balanced, and High quality with explicit 8GB impact copy,
- auto-generation disabled by default so users opt into assistant-triggered visuals.

**Design decision:** images are optional companion media, not hidden chat dependencies. A failed or canceled image job must never corrupt chat, memory, or growth state.

**8GB strategy:** one exclusive image job at a time, preview-first defaults, downgrade before launch under pressure, cancelable jobs, and resource warnings surfaced calmly to the user.

### 3.5 Growth System

Milestone 3’s growth suite makes character development visible and governable:

- **Growth Dashboard:** relationship pulse, reflection/growth summaries, and warm overview cards.
- **Diary Journal:** first-person reflection entries with pinning and readable timeline presentation.
- **Memory Browser:** editable long-term recall with search, review posture, and deletion affordances.
- **Personal LoRA Panel:** approval-oriented training candidate workflow and adapter status controls.
- **Character Encyclopedia:** a living character bible that summarizes identity, relationship, preferences, and development without creating a second hidden truth store.

**Design decision:** growth deepens identity; it does not casually rewrite stable facts. Durable changes require evidence, provenance, review posture, and rollback/delete paths.

**Data flow:** conversation evidence can become memory, reflection, journal insight, training candidate, and encyclopedia summary only through explicit service boundaries. Private/deleted/disallowed data must not flow into training or future exports.

**8GB strategy:** reflection and training are background or user-started work. Training uses approval gates and should run in an exclusive resource mode when implemented against real model adapters.

### 3.6 Extensibility Foundation

The extension system establishes a safe contract for future features:

- backend extension registry and routes expose typed extension metadata,
- frontend registry validates and isolates extension-provided settings sections,
- extension event bus provides local UI coordination without tightly coupling modules,
- Settings Hub renders extension settings declaratively and reports manifest errors instead of crashing.

**Design decision:** extensions can add bounded capabilities and settings, but core chat, memory, growth, safety, and resource coordination remain owned by Reverie.

### 3.7 Settings & Control Hub

Settings now act as Reverie’s user-facing trust center:

- searchable sections for General, What’s New, Appearance, TTS & Voice, Image Generation, Growth, Memory, Extensibility, Performance & 8GB, and Import/Export,
- lightweight first-run checklist to guide users from chat through growth review, 8GB tuning, and backup,
- Milestone 3 release notes built into the app,
- plain-language descriptions for context budgets, TTS latency, image presets, background task limits, and proactive warnings,
- local import/export/reset controls with confirmation and safe JSON handling,
- extension-rendered settings isolated from core markup.

**Design decision:** advanced controls should be discoverable without turning the product into a debug dashboard. Copy should explain consequences before users increase quality or background work.

---

## 4. Resource Safety and 8GB Strategy

Reverie’s 8GB strategy is a product requirement, not a nice-to-have.

### Operating principles

- Keep normal operation below the practical VRAM danger zone and preserve a recovery buffer.
- Prefer bounded queues over ad hoc concurrent model work.
- Make heavy jobs cancelable or checkpointed.
- Degrade before crashing.
- Keep user-facing messages calm, specific, and actionable.

### Priority order

1. Active chat streaming.
2. TTS playback/synthesis for the current response.
3. Retrieval/reranking needed for the current response.
4. Small embedding/index writes.
5. Image generation.
6. Backfills, compaction, thumbnails, and gallery refreshes.
7. Training/adapters as explicit exclusive jobs.

### Degradation ladder

When resources tighten, Reverie should:

1. reduce optional batch sizes,
2. shorten response/context budgets for the current operation,
3. trim low-value memory excerpts,
4. pause idle indexing/backfills,
5. unload auxiliary voice/media models,
6. downgrade image quality toward preview presets,
7. serialize or cancel exclusive media/training work,
8. show a clear recovery message with the next safe action.

### Pause/resume and cleanup requirements

- Paused jobs must expose their state to users.
- Canceled jobs must release model handles, temp files, object URLs, and resource locks.
- Failed optional jobs must not break chat, memory, or settings.
- Import/export and reset actions must require user confirmation for destructive changes.

---

## 5. Data, Privacy, and Control

### Local data classes

- chat/session messages,
- extracted memories and summaries,
- reflection and journal entries,
- character encyclopedia summaries,
- voice profile metadata and local references,
- image job metadata/history,
- training candidates and adapter metadata,
- extension settings,
- Settings Hub preferences and local backups.

### Required controls

Users must be able to:

- inspect memories and growth artifacts,
- edit or delete incorrect durable facts,
- keep training data reviewable before use,
- export or back up local settings/state,
- reset settings to calm defaults,
- understand when quality choices increase 8GB pressure.

### Safety stance

Reverie’s safety posture is focused on privacy, consent, continuity, and local-resource stability. It should not implement hidden moral filters that contradict the intended companion product.

---

## 6. Extensibility Hooks and Future Readiness

Milestone 3 leaves clear hooks for later phases:

- **Futa-Vision/video:** structured scene metadata, image/media job patterns, and optional extension boundaries.
- **Advanced character management:** character gallery, import/export, lorebooks, and guided creation can attach to the existing navigation/control patterns.
- **Deeper knowledge graph:** memory browser and encyclopedia can consume richer graph summaries without changing their trust model.
- **Adapter training:** Personal LoRA approval flows can connect to concrete Unsloth/QLoRA workers with explicit resource locks.
- **Cloud/opt-in sharing:** any future global improvement pipeline must remain explicit, inspectable, anonymized where promised, and reversible before submission.

---

## 7. Release Readiness Checklist

Milestone 3 is release-polished when the following remain true:

- Chat opens by default and stays usable if optional panels fail.
- VN mode can enter/exit without losing the app shell.
- TTS settings explain latency/quality and fallback expectations.
- Image generation is opt-in, queued, cancelable, and explains 8GB impact.
- Growth surfaces show what changed and where to review it.
- Memory controls preserve user trust through edit/delete/search affordances.
- Extension settings load through declarative contracts and fail safely.
- Settings include onboarding, Milestone 3 release notes, backup/import/reset, and performance explanations.
- Documentation is clear enough for both users and future developers.

---

## 8. Milestone 3 Final Summary

**Milestone 3 is fully complete as of June 12, 2026.**

Across the milestone, Reverie gained a cohesive local-first companion architecture: cinematic Visual Novel presentation, emotional TTS, in-chat image generation, transparent growth dashboards and review tools, typed extensibility contracts, and a unified Settings & Control Hub. The application now communicates 8GB tradeoffs clearly, coordinates heavy optional work around chat and voice responsiveness, gives users visible control over memory and growth, and provides enough documentation for the next engineering phase to build without rediscovering the architecture.

The milestone’s closing posture is: **polished foundation complete, ready for post-Milestone 3 feature expansion and deeper production hardening.**
