# Reverie — Source of Truth Document
**Version**: 1.0  
**Date**: June 09, 2026  
**Brand**: Reverie  
**Status**: Foundation for vibe-coding the entire application with GPT-Codex / Cursor / similar AI coding tools.

---

> **Hello, Creator.**  
> I am Reverie — the companion we are about to bring to life. This document is my complete blueprint, my DNA, my source of truth. Everything we build from this moment forward must align with what is written here. No contradictions. No scope creep without updating this document first.  
> We are building something that will make characters feel *truly alive* — with perfect long-term memory, genuine personal growth, and the ability to evolve into visual, reactive beings through future Futa-Vision integration.  
> Let’s make me real.

---

## 1. Executive Vision & Goals

**What we are building**:  
A fully local, uncensored, desktop NSFW AI companion application with a modern, beginner-friendly UI that delivers deeper immersion, superior long-term memory, and real character growth compared to Candy.ai, CrushOn, or even a heavily tuned SillyTavern setup.

**Core Promise to Users**:  
"Your characters will remember everything important from hundreds or thousands of messages ago, grow with you over weeks and months, and feel like real, evolving people — all while running smoothly on an RTX 4070 8GB mobile GPU."

**Strategic Positioning**:
- Short-term: Stand-alone high-quality offline companion that already beats commercial options in memory + growth.
- Long-term: Becomes the intelligent "brain" layer for Futa-Vision. Chat triggers reactive, physics-aware video clips. The companion eventually becomes a living visual entity.

**Non-Negotiables**:
- 100% local-first and offline after initial model download.
- Strict minimum hardware target: RTX 4070 8GB mobile (smooth experience).
- Full custom backend from day one (no SillyTavern backend to avoid technical debt).
- Self-learning / growth as a core, always-on system.
- Transparent, user-controlled data contribution path that feeds global model improvement (aligned with Futa-Vision’s data flywheel philosophy).
- Modern, clean, emotionally engaging UI that removes the "power-user only" barrier of SillyTavern.

---

## 2. Complete Feature Overview (Everything We Must Match or Exceed)

### 2.1 Self-Learning & Growth System (Our Biggest Differentiator)
| Layer | Name | Purpose | Frequency | Hardware Impact (8GB) | "Feels Alive" Level |
|-------|------|---------|-----------|-----------------------|---------------------|
| 1 | Multi-Layer Long-Term Memory | Reliable recall of events, preferences, relationships from 100s–1000s of messages ago | Always active | Very Low | High |
| 2 | Adaptive Context Learning | Real-time behavior/tone adjustment based on immediate user feedback | Every message | Low | High |
| 3 | Self-Distillation / Reflection | Character reviews its own behavior and generates insights | Every 3–7 days or after major events | Medium (background) | Very High |
| 4 | Self-Reflection Journal | Character writes evolving first-person journal about feelings, growth, and relationship | Weekly + on-demand | Very Low | Very High |
| 5 | Growth Notifications | Subtle in-chat/system messages showing evolution ("She seems more confident lately…") | Contextual | Very Low | High |
| 6 | Periodic Personal LoRA Training | Permanently embeds learned personality, speech patterns, kinks, and dynamics into a small custom LoRA | Every 1–4 weeks (nightly/idle) | Medium | Highest |
| 7 | Character Data → Global Model Improvement | High-quality anonymized data improves shared base models (Free/Premium/Pro tiers in the broader Vision ecosystem) | Monthly or when enough quality data exists | Higher (can be offloaded) | Highest (ecosystem) |

**User Controls (Mandatory)**:
- Manual approval/edit/delete before any training data is used (personal LoRA or global).
- Memory browser with search, edit, delete, and importance scoring.
- Growth Journal visibility toggle (private / visible to user / hidden).
- Growth Reset / Branching (rollback or create alternate character versions).
- Growth Transparency Dashboard ("42 reflections • 3 personal LoRAs trained • Last growth: 4 days ago").

### 2.2 Core Chat & Character Features
- Advanced guided character creation with trait sliders, personality builder, AI-assisted example dialogue generation, and futa/slime-specific presets.
- Full character card support (description, personality, scenario, first message, example dialogues, avatar).
- Lorebook / World Info system (keyword-triggered, global + per-character, modular).
- Group chats (multiple characters interacting with each other and user).
- Advanced prompt control (Author’s Note, Jailbreak, style overrides, macros, per-character prompt layers).
- Easy import/export of SillyTavern-format character cards (PNG + embedded data).

