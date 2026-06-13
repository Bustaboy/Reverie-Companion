# Reverie

**The offline adult AI companion that feels truly alive.**

> "Your characters should remember what matters, stay visually and emotionally recognizable, grow from evidence, and feel present across long conversations, images, voice, and shared history — all while running locally on a reasonably modern gaming PC or laptop."

**Reverie** is a fully local, uncensored desktop AI companion focused on deep long-term memory, believable character continuity, transparent self-learning, local image/voice immersion, and warm premium adult roleplay.

---

## What is Reverie?

Reverie is built around one product promise:

> **A private local companion who feels like a persistent person, not a prompt wrapper.**

The app prioritizes:

- **True long-term memory** with local LanceDB persistence, Ollama embeddings, bounded prompt context, and user-editable recall.
- **Character continuity** through a versioned `CharacterBlueprint`, relationship state, visual identity, roleplay policy, prompt compiler, selected-character chat, and character-scoped memory/reflection.
- **Moment Capture**: image generation as companion presence, using character identity, scene state, memory, and gallery feedback instead of generic prompt gambling.
- **Genuine self-learning and growth** through reflection, first-person journaling, growth notices, reviewable visual changes, and future user-approved training artifacts.
- **Roleplay-first adult freedom**: fictional adult fantasy stays in-character by default, without moralizing interruptions or hidden adult-content filters.
- **User trust and control**: local-first storage, inspectable journals, editable memories, opt-in training collection, approved-only training jobs, deletion-aware pipelines, and rollback-friendly design.
- **Strict optimization for RTX 4070 8GB mobile** with resource coordination, queued media jobs, conservative context budgets, and graceful degradation.
- **Modern, warm, immersive UX** across Chat, Visual Novel, TTS, Images, Growth, Journal, Memory, Training, Encyclopedia, Settings, and the planned Companion Genesis creator.

---

## Current Capabilities

Milestones 1–4 are complete. Reverie currently includes:

- FastAPI backend with Ollama chat, streaming SSE responses, and health diagnostics.
- Local memory foundation using Ollama embeddings plus embedded LanceDB, with optional mem0 write-through.
- Growth orchestration that prepares memory context, reflection journal context, rare growth notifications, and Personal LoRA collection hooks without blocking active chat.
- Self-reflection journal API and frontend Journal panel for private, inspectable growth entries.
- Unified Settings & Control Hub for memory, reflection, TTS, image generation, performance presets, extensions, backup/import/reset, and Milestone 3 release notes.
- Training UI for Personal LoRA review: collection opt-in, training opt-in, pending candidate approval/rejection/deletion, and safe starter training jobs.
- Visual Novel mode, emotional TTS playback, local image generation gallery, Growth Dashboard, Memory Browser, and Character Encyclopedia foundations.
- Tauri + Svelte desktop shell with warm dark styling, local backend integration, and first-run Milestone 3 onboarding.

---

## Current Development Focus

Reverie has closed **Milestone 4 — Character Runtime & Capability Alignment**. The app now has the runtime substrate that lets future creator choices affect prompt assembly, selected-character chat, local persistence, character-scoped memory/reflection, relationship state, visual identity summaries, and roleplay-first integrity controls.

The full immersive character creator is still intentionally **not** being built before the runtime can honor its choices. The guiding strategy remains:

```text
Build the powers first.
Then build the ritual that lets users command those powers.
```

The current focus moves to **Milestone 5 — Moment Capture & Visual Continuity**, which elevates image generation into character-linked embodied memory.

Milestone 6 adds the practical creator foundation.

Milestone 7 builds the immersive **Companion Genesis** creator experience.

---

## Roleplay Philosophy

Reverie is a roleplay companion first.

Fictional adult fantasy is not treated as real-world intent. The app should preserve in-character immersion for adult fantasy, dark romance, power exchange, villain arcs, fantasy violence, and other user-chosen fictional scenarios.

The hard product boundary is simple:

```text
18+ only. No underage sexual content. No deliberately childlike sexual presentation.
```