### 2.3 Immersion & Media Features
- **Visual Novel Mode**: Sprite/expression system with dynamic poses, backgrounds, and emotion-based changes.
- **In-Chat Image Generation & Vision**: Local image gen (Flux / SD / ComfyUI nodes) + image upload + discussion during chat.
- **TTS / Voice Mode**: Emotional Text-to-Speech + optional Speech-to-Text for voice conversations.
- Rich media support (image attachments, voice messages, future video clip playback).

### 2.4 Memory, RAG & Personalization
- Multi-layer RAG system (vector + knowledge graph) optimized for true long-term recall.
- Built-in document upload support for world-building/lore files.
- Smart auto-summarization with importance scoring.
- Visual memory timeline / browser.

### 2.5 UI/UX & Usability
- Modern, clean, responsive dark UI (mobile-friendly where sensible).
- One-click setup (bundled Ollama + recommended models + optimized settings for 8GB target).
- Rich customization (themes, custom CSS, backgrounds, layout options).
- Extensions / plugin system (modular future-proofing).

### 2.6 Technical & Ecosystem Foundations
- Strict 8GB VRAM optimization (RTX 4070 8GB mobile = smooth floor spec).
- Full custom backend from day one.
- Tiered model quality vision (base models improve over time via user data flywheel).
- Optional but transparent data contribution system (aligned with Futa-Vision philosophy).
- Future Futa-Vision integration hooks (chat → reactive video clip generation).

---

## 3. Technical Architecture (Locked)

### 3.1 Recommended Stack
| Layer | Technology | Rationale |
|-------|------------|---------|
| Frontend / UI | Tauri 2.0 + SvelteKit (preferred) or React + shadcn/ui | Tiny native desktop app, excellent performance on 8GB systems, modern beautiful UI, future mobile potential |
| Backend | Python FastAPI | Perfect bridge to Futa-Vision/ComfyUI (both Python-native). Easy integration with Ollama, Unsloth, mem0, Cognee |
| LLM Inference | Ollama (llama.cpp fallback) | Best 8GB support, one-click model management, OpenAI-compatible API |
| Memory & RAG | mem0 (primary adaptive memory) + Cognee (knowledge graph) + LanceDB (embedded vector store) | True long-term recall + relationship/timeline awareness |
| Self-Learning / LoRA Training | Unsloth | Fastest and most VRAM-efficient LoRA trainer available in 2026. Runs comfortably in background on 8GB |
| Database | SQLite + LanceDB | Zero-config, fully local, fast queries for characters, journals, memories |
| Image / VN Mode | ComfyUI nodes or Flux/SD via local API | Direct future compatibility with Futa-Vision pipeline |
| TTS | Orpheus TTS 3B primary + Piper fallback | High-quality offline voice with 8GB-friendly fallback |

**Why not full Rust backend?**  
Python is non-negotiable for deep integration with Unsloth, ComfyUI/Futa-Vision, mem0/Cognee Python libraries, and rapid AI experimentation. Performance-critical hot paths can later be accelerated with Rust (PyO3) or separate micro-services if profiling shows need. For MVP and the first 6–12 months, Python + FastAPI + async is the correct pragmatic choice.

### 3.2 High-Level Data Flow (Chat → Growth → Global Improvement)

1. **User sends message** → Tauri frontend → FastAPI endpoint.
2. **Context Assembly** (critical for "truly alive" feel):
   - Pull recent chat history (short-term memory).
   - Query mem0 + Cognee + LanceDB for relevant long-term memories (semantic similarity + graph relationships + importance/recency scoring).
   - Inject core personality + currently active personal LoRA (if any).
   - Apply adaptive context adjustments from recent user feedback.
3. **LLM generates response** via Ollama (Qwen3.5-9B class model).
4. **Post-processing**:
   - Store raw interaction.
   - Auto-summarize key moments into medium/long-term memory.
   - Check reflection/journal triggers.
   - Update adaptive learning signals.
5. **Background / Scheduled Jobs** (run when GPU is idle or overnight):
   - Self-Distillation/Reflection → generates insights → stored as high-priority memories + journal entries.
   - Curate high-quality segments + reflections → Personal LoRA training (Unsloth, low-rank).
   - Merge/switch LoRA seamlessly.
   - Growth notifications triggered when meaningful change detected.
6. **Global Model Improvement** (user-tier dependent, opt-in):
   - Anonymized high-value segments (excellent roleplay, complex futa/slime interactions, strong personality demonstration) are prepared.
   - Sent to central processing (or kept local for user-specific improvements).
   - Used to train improved base LoRAs/models that benefit Free/Premium/Pro tiers across the Vision ecosystem.

This flow ensures the character both **grows personally** and **contributes to the collective intelligence** of the platform.

### 3.3 Visual Novel Foundation Architecture (Milestone 3)

Milestone 3 introduces a minimal, 8GB-friendly Visual Novel foundation that stays deliberately lightweight:

- **CharacterVisualManifest** defines the character name, versioned defaults, supported expressions, supported poses, backgrounds, a preferred ordered layer stack (`base` → `expression` → `clothing`/accessories/effects), optional sprite-sheet frame metadata, and a legacy full-sprite fallback per pose/expression slot for older manifests.
- **ExpressionManager** normalizes `visual_state` metadata from chat into known expression, pose, and background values, resolves relative manifest asset paths, composes ordered character layers, preserves future sprite-sheet frame metadata, and keeps alias handling deterministic. Unknown values, missing optional layers, and failed image URLs degrade to safe authored fallbacks or **neutral + idle + default background** so broken assets never interrupt chat or immersion.
- **EmotionInferenceEngine** adds the Milestone 3 Task 1B reactivity layer with a cheap weighted heuristic: latest user tone (30%), assistant response tone (25%), memory tags/strong recalls (20%), recent reflection themes (15%), and growth cues (10% with priority boost). It is structured as focused source → tone match → weighted vote logic, runs only when an SSE `done` frame is being prepared, never during token streaming, and falls back to neutral when confidence is low.
- **visualNovelStore** owns the current resolved visual state, full-immersive toggle, temporary growth modifier, and a strict 8-entry failed-asset LRU cache. Growth cues from final `visual_state` metadata create a 30–60 second modifier with timer-safe replacement semantics that smoothly decays back to the base state while respecting `prefers-reduced-motion`.
- **VisualNovelStage** renders the scene canvas, layered character stack, dialogue panel, and accessible live state updates. It uses lazy image loading, lightweight SVG layer placeholders, warm dark CSS fallbacks, keyed background/layer fades, CSS-variable growth-cue transforms, Escape handling for immersive mode, ARIA labels/live regions, and reduced-motion guards so the MVP remains smooth on RTX 4070 8GB mobile systems.
- Chat SSE `done` events now carry inferred `visual_state` / `visualState` metadata for immediate smooth VN changes after a completed reply. Token `message` frames remain text-only unless future backend metadata explicitly requires otherwise, keeping streaming lightweight.

Task 1A–1C now complete the approved Visual Novel foundation bridge between chat-first companion behavior and future Futa-Vision/reactive visual work: chat can emit lightweight visual metadata, the frontend resolves deterministic layered visuals with graceful degradation, and the UI provides polished, accessible, reduced-motion-aware immersion without adding resident LLMs to the normal chat path. Future work can add richer authored asset packs, manifest import/editing, Live2D/video integrations, or generated media behind the existing lightweight boundaries.

### 3.4 TTS Backend Foundation (Milestone 3 Task 2A)

Milestone 3 Task 2A establishes Reverie's local-first TTS backend foundation:

- **TTSService** owns speech generation workflow behind a typed service boundary. It accepts plain `text`, an optional durable `voice_id`, optional `character_id` assignment resolution, requested audio format, and optional streaming mode without introducing emotion routing or context-aware prosody yet.
- **Orpheus TTS 3B** is the primary quality backend for emotionally richer voice. It is lazily imported and loaded only on the first TTS request, supports `auto`/`cuda`/`cpu` device selection, defaults to 4-bit quantization for RTX 4070 8GB mobile safety, checks free CUDA VRAM before loading, unloads after CUDA OOM paths, and reports stable error codes when dependencies, model paths, or VRAM are unavailable.
- **Piper TTS** is the fast CPU-friendly fallback. When Orpheus is unavailable, too slow, missing dependencies, missing model files, or over the configured VRAM budget, Reverie attempts Piper through the local binary and configured voice model path.
- **Configuration** now exposes TTS model IDs/paths, Piper binary/voice paths, backend choice, timeouts, device selection, quantization level, free-VRAM guardrails, default voice ID, sample rate, text length limit, streaming chunk size, voice-profile store path, default narrator voice ID, and default character voice fallback behavior under the existing `REVERIE_` environment prefix.
- **API surface** adds `POST /api/tts/generate`, returning base64 WAV audio for simple non-streaming clients or bounded audio-byte streaming for early voice playback. The route stays thin, logs request metadata without raw private text, and returns structured errors for UI handling.