Do not over-police normal adult character design. Cute adult, petite adult, youthful adult, early-20s adult, anime-stylized adult, soft-featured adult, short adult, tall adult, thin adult, curvy adult, muscular adult, and plus-size adult characters are valid.

---

## Grok + Codex Workflow

Reverie is developed with a two-run implementation workflow:

1. **Grok** acts as Coding Director and writes one detailed implementation prompt.
2. The same prompt is run twice in **Codex** as Run A and Run B.
3. Each run produces a separate branch, PR, or patch.
4. Grok reviews both outputs for architecture, UX, 8GB safety, tests, maintainability, roleplay integrity, and vision alignment.
5. The better version is accepted or a small synthesis patch is requested.
6. Accepted work updates tests and docs when behavior changes.

This workflow is documented in [`prompts/GROK_CODING_DIRECTOR_WORKFLOW.md`](prompts/GROK_CODING_DIRECTOR_WORKFLOW.md).

---

## Documentation

Core docs:

- [Source of Truth](Reverie_Source_of_Truth.md)
- [Development Plan](DEVELOPMENT_PLAN.md)
- [Character Creator Capability Matrix](CHARACTER_CREATOR_CAPABILITY_MATRIX.md)
- [Roleplay-First Character Integrity Policy](ROLEPLAY_FIRST_CHARACTER_INTEGRITY_POLICY.md)
- [Global Coding Prompt](prompts/GLOBAL_CODING_PROMPT.md)
- [Grok Coding Director Workflow](prompts/GROK_CODING_DIRECTOR_WORKFLOW.md)
- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)

Key skill prompts for Grok/Codex:

- [Character Runtime & Creator](prompts/skills/character-runtime-creator.md)
- [Roleplay-First Character Integrity](prompts/skills/roleplay-character-integrity.md)
- [Moment Capture & Visual Continuity](prompts/skills/moment-capture-visual-continuity.md)
- [Companion Genesis UX](prompts/skills/companion-genesis-ux.md)
- [Character Quality Evals](prompts/skills/character-quality-evals.md)
- [Memory/RAG System](prompts/skills/memory-rag-system.md)
- [Self-Learning Growth](prompts/skills/self-learning-growth.md)
- [Self-Reflection Journal](prompts/skills/self-reflection-journal.md)
- [8GB VRAM Optimization](prompts/skills/8gb-vram-optimization.md)
- [8GB Local AI Patterns](prompts/skills/8gb-local-ai-patterns.md)
- [Tauri/Svelte UI Patterns](prompts/skills/tauri-svelte-ui-patterns.md)
- [FastAPI Backend Patterns](prompts/skills/fastapi-backend-patterns.md)
- [Futa-Vision Integration](prompts/skills/futavision-integration.md)

---

## Current Status

- ✅ **Milestone 1 — Foundation**: repository structure, backend shell, frontend shell, core documentation, initial chat path.
- ✅ **Milestone 2 — Memory & Self-Learning**: memory context, reflection journal, growth orchestration, Journal/Settings/Training UI, growth notifications, and Personal LoRA foundation.
- ✅ **Milestone 3 — Immersion & Production Foundations**: Visual Novel foundation, emotional TTS, local image generation, growth visibility, extensibility, 8GB resource guardrails, Settings Hub, onboarding, and release documentation.
- ✅ **Milestone 4 — Character Runtime & Capability Alignment**: CharacterBlueprint runtime, selected-character chat, character-scoped memory/reflection, relationship/growth/visual identity schemas, roleplay-first policy, and minimal frontend shell.
- 🚧 **Milestone 5 — Moment Capture & Visual Continuity**: current focus.

---

## Philosophy

We are building companions users can form real, long-term emotional connections with: characters that remember what matters, stay recognizable, grow from evidence, feel present through media, and keep the user in control.

Reverie should feel intimate and magical on the surface, while staying boringly reliable underneath. The human sees a companion coming alive. The backend sees schemas, provenance, tests, and resource budgets.

---

**Reverie**  
June 2026