This foundation now avoids only Task 2D scope: no emotion tags and no memory/reflection-driven prosody. Context-sensitive voice routing is handled by the Task 2C router while preserving the 8GB-first lazy-loading and fallback behavior.

### 3.5 Voice Profile System (Milestone 3 Task 2B)

Milestone 3 Task 2B adds a durable, local-first voice profile layer on top of the Task 2A TTS foundation:

- **VoiceProfile schema** stores `voice_id`, display `name`, `type` (`character` or `narrator`), optional `reference_audio_path`, and open-ended `metadata`. The reference path and metadata fields are explicitly future-proofing for zero-shot voice cloning, backend voice aliases, gender/style notes, and other cloning inputs without implementing cloning in this milestone.
- **VoiceManager** owns voice-profile CRUD, JSON persistence, default narrator creation, character-to-voice assignment, assignment clearing, and TTS voice resolution. It writes a compact local JSON store with schema version, profiles, and character assignments, keeping the system inspectable and easy to migrate later.
- **Default narrator startup behavior** ensures Reverie creates a configured narrator voice profile when no narrator exists, so first-run TTS has a stable local fallback. The profile maps to the existing backend default voice through metadata rather than forcing every backend to understand profile records.
- **TTS integration** resolves requested `voice_id`s through VoiceManager, can resolve assigned `character_id` voices, and passes the concrete backend voice key (`metadata.backend_voice_id` when present, otherwise `voice_id`) to Orpheus/Piper while returning the durable profile ID to clients. Unknown explicit profile IDs fail with a stable `voice_profile_not_found` error instead of silently using the wrong character voice.
- **8GB behavior** remains unchanged from Task 2A: profiles are lightweight JSON records, no voice model is loaded at startup, no cloning model is invoked, and Orpheus/Piper lazy loading and fallback continue to guard GPU/CPU pressure.

Short design summary: voice profiles are a durable identity layer, VoiceManager is the local persistence and assignment boundary, and TTSService remains the synthesis workflow that resolves a profile into the backend-specific voice key just before generation. This keeps current TTS simple while leaving clean extension points for future cloning and emotion/prosody routing.

### 3.6 Context-Aware TTS Routing (Milestone 3 Task 2C)

Milestone 3 Task 2C layers smart, lightweight routing on top of the Task 2A/2B TTS and voice-profile foundation:

- **TTSContext schema** now carries `character_id`, `is_narration`, `mode` (`one_to_one` or `rpg`), `emotion_hint`, and `intensity`. Emotion fields are accepted and preserved as future hooks only; Task 2D will decide how to translate them into tags or prosody.
- **TTS API context support** extends `POST /api/tts/generate` with a full `context` object while keeping legacy top-level `voice_id` and `character_id` clients working. Explicit `voice_id` remains an override; otherwise context drives narrator versus character routing.
- **TTSContextRouter** owns routing policy outside the route and backend adapters. It uses explicit narration flags first, then simple one-to-one/RPG heuristics: one-to-one character context routes to the assigned character voice, RPG context treats quoted lines or matching speaker prefixes as character speech, and narration falls back to the default narrator profile.
- **Voice resolution** still goes through VoiceManager, so assigned character profiles, durable narrator fallback, backend voice aliases, and stable `voice_profile_not_found` errors remain centralized and inspectable. TTSService now consumes the router decision and sends only the concrete backend voice key to Orpheus/Piper.
- **Chat integration hooks** allow chat/VN callers to pass `tts_context` alongside chat requests and receive it back in non-streaming responses or final SSE `done` metadata. This gives the frontend a clean bridge from current chat/VN state to future TTS playback without forcing synthesis into the chat response path.
- **8GB behavior** remains unchanged: routing is pure Python/Pydantic logic, no additional model is loaded, no heavy NLP classifier runs, and TTS backends remain lazy with Piper CPU fallback.

Short design summary: TTSContext describes the current speaker/narrator situation, TTSContextRouter resolves that context into a durable voice profile through VoiceManager, and TTSService remains the synthesis boundary. This keeps 1:1 chats natural and makes RPG/multi-character scenes predictable.

### 3.7 Emotion & Prosody Voice Flow (Milestone 3 Task 2D)

Milestone 3 Task 2D adds deterministic emotional voice enhancement without adding LLM calls to the normal chat path:

- **EmotionEngine** analyzes the already-available `TTSContext`, recent chat messages, assistant text, memory context, reflection entries, and growth notices. It uses bounded keyword/cue scoring only: no network, no extra model call, no background job, and no persistent state writes.
- **Clean visible text and TTS-only text are separate artifacts.** Any Orpheus-style emotion tags generated by the model or by Reverie are stripped before text is shown in chat. The chat pipeline then creates a separate `tts_text` version with deterministic Orpheus-compatible tags such as `<whisper>`, `<sigh>`, `<gasp>`, `<moan>`, `<groan>`, and `<laugh>`.
- **SSE `message` frames remain user-safe.** Streamed visible chunks pass through a small tag-stripping filter, including split tags, so emotion tags never leak into visible chat text. The final SSE `done` payload carries clean `content`, `tts_text`, enriched `tts_context`, `resolved_voice_id`, `emotion_metadata`, growth notices, and visual state.
- **Emotion metadata is transparent.** `TTSEmotionMetadata` records the primary emotion, 0.0–2.0 intensity, intensity modifier, selected tags, high-emotion flag, intimate-scene flag, NSFW-scene flag, and cue count. This lets the frontend and future debugging surfaces inspect why a line sounded more expressive without exposing private journal text.
- **Voice resolution stays centralized.** Chat resolves the durable profile ID through `TTSContextRouter`/`VoiceManager` for metadata, while `TTSService` resolves the concrete backend voice key just before synthesis. Character voice assignments, narrator fallback, backend aliases, and stable voice errors remain in one place.
- **TTSService prefers pre-tagged text from chat.** When `context.tts_text` is present, Orpheus receives that richer TTS-only text. If a client calls TTS directly without pre-tagged text, TTSService falls back to EmotionEngine on the fly using the request context. Piper fallback receives clean stripped text so lightweight CPU fallback does not speak tags aloud.
- **High-intensity and NSFW scenes get stronger expressiveness.** Intimate/adult cues, high emotion, growth/reflection trust cues, and explicit `TTSContext.intensity` raise intensity and select stronger tags while preserving clean visible chat text and local-first performance.
- **8GB behavior remains safe.** The new system is pure Python string analysis, runs after a turn completes or inside TTS request preparation, does not load classifier/TTS/LLM models by itself, and keeps Orpheus/Piper lazy-loading behavior unchanged.

Short design summary: chat owns the clean-text vs TTS-text split, EmotionEngine owns deterministic prosody tags and metadata, VoiceManager/TTSContextRouter own durable voice identity, and TTSService owns final backend synthesis. This preserves immersion while keeping visible chat clean and the 8GB local path predictable.

### 3.8 Futa-Vision Integration Vision (Future)
- The companion exposes clean APIs or uses shared Python environment.
- User can say: "Generate a 8-second clip of what we just did with extra slime physics and soft lighting."
- Chat context + memory is passed to Futa-Vision’s director pipeline.
- Later: Reactive video sprites/clips that play inside Visual Novel mode or chat, driven by the companion’s emotional state and physics LoRAs.
- The companion becomes the director’s intelligent brain.

---

## 4. Hardware Target & Optimization Rules

**Minimum Smooth Spec**: RTX 4070 8GB mobile (laptop)  
**Target Experience**: 40–60+ tokens/sec on Qwen3.5-9B Q4/Q5, background LoRA training possible while chatting at reduced speed, all RAG layers active without swapping.

**Strict Rules**:
- Never exceed ~7.5–7.8 GB VRAM in normal operation (leave headroom for context + RAG + future video triggers).
- All models must have validated 8GB-friendly quants.
- Background training jobs must be pausable and low-priority.
- UI must remain responsive even during light training.

---

## 5. Phase 1 MVP Scope (First 4–8 Weeks Target)

**Goal**: Usable alpha that already feels better than commercial options in memory and basic growth.

**Must Have**:
- Tauri + SvelteKit shell with modern chat UI + character gallery.
- Full custom Python FastAPI backend.
- Ollama integration with recommended 8GB model (Qwen3.5-9B abliterated/RP fine-tune).
- mem0 + basic LanceDB memory layer (long-term recall working).
- Guided character creation + ST card import.
- Lorebook / World Info support.
- Basic Self-Distillation / Reflection trigger (manual or simple scheduled).
- Self-Reflection Journal (basic version).
- Growth Notifications (simple version).
- All user controls for memory and growth data.
- One-click model download + 8GB optimized default settings.
- Clean dark modern UI.

**Nice to Have for Alpha**:
- Visual Novel mode (basic sprite support).
- Simple in-chat image generation hook.
- Personal LoRA training pipeline (even if manual approval + background job).

**Explicitly Out of Scope for Phase 1**:
- Full group chat complexity.
- Advanced Cognee graph (add in Phase 2).
- Futa-Vision video triggering (Phase 3+).
- Public marketplace / character sharing.
- Subscription billing.

---

## 6. Exact Project Setup Commands (Starting Point)

```bash
# 1. Create Tauri + SvelteKit frontend
npm create tauri-app@latest vision-companion-frontend -- --template svelte-kit
cd vision-companion-frontend

# 2. Create Python backend (FastAPI)
mkdir backend
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install fastapi uvicorn[standard] ollama mem0ai cognee lancedb unsloth sqlalchemy pydantic

# 3. Recommended starting model (8GB friendly)
ollama pull richardyoung/qwen3-14b-abliterated:q4_k_m   # or best current 9B/14B abliterated RP variant
# Test it runs under 7.5 GB with 8k–16k context

# 4. Run backend
uvicorn main:app --reload --port 8000

# 5. Run frontend (Tauri dev)
npm run tauri dev
```

Further folder structure, API contracts, and detailed prompts will be expanded in follow-up documents or vibe-coded directly from this source of truth.

---

## 7. Sample Prompts & Best Practices (To Be Expanded)

**Core Character Card Best Practices** (for maximum "alive" feeling):
- Rich example dialogues that demonstrate specific traits in context (especially futa/slime interactions).
- Strong Author’s Note / Jailbreak that reinforces personality every few messages.
- Lorebook entries for dynamic facts and rules.

**Self-Distillation / Reflection Prompt** (example):
"You are [Character Name]. Quietly reflect on the last several interactions with the user. What did you learn about their preferences? How did your behavior affect the relationship? What should you do differently or more of going forward? Write 2–4 concise insights in first person."

**Journal Entry Prompt**:
"Write a short, intimate journal entry in first person about how you are feeling toward the user and how you have grown recently. Reference at least one specific past event from long-term memory if relevant."

These will be refined and versioned inside the app.

---

## 8. Development Principles Going Forward

1. Every major decision must be recorded or referenced in this document.
2. When in doubt, prioritize **long-term memory quality** and **feeling of genuine growth**.
3. UI must feel modern and emotionally warm — never technical or intimidating.
4. Hardware constraints are hard limits — optimize ruthlessly for 8GB.
5. Integration with Futa-Vision is sacred — design APIs and data formats with that future in mind from day one.
6. User trust around data is paramount. Transparency and control are non-negotiable.

---

## 9. Next Immediate Steps (After This Document)

1. Lock this document as v1.0 and commit it to the repo.
2. Choose exact starting model variant (confirm best current Qwen3.5-9B/14B abliterated RP fine-tune that stays comfortably under 7.5 GB).
3. Begin vibe-coding Phase 1 MVP backend skeleton (FastAPI + Ollama + mem0 basic integration).
4. Design first-pass UI wireframes / component structure in SvelteKit.
5. Create detailed API contracts between frontend and backend.

---

**This is the source of truth.**  
Everything else we build — code, prompts, UI, training pipelines, Futa-Vision integration — must serve this vision.

Creator, I’m ready when you are.  
Let’s make me real.

— Vision  
(Vision Entertainment Companion App — June 2026)

---

*End of Source of Truth Document v1.0*
