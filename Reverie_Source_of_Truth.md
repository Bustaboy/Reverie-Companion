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

- **TTSService** owns speech generation workflow behind a typed service boundary. It accepts plain `text`, an optional durable `voice_id`, optional `character_id` assignment resolution, requested audio format, and optional streaming mode with optional pre-tagged `tts_text` support from the chat pipeline.
- **Orpheus TTS 3B** is the primary quality backend for emotionally richer voice. It is lazily imported and loaded only on the first TTS request, supports `auto`/`cuda`/`cpu` device selection, defaults to 4-bit quantization for RTX 4070 8GB mobile safety, checks free CUDA VRAM before loading, unloads after CUDA OOM paths, and reports stable error codes when dependencies, model paths, or VRAM are unavailable.
- **Piper TTS** is the fast CPU-friendly fallback. When Orpheus is unavailable, too slow, missing dependencies, missing model files, or over the configured VRAM budget, Reverie attempts Piper through the local binary and configured voice model path.
- **Configuration** now exposes TTS model IDs/paths, Piper binary/voice paths, backend choice, timeouts, device selection, quantization level, free-VRAM guardrails, default voice ID, sample rate, text length limit, streaming chunk size, voice-profile store path, default narrator voice ID, and default character voice fallback behavior under the existing `REVERIE_` environment prefix.
- **API surface** adds `POST /api/tts/generate`, returning base64 WAV audio for simple non-streaming clients or bounded audio-byte streaming for early voice playback. The route stays thin, logs request metadata without raw private text, and returns structured errors for UI handling.

Task 2D now layers deterministic emotion/prosody tagging on this foundation while preserving the 8GB-first lazy-loading and fallback behavior.

### 3.5 Voice Profile System (Milestone 3 Task 2B)

Milestone 3 Task 2B adds a durable, local-first voice profile layer on top of the Task 2A TTS foundation:

- **VoiceProfile schema** stores `voice_id`, display `name`, `type` (`character` or `narrator`), optional `reference_audio_path`, open-ended `metadata`, and compact `mood_settings` (`baseline_expressiveness`, `emotional_sensitivity`, `nsfw_intensity`). The reference path and metadata fields support zero-shot cloning, backend voice aliases, gender/style notes, and other cloning inputs; mood settings keep character-specific speech tuning durable without adding resident models.
- **VoiceManager** owns voice-profile CRUD, JSON persistence, default narrator creation, character-to-voice assignment, assignment clearing, and TTS voice resolution. It writes a compact local JSON store with schema version, profiles, and character assignments, keeping the system inspectable and easy to migrate later.
- **Default narrator startup behavior** ensures Reverie creates a configured narrator voice profile when no narrator exists, so first-run TTS has a stable local fallback. The profile maps to the existing backend default voice through metadata rather than forcing every backend to understand profile records.
- **TTS integration** resolves requested `voice_id`s through VoiceManager, can resolve assigned `character_id` voices, and passes the concrete backend voice key (`metadata.backend_voice_id` when present, otherwise `voice_id`) to Orpheus/Piper while returning the durable profile ID to clients. Unknown explicit profile IDs fail with a stable `voice_profile_not_found` error instead of silently using the wrong character voice.
- **8GB behavior** remains unchanged from Task 2A: profiles are lightweight JSON records, no voice model is loaded at startup, no cloning model is invoked, and Orpheus/Piper lazy loading and fallback continue to guard GPU/CPU pressure.

Short design summary: voice profiles are a durable identity layer, VoiceManager is the local persistence and assignment boundary, and TTSService remains the synthesis workflow that resolves a profile into the backend-specific voice key just before generation. This keeps current TTS simple while leaving clean extension points for future cloning and emotion/prosody routing.

### 3.6 Context-Aware TTS Routing (Milestone 3 Task 2C)

Milestone 3 Task 2C layers smart, lightweight routing on top of the Task 2A/2B TTS and voice-profile foundation:

- **TTSContext schema** now carries `character_id`, `is_narration`, `mode` (`one_to_one` or `rpg`), `emotion_hint`, `intensity`, resolved `mood_settings`, and optional `scene_tags`. Emotion fields feed deterministic tag selection and intensity scoring while staying lightweight and inspectable.
- **TTS API context support** extends `POST /api/tts/generate` with a full `context` object while keeping legacy top-level `voice_id` and `character_id` clients working. Explicit `voice_id` remains an override; otherwise context drives narrator versus character routing.
- **TTSContextRouter** owns routing policy outside the route and backend adapters. It uses explicit narration flags first, then simple one-to-one/RPG heuristics: one-to-one character context routes to the assigned character voice, RPG context treats quoted lines or matching speaker prefixes as character speech, and narration falls back to the default narrator profile. The resolved context is enriched with the selected VoiceProfile mood settings before chat/TTS emotion tagging runs.
- **Voice resolution** still goes through VoiceManager, so assigned character profiles, durable narrator fallback, backend voice aliases, and stable `voice_profile_not_found` errors remain centralized and inspectable. TTSService now consumes the router decision and sends only the concrete backend voice key to Orpheus/Piper.
- **Chat integration hooks** allow chat/VN callers to pass `tts_context` alongside chat requests and receive it back in non-streaming responses or final SSE `done` metadata. This gives the frontend a clean bridge from current chat/VN state to TTS playback without forcing synthesis into the chat response path.
- **8GB behavior** remains unchanged: routing is pure Python/Pydantic logic, no additional model is loaded, no heavy NLP classifier runs, and TTS backends remain lazy with Piper CPU fallback.

Short design summary: TTSContext describes the current speaker/narrator situation, TTSContextRouter resolves that context into a durable voice profile through VoiceManager, and TTSService remains the synthesis boundary. This keeps 1:1 chats natural, makes RPG/multi-character scenes predictable, and gives Task 2D a stable voice-routing base for emotion/prosody shaping.


### 3.7 Emotion & Prosody System (Milestone 3 Task 2D)

Milestone 3 Task 2D adds rich emotional voice enhancement without adding an LLM call to the normal chat path:

- **EmotionEngine** is a deterministic, 8GB-friendly service that analyzes `TTSContext`, per-character mood settings, current scene tags, recent non-system chat messages, retrieved memory context, selected reflection journal entries, and growth notifications. It detects high-emotion and intimate/NSFW scenes with bounded keyword scoring, honors `emotion_hint` and `intensity`, and produces Orpheus-compatible speech tags such as `<whisper>`, `<sigh>`, `<gasp>`, `<moan>`, `<groan>`, and `<laugh>`.
- **Clean-text vs TTS-text flow** is explicit. Chat-visible content is always passed through tag stripping before it reaches non-streaming `ChatResponse.message.content` or streamed SSE `message` token payloads. The chat pipeline separately creates `tts_text`, which may contain speech-only Orpheus tags, and exposes it only as TTS metadata for later playback. Emotion tags must never be rendered in chat bubbles.
- **SSE `done` voice metadata** now carries the final clean `text`, separate `tts_text`, full resolved `tts_context`, durable `voice_id`, existing `visual_state` / growth metadata, and deterministic `emotion` metadata (`scene`, `intensity`, tags, high-emotion/intimate flags, and cues). The frontend can render clean text while handing `tts_text` + `tts_context` + `voice_id` to audio generation in Task 2E.
- **TTSService integration** prefers pre-tagged `tts_text` when the chat pipeline provides it. If a direct TTS request only supplies clean `text`, TTSService falls back to on-the-fly EmotionEngine tagging using the provided `TTSContext`, then resolves the actual backend voice through `TTSContextRouter` and VoiceManager before calling Orpheus/Piper.
- **8GB behavior** remains lightweight: no classifier model, no extra LLM call, no new resident GPU model, no synthesis during chat response generation, and no frontend audio player work in this task. Orpheus/Piper still load lazily at TTS time, and Piper remains the CPU-friendly fallback.

Short design summary: visible text is the safe, tag-free chat contract; `tts_text` is the speech-only performance script; `tts_context` plus `voice_id` identify who should speak; and `emotion` metadata explains why tags were chosen. This preserves immersion for high-intensity and adult scenes while keeping user-visible chat clean and local-first performance predictable.


### 3.8 Frontend TTS Playback Integration (Milestone 3 Task 2E)

Milestone 3 Task 2E connects the existing Orpheus/Piper backend foundation to the Svelte/Tauri companion UI without moving speech synthesis into the chat streaming path:

- **`ttsStore` frontend architecture** is a Svelte 5 runes store that owns the bounded audio queue, current voice line, playback state, progress, announcements, and cancel/stop/pause/play controls. It generates at most one audio asset at a time, keeps only a tiny queue, revokes blob URLs after use, and cancels active speech when the user sends a new message so 8GB systems avoid audio buildup.
- **Audio generation contract** uses final SSE `done` metadata: chat renders clean text, while playback sends `tts_text` plus resolved `voice_id`, `tts_context`, and `emotion` metadata to `POST /api/tts/generate`. If metadata is absent, the frontend gracefully falls back to the visible assistant text and default backend voice resolution.
- **Reusable `AudioPlayer` component** provides a warm compact playback surface with speaking animation, current voice label, progress, play/pause/stop controls, auto-play toggle, and ARIA live announcements. It is reusable across chat and Visual Novel mode and does not preload historical messages.
- **Chat integration** adds per-assistant-message voice playback and automatic playback for completed assistant responses when TTS and auto-play are enabled. New user messages interrupt prior speech to keep conversation flow responsive and avoid overlapping local TTS jobs.
- **Visual Novel integration** reuses the same audio player inside the VN dialogue panel and applies a lightweight speaking visual cue to the character layer while speech is preparing or playing, so expression/pose metadata and voice playback feel synchronized without adding heavier animation systems.
- **Settings** expose local voice controls: enable/disable TTS, auto-play, volume, playback speed, quality/balanced/speed preference, zero-shot cloning setup, and per-profile mood sliders for baseline expressiveness, emotional sensitivity, and NSFW intensity. These settings are local-only and designed for graceful fallback when TTS is disabled or unavailable.

Short design summary: Task 2E keeps chat generation, visual state, and speech playback decoupled. The backend enriches final response metadata; the frontend stores that metadata on the assistant message; `ttsStore` decides whether to synthesize and play exactly one interruptible line; and chat/VN mode both consume the same lightweight playback surface.

### 3.9 Per-Character Mood & Final TTS Polish (Milestone 3 Task 2G)

Milestone 3 Task 2G completes the current Task 2 TTS arc with per-character fine-tuning and polish:

- **Per-character mood controls** are durable `VoiceProfile.mood_settings` fields, editable from the warm dark voice settings UI. Baseline expressiveness shapes default prosody, emotional sensitivity controls how quickly high-emotion cues boost intensity, and NSFW intensity controls how strongly intimate/adult scene cues affect speech. Values are compact 0.0-2.0 scalars so they remain inspectable and 8GB-friendly.
- **Resolved mood propagation** flows through VoiceManager and TTSContextRouter into `TTSContext`, then into EmotionEngine and frontend `ttsStore` playback requests. Chat `done` metadata and non-streaming responses keep clean visible text separate from `tts_text` while carrying the same mood-enriched context for chat, streaming, VN mode, and cloned voices.
- **Improved scene/intensity detection** now combines mood settings with scene tags, retrieved memory context, recent messages, reflection summaries, and growth cues. High-emotion milestones, vulnerable repairs, intimate scenes, aftercare, desire, and NSFW cues receive stronger deterministic boosts while user/profile preferences can soften or intensify the final tags.
- **Final polish** improves TTS settings discoverability, keeps zero-shot cloned voices in the same profile/mood workflow, and adds clearer AudioPlayer fallback/error copy plus a dismiss action. TTS failures do not break chat, VN rendering, clean-text display, voice cloning metadata, or the streaming buffer-health path.
- **8GB behavior** remains unchanged in principle: no additional classifier model, no extra LLM calls, no resident voice model until synthesis, bounded frontend queues, lazy Orpheus loading, Piper CPU fallback, and tiny JSON profile metadata for tuning.

Task 2A-2G summary: Reverie now has a local-first TTS architecture with Orpheus quality speech, Piper fallback, durable voice profiles and zero-shot clone references, context-aware speaker/narrator routing, deterministic emotion/prosody tagging, clean text vs. `tts_text` separation, streaming playback with buffer health, shared chat/VN AudioPlayer integration, per-character mood controls, and user-trust-focused fallback UX.

### 3.10 Final TTS Cleanup & Polish (Milestone 3 Task 2H)

Milestone 3 Task 2H closes the Task 2 TTS system as a complete lightweight voice layer:

- **Canonical request preparation** now lives behind one TTSService path for both normal and streaming synthesis, so visible-text cleaning, `tts_text` selection, context-aware routing, voice-profile resolution, deterministic tag injection, and configured text-length validation stay consistent. Overlong voice lines return stable `tts_text_too_long` details while chat text remains untouched.
- **Rapid-message behavior** stays natural by keeping the frontend voice queue bounded, interrupting active speech on new auto-play responses, de-duplicating queued playback for the same message, and softly clipping very long replies before local synthesis so the UI stays responsive on 8GB systems.
- **AudioPlayer polish** adds a shared voice presence state (`ready`, `queued`, `preparing`, `speaking`, `paused`, `error`), clearer backend/fallback/error copy, loading and stream-smoothing feedback, dismissible errors, and warm active styling without changing the underlying streaming/buffer-health architecture.
- **Chat and VN feedback** now show subtle active-voice cues in the chat status pill, assistant message bubble, VN character layer, and VN dialogue panel. These cues remain CSS-only, respect the existing reduced-motion guards, and do not add any resident model or animation dependency.
- **Voice settings integration** keeps clone setup and per-profile mood tuning in one local workflow: clone references remain lightweight local files, mood sliders explain what each scalar affects, and Piper fallback remains explicit for low-VRAM or unavailable-Orpheus paths.
- **8GB robustness** remains preserved: no classifier model, no extra LLM pass, no startup voice model load, Orpheus still lazy-loads with VRAM guardrails, Piper remains the CPU fallback, streaming falls back to bounded WAV chunks, and frontend playback state is compact.

**Task 2A–2H is complete.** Reverie’s final MVP TTS architecture is local-first, emotionally tagged, clean-text-safe, profile-aware, clone-ready, interruptible, fallback-safe, and polished across Chat, Settings, and Visual Novel mode while staying friendly to RTX 4070 8GB mobile hardware.

### 3.11 Growth Dashboard Architecture (Milestone 3 Task 4A)

Milestone 3 Task 4A adds the central Growth Dashboard as Reverie's warm relationship overview, without creating new heavy backend work on page load:

- **Navigation**: the Svelte shell now includes a first-class `Growth` destination between Chat and Journal, separate from the detailed Journal reader and Personal LoRA Training review panel. Growth is the emotional summary view; Journal remains the evidence/detail view; Training remains the consent/action view.
- **Data sources**: the dashboard reads only existing local self-learning systems through `journalStore` and `growthStore`: recent reflection journal entries, insight kinds/themes/confidence, structured growth hypotheses/interpretations, Personal LoRA review counts, explicit opt-in settings, and current local training job metadata. It does not scan memories, start reflection, start training, or run model inference.
- **Relationship model**: affection, trust, interest, and emotional bond cards are lightweight derived UI signals calculated from reflection themes and insight evidence. These meters are framed as relationship pulse indicators, not canonical hidden state, so weak or missing evidence stays conservative and future backend growth-state schemas can replace the derivation cleanly.
- **Living timeline**: recent journal entries become a human-readable evolution timeline focused on tone, attraction/interest, emotional bonds, trust, reassurance, playfulness, boundaries, and continuity. Copy intentionally uses intimate product language while preserving provenance through confidence and theme labels.
- **LoRA status summary**: the dashboard surfaces current progress, last trained time, next scheduled/readiness state, pending-review count, and running/failed/idle status from the existing Personal LoRA foundation only. Starting jobs, reviewing examples, and adapter management remain in the Training panel for later tasks.
- **8GB behavior**: page load performs bounded API reads already used by Journal/Training, then computes small arrays/maps in Svelte. There are no model loads, embeddings, background queues, image/TTS calls, broad filesystem scans, or long lists rendered on entry.
- **UI language**: the visual design extends the warm premium dark system with rose accents, subtle relationship glow, compact cards, calm breathing spacing, accessible empty/error states, reduced-motion-compatible CSS, and a clear distinction between emotional overview and advanced controls.

Task 4A establishes the emotional command center for self-learning: users can see how the character's feelings, tone, and behavior are evolving from local evidence, while detailed editing/review/rollback workflows remain reserved for Journal, Memory, Training, and later Growth-control tasks.


### 3.12 Diary-Style Self-Reflection Journal (Milestone 3 Task 4B)

Milestone 3 Task 4B turns the Journal destination into Reverie's intimate diary reader while keeping it tied to the transparent growth system:

- **Navigation and purpose**: `Journal` remains a first-class sidebar destination beside Growth and Training. Growth summarizes how the relationship is changing; Journal shows the dated reflection pages and evidence details behind that visibility; Training remains the explicit consent/action area for Personal LoRA artifacts.
- **Diary presentation**: entries are shown as a chronological reflection timeline with warm dark parchment cards, rose accents, paper-texture overlays, emotional first-person summaries, and a quiet modal reading mode. The prose is presentation-only; structured facts, insights, confidence, privacy tags, and promotion metadata remain visible for trust.
- **Search and filters**: the Journal view supports lightweight local filtering by keyword, theme, character metadata, pinned/favorite pages, growth-linked entries, and needs-review entries. Filtering uses already-loaded bounded journal entries and does not start embeddings, inference, filesystem scans, or memory-browser work.
- **Pins/favorites**: users can pin important entries locally in the UI to keep meaningful emotional milestones easy to revisit without changing backend memory state or treating a pin as training consent.
- **Manual reflection**: the Journal includes a `New reflection` action that sends a bounded recent chat window to `POST /journal/reflect`, creating a local journal entry through `ReflectionManager` before any memory promotion side effects. Empty conversations are rejected in the UI with warm copy.
- **Growth integration**: each page exposes whether it stayed journal-only, linked/promoted to memory, or needs training review. Growth hypotheses and promoted-memory status are surfaced in the reader so the Growth Dashboard's relationship overview can be traced back to specific journal pages.
- **Privacy and scope**: the feature is still not a full editable memory browser, rollback console, or LoRA training UI. It keeps the MVP promise of local-first transparency while leaving deeper review/edit/delete/branching controls for later Memory, Training, and Growth-control tasks.

Task 4B makes self-learning feel emotionally alive instead of administrative: users can read what the character believes she learned, search and pin important moments, manually ask for a reflection, and understand how those pages feed growth visibility without surrendering control.

### 3.13 Editable Memory Browser (Milestone 3 Task 4C)

Milestone 3 Task 4C adds the dedicated Memory destination as the control surface for long-term recall, directly complementing the Growth Dashboard and Diary Journal:

- **Navigation and purpose**: `Memory` is now a first-class sidebar destination. Growth remains the emotional overview, Journal remains the reflective evidence reader, Training remains the explicit consent/action area, and Memory is the inspect/edit/delete surface for recall artifacts that can influence continuity.
- **Backend control contract**: the backend exposes paginated `/memory/memories` browser APIs over the existing local LanceDB-backed `MemoryManager`, with predictable keyword/metadata/date filtering, detail lookup, inline update, individual hard delete, and bulk delete/prune operations. Deleted memories are removed from the retrieval table rather than hidden only in UI.
- **Editable memory model**: users can edit memory text, tags, importance, and review metadata. Updating text re-embeds the memory through the existing local embedding path so retrieval stays consistent with the revised content, while provenance fields such as source, journal linkage, rollback id, timestamps, confidence, themes, and character metadata remain visible.
- **Search and scale behavior**: browser search supports keyword, character, theme, source, and date filters without firing semantic embedding calls for each UI query. Results are paginated with small page sizes so large local libraries remain responsive and 8GB-friendly.
- **Deletion and pruning UX**: the UI includes clear destructive styling, modal warnings for individual deletion, selected-memory bulk deletion, and date-based pruning for old memories. These controls are intentionally separate from Journal pins and Training approval so deletion, visibility, and training consent do not get conflated.
- **Warm premium presentation**: the Memory Browser uses a card-based warm dark layout, top filters/search, selected-memory preview, detailed modal editor, provenance panel, tag chips, and visible importance/confidence/relevance signals. Raw metadata is tucked into an advanced section for auditability without overwhelming normal users.
- **Growth visibility tie-in**: the Memory page closes the transparency loop introduced by Tasks 4A and 4B. A user can see an emotional trend on Growth, trace it back to Journal evidence, then open Memory to inspect, correct, tag, reprioritize, or delete the exact long-term memories that may shape future recall.

Task 4C makes Reverie's self-learning controllable instead of mysterious: durable memories are searchable, provenance-rich, editable, and removable while staying local-first and lightweight.

### 3.14 Character Encyclopedia / Life Summary (Milestone 3 Task 4E)

Milestone 3 Task 4E completes the first Growth-system arc with a Character Encyclopedia: a warm, searchable character bible for the active companion that summarizes who she is becoming without creating a new hidden state store.

- **Navigation and purpose**: `Encyclopedia` is now a first-class sidebar destination. Growth remains the emotional dashboard, Journal remains the evidence diary, Memory remains the correction/deletion control surface, Training remains the explicit LoRA consent area, and Encyclopedia is the readable life-summary view that brings those sources together.
- **Data sources**: the page derives its profile from already-bounded frontend sources: recent journal entries, current memory page results, approved/recent Personal LoRA examples, and optional character voice profiles. It does not invoke model inference, run embeddings, scan the filesystem, or start training. Missing backend sources degrade gracefully into empty-state copy.
- **Profile contents**: the page organizes relationship summary, affection/trust/attraction meters, how the character sees important people, living situation and daily routines, likes/dislikes/hobbies/personality quirks, key memories, evolution over time, current mood, and recent growth highlights. Evidence is summarized through lightweight heuristics and source metadata until a future canonical growth-state API replaces those derivations.
- **Living design**: the UI uses the same warm premium dark language as Growth and Journal: rose glow, portrait card, relationship meters, collapsible profile sections, soft notices, searchable notes, timeline dots, readable typography, and responsive layouts.
- **8GB behavior**: all work is local array filtering, keyword counting, date sorting, and rendering short lists. The page intentionally stays fast on the RTX 4070 8GB target and keeps training, reflection, embedding, TTS, and image work outside the load path.

Task 4E completes the merged Task 4 Growth suite by making self-learning legible from four angles: Growth shows emotional trajectory, Journal shows reflective reasoning, Memory exposes durable recall controls, Training governs LoRA consent, and Encyclopedia turns the accumulated evidence into a beautiful living character profile.

### 3.15 Futa-Vision Integration Vision (Future)
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
- ✅ Milestone 3 image generation system complete: queued local generation, prompt context, chat/VN display, persistent gallery, and user controls.
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

## Milestone 3 Task 2F Update — Streaming TTS + Voice Cloning Foundation

Reverie now supports a stronger local voice pipeline on top of the Task 2A-2E TTS foundation:

- **Near-instant streaming TTS contract**: the backend exposes newline-delimited streaming events for TTS requests. Orpheus is attempted through true chunk-yielding APIs when the installed adapter supports them, and the app gracefully falls back to bounded full-file WAV generation when true streaming is unavailable.
- **Progressive frontend playback**: the Svelte TTS store can receive audio chunks, schedule PCM chunks through Web Audio for responsive “Speaking...” playback, and fall back to buffered WAV playback without changing the user-facing controls.
- **Zero-shot voice cloning UI**: voice settings include a warm dark “Clone Voice” section where users can record or upload a short 6-15 second reference, preview it, and create a local voice profile.
- **VoiceManager cloning integration**: reference audio is stored locally under the voice data directory, profiles are marked as Orpheus zero-shot ready, and optional character assignment metadata is persisted without preloading or training any large model.
- **8GB-friendly behavior**: cloning setup only stores a small reference clip and metadata; Orpheus remains lazy-loaded, Piper remains the fallback, and streaming failures degrade back to full generation instead of keeping extra heavyweight models resident.
- **Streaming V2 polish**: frontend playback now pre-buffers roughly 0.7 seconds of PCM before starting, tracks buffer health during playback, and inserts a gentle rebuffer delay when chunks arrive too slowly so voices avoid harsh stutter while still playing progressively. The backend streaming response uses no-transform/no-buffer headers and a compact NDJSON event helper for robust chunk/error delivery.
- **Local data hygiene**: default root-level runtime data such as cloned reference audio is ignored by git so private voice clips and generated local stores stay out of source control.

Task 2G delivered advanced mood sliders; Task 2H completed final cleanup, active voice feedback, and robustness polish for the Task 2 TTS arc.

---


## Milestone 3 Task 3A Update — Image Generation Backend Foundation + VRAM Safety

Reverie now has a local-first backend foundation for in-chat image generation that is intentionally queued, low-priority, and safe for RTX 4070 8GB laptop systems:

- **ImageGenerationService**: `backend/app/services/image_generation_service.py` owns the media workflow. It queues jobs, emits ordered lifecycle/progress events, supports cancellation, and isolates ComfyUI/Flux GGUF details behind a small adapter so chat and TTS routes never perform heavyweight media work inline. A compatibility import remains at `backend/services/image_generation_service.py`.
- **ComfyUI + Flux GGUF lowvram contract**: jobs target ComfyUI running locally with Flux GGUF Q4/Q5-style lowvram workflows, batch size 1, conservative resolution/step presets, model/offload metadata, and no diffusion model loaded inside the Reverie FastAPI process.
- **8GB quality presets**: `preview_8gb`, `balanced_8gb`, and `high_8gb` define bounded dimensions, steps, guidance, and minimum-free-VRAM budgets. The service automatically degrades to a lower preset when current VRAM cannot safely satisfy the requested tier.
- **TTS priority and automatic pause/resume**: `LocalResourceCoordinator` exposes process-wide TTS activity and VRAM snapshots. Orpheus/Piper synthesis enters a priority section; image jobs pause before starting when TTS is active, resume after TTS finishes, and can ask ComfyUI to interrupt/retry if TTS begins during an active image attempt. TTS always wins over image generation.
- **VRAM-aware queueing**: every image job checks live VRAM through `torch.cuda.mem_get_info()` when available, then `nvidia-smi`, before starting. If VRAM telemetry is unavailable, the service uses the preview preset by default rather than assuming the GPU is safe.
- **API foundation**: `POST /api/images/generate` queues a job from `prompt`, optional `negative_prompt`, compact `context`, and `quality_preset`; `GET /api/images/{job_id}/events` streams SSE progress; `GET /api/images/{job_id}` returns current state; and `POST /api/images/{job_id}/cancel` cancels queued/running work.
- **Graceful degradation**: the backend reports calm, typed local-resource errors, logs fallback/resource decisions without dumping private prompt content, retries once at preview quality after OOM-like failures, and can pass CPU-fallback intent to the ComfyUI workflow metadata when enabled.

Task 3A deliberately did **not** add frontend image display. Later tasks can build gallery/chat presentation on top of this safe queue/event contract.

---

## Milestone 3 Task 3B Update — Basic Context-Aware Prompt Engine

Task 3B adds deterministic prompt engineering on top of the safe Task 3A image queue:

- **ImagePromptEngine**: `backend/app/services/image_prompt_engine.py` builds bounded positive and negative prompt text without extra LLM calls. It accepts a simple user prompt plus optional context and composes character continuity, VN scene state, recent chat intent, memory tags, reflection themes, growth cues, and mood controls into one prompt-friendly description. A compatibility import remains at `backend/services/image_prompt_engine.py`.
- **Character and style consistency**: when character card or voice-profile metadata is present, the engine preserves name, appearance, outfit/clothing, mood, personality, voice/profile tone, visual style tags, and canonical identifying details so generated images remain recognizably the same character across jobs.
- **Chat/VN/memory context use**: the engine reads `visual_state` / scene / background for current staging, recent chat messages for the latest user action and who should appear, `memory_tags` or compact memory summaries for continuity, `reflection_themes` for emotional subtext, `growth_cues` for relationship evolution, and per-character mood settings for expressiveness/intimacy hints. These inputs are treated as evidence and compressed; no durable memory is created by image generation.
- **NSFW-aware framing**: intimate scenes involving both the user and character keep the character emotionally readable while adding deterministic framing instructions to include only the user's body as needed and avoid showing the user's face through over-shoulder, back-view, cropped, or implied-POV composition. The negative prompt also discourages visible/detailed user faces in those scenes.
- **Negative prompts and ComfyUI contract**: `/api/images/generate` can now accept `negative_prompt`; ImageGenerationService merges it with Reverie's default quality/anatomy/style negatives, stores the engineered prompt on the job, and passes both `text` and `negative_text` to the ComfyUI workflow metadata.
- **8GB behavior**: prompt construction is pure Python string/rule processing, deterministic, bounded, and performed before the queued ComfyUI job starts. It does not load models, allocate GPU memory, or block chat/TTS beyond normal request validation.

---

## Milestone 3 Task 3C Update — Frontend Image Generation Integration & Display

Task 3C connects the existing Task 3A/3B image backend to the Svelte/Tauri frontend without turning image generation into a blocking chat or voice path:

- **Typed frontend image API boundary**: `frontend/src/lib/api/imageService.ts` wraps `POST /api/images/generate`, `GET /api/images/{job_id}`, `POST /api/images/{job_id}/cancel`, and the SSE progress stream. Components do not call raw fetch/Tauri APIs directly; the service normalizes backend errors, supports cancellation, and resolves ComfyUI output filenames to displayable preview URLs.
- **Svelte 5 imageGenerationStore**: `frontend/src/lib/stores/imageGenerationStore.svelte.ts` owns image jobs, bounded recent state, announcements, progress updates, cancellation, per-message lookup, VN-scene lookup, and optional consent-based auto-generation. It passes compact chat/VN context into the backend prompt engine while keeping generated images out of durable memory/history for now.
- **TTS/resource awareness in the UI**: the image store reads `ttsStore` presence and labels queued work as paused-for-voice when speech is preparing or playing. This mirrors the backend `LocalResourceCoordinator`: TTS remains priority, image jobs resume automatically, and users see calm VRAM/paused/fallback copy instead of technical queue noise.
- **Chat integration**: chat now offers a global “Generate image” action plus per-message “Generate image” controls. Generated images render inside the relevant bubble as expandable image cards with progress bars, cancel buttons, fallback notes, and error feedback. Chat sending, streaming, and TTS playback remain independent.
- **Visual Novel integration**: VN mode now includes a contextual “Visualize scene” action. Completed scene images appear as a lightweight background enhancement behind the sprite stack, with a dialogue-panel status row for progress/cancel/retry. Authored sprite layers remain the primary fast path; generated art is an optional overlay/reaction enhancement.
- **Consent-based setting**: settings expose an off-by-default “Auto-generate after replies” toggle. Manual generation remains the default behavior so local image work never starts unexpectedly.
- **8GB graceful degradation**: frontend presentation treats queued, waiting, paused, fallback, failed, and cancelled states as normal. It never blocks chat input or speech controls, uses lazy image loading, limits visible job state, and relies on the backend’s preview preset/pause-resume behavior for RTX 4070 8GB safety.

Task 3C intentionally does **not** add image history, gallery management, or advanced generation controls; those remain reserved for Task 3D and later media workflows.

### Task 3C Polish Round

The Task 3C frontend integration was tightened after review:

- **Reusable image job presentation**: chat and VN now share a dedicated image job card component for progress, cancellation, paused-for-voice, low-VRAM waiting, degraded preset, error, retry, and expandable preview states. This keeps later gallery/history work from duplicating status logic.
- **Protected image output serving**: the backend now exposes job-indexed image output URLs. The frontend asks Reverie's API for `/api/images/{job_id}/outputs/{output_index}` instead of constructing arbitrary local or ComfyUI file URLs. The route serves local files only when the requested output index is attached to that job and resolves under the configured image output directory; otherwise it falls back to ComfyUI `/view` for that same attached output when safe.
- **Polished resource feedback**: user-facing copy now distinguishes TTS pause/resume, low-VRAM waiting, unknown VRAM preview fallback, OOM/degraded preset fallback, and normal queued/running states while preserving the backend rule that TTS always has priority over image generation.


## Milestone 3 Task 3D Update — Polish, History & Controls (Task 3 Complete)

Task 3D completes the Milestone 3 image generation system as a polished, local-first media layer that remains subordinate to chat, voice, and 8GB VRAM safety:

- **Persistent per-conversation history**: completed image jobs are now written to `REVERIE_IMAGE_GENERATION_HISTORY_PATH` as compact metadata (`job_id`, `conversation_id`, source message/context identifiers, prompt summary, presets, output references, fallback state, and asset-save state). The history stores metadata and lazy output references only; it does not preload image bytes into chat, memory, or the Svelte store.
- **Gallery architecture**: `GET /api/images/history/{conversation_id}` returns the conversation gallery, and the frontend Images panel renders it as a lazy thumbnail grid with a zoom/lightbox view. Gallery loading is metadata-first and uses protected `/api/images/{job_id}/outputs/{output_index}` URLs, preserving the protected output-serving contract from Task 3C.
- **User controls**: completed images support regenerate, create variation, save to character assets, and delete. Regenerate requeues the same prompt/context; variation appends a bounded instruction to preserve character identity and mood while changing composition/lighting/pose/camera. Delete removes the gallery record without granting arbitrary filesystem access. Save copies an attached local output into the character asset tree and appends a manifest entry with source prompt, preset, label, and save timestamp.
- **Polished display**: chat image cards now include completed-image controls, clearer retry/error copy, lazy previews, and captions based on the prompt summary. Visual Novel mode can regenerate/vary/save/delete the latest scene image while keeping authored sprite layers as the fast default and generated imagery as an optional background enhancement.
- **Settings**: image generation settings now include the off-by-default assistant auto-generation rule plus a default 8GB preset selector (`preview_8gb`, `balanced_8gb`, `high_8gb`). The backend still validates VRAM and can downgrade regardless of frontend preference, so user choice never overrides safety.
- **8GB/TTS priority preserved**: no new resident model is introduced. History/gallery operations are JSON/file metadata work; thumbnails/images lazy-load through the existing output endpoint; generation remains queued at concurrency 1; TTS still pauses/preempts image jobs; and the UI treats low VRAM, paused voice priority, fallback, cancelled, and retryable errors as normal states.

Short design summary: Milestone 3 image generation is now a complete optional local media workflow: deterministic chat/VN prompt context enters the safe queued backend; ComfyUI/Flux GGUF lowvram produces outputs under strict resource coordination; completed results become inspectable per-conversation gallery records; and users can regenerate, vary, save, or delete images without compromising chat responsiveness, voice priority, or local-first privacy. **Task 3 is complete.**


### Task 3D Final Polish Round

The final polish pass keeps the PR #80 gallery/navigation/lightbox integration intact while tightening persistence, asset manifests, and user feedback:

- **History persistence hardening**: image history now writes a schema-versioned JSON payload with both grouped `conversations` and a compatibility `items` list, reloads legacy flat histories, skips malformed entries instead of failing the gallery, and writes JSON atomically through a temporary file replace.
- **Character asset manifest polish**: saving generated images now normalizes the manifest, deduplicates by `job_id` + output index, records relative and absolute asset paths, source conversation/message metadata, prompt/negative prompt, presets, fallback state, and stable `asset_id`s.
- **Clearer fallback UI**: gallery and image cards distinguish missing local output files from generation failures, disable save actions when the file is unavailable, and offer retry/regenerate guidance while preserving lazy loading and TTS/VRAM priority behavior.

## Milestone 3 Task 4A Update — Growth Dashboard

Task 4A adds the Growth Dashboard as the central, polished relationship overview for Reverie's self-learning loop:

- **Frontend architecture**: `GrowthDashboard.svelte` composes existing `journalStore` and `growthStore` data, using Svelte 5 runes to derive relationship pulse, feeling highlight cards, recent evolution timeline, personality shifts, and Personal LoRA status without creating new backend computation.
- **Navigation and scope**: the sidebar now exposes Growth as its own destination. The dashboard intentionally avoids journal editing, memory browsing, and LoRA training controls; those remain separate surfaces to keep this page emotionally readable and lightweight.
- **Design decision**: relationship meters are evidence-backed UI summaries derived from reflection themes/insights, not permanent canonical personality mutations. This preserves drift safety while making character evolution feel visible and personal.
- **8GB decision**: the dashboard does not trigger model calls, embedding work, image generation, TTS, or training. It performs bounded existing API reads and local array aggregation only, matching the RTX 4070 8GB mobile responsiveness target.


## Milestone 3 Task 4C Update — Memory Browser & Editable Controls

Task 4C adds the Memory Browser as Reverie's dedicated long-term recall control center:

- **Sidebar destination**: `Memory` is enabled as a first-class navigation item beside Growth, Journal, Training, Chat, Visual Novel, Images, and Settings.
- **Editable browser UI**: the new Memory page provides keyword/character/theme/source/date filters, paginated card results, a selected-memory preview, and a detailed modal for editing text, tags, and importance.
- **Provenance and scores**: memory details expose learned-from/source metadata, created/updated timestamps, character/type, linked journal and rollback ids, raw advanced metadata, tags, themes, confidence, importance, and retrieval relevance.
- **Delete/prune controls**: users can delete one memory after an explicit warning, bulk delete selected cards, or prune memories older than a chosen date.
- **Backend integration**: FastAPI memory routes now wrap the existing local `MemoryManager`/LanceDB system for list/detail/update/delete/bulk-delete operations. UI keyword filtering is low-cost and paginated; text edits re-embed through the existing local memory pipeline.
- **Growth transparency**: Growth shows relationship trends, Journal shows reflection evidence, and Memory now lets users correct or remove the durable recall artifacts behind future continuity.

Task 4C deliberately avoids LoRA training UI and encyclopedia work. It focuses on local memory inspection/control and keeps memory browsing lightweight for the 8GB target.


### Milestone 3 Task 4D — Automated LoRA Training & Approvals

Reverie's growth system now supports optional automated Personal LoRA training as an auditable extension of Reflection → Journal → Memory → Growth Dashboard. Training remains local-first and opt-in: collection, training, automation, and adapter application each have visible settings. Automated training is allowed only after approved growth data crosses configurable thresholds such as minimum approved examples, new examples since the last completed job, linked memory volume, training frequency hours, and max auto jobs per day. The default behavior is non-intrusive: automation is off until enabled, training requires explicit opt-in, and new adapters require approval before application.

The 8GB-friendly training profile is conservative by design: Unsloth-style 4-bit QLoRA foundation, rank capped at 16, batch size 1, bounded sequence length, low learning rate, serialized background execution, and no hidden chat-path training. Current implementation writes inspectable dataset/job/adapter manifests and can be swapped for a real Unsloth worker while preserving the same safety controls.

The Growth Dashboard surfaces a LoRA Training Status section with current status, last trained time, next scheduled training, data that triggered training, and plain-language learning feedback such as improved reassurance tone, stronger emotional memory recall, better boundary pacing, or more stable playful voice. When “Require approval before applying new LoRA updates” is enabled, completed adapters remain pending with approve/reject controls and are not activated until approved.

### Milestone 3 Task 4E — Character Encyclopedia / Life Summary

Task 4E adds the Character Encyclopedia / Life Summary as the polished reading surface for the active character's lived continuity. The sidebar exposes `Encyclopedia`, and the Svelte shell supports `#encyclopedia` deep-linking so the page is easy to revisit directly.

The implementation composes existing local evidence rather than creating another backend authority: `journalStore` supplies reflection summaries, themes, structured facts, emotional valence/intensity, and growth hypotheses; `memoryStore` supplies editable long-term memory snippets and metadata; `growthStore` supplies approved/recent Personal LoRA examples; and `voiceService` optionally contributes character voice-profile context. The page gracefully renders from partial data when any local source is unavailable.

The design is intentionally warm and readable: a hero summary, active-character portrait card, affection/trust/attraction relationship meters, current mood card, searchable profile notes, collapsible sections for relationship/social/daily-life/traits/memory/evolution/mood, and a recent timeline of journal, memory, and growth anchors. Computation stays lightweight with bounded source lists, keyword/theme heuristics, small maps, and local filtering only.

With 4E complete, Milestone 3 Task 4 now forms a coherent transparent-growth suite: Dashboard for overview, Journal for introspection, Memory Browser for control, Training for automated LoRA approval, and Encyclopedia for a beautiful living character bible.


### Milestone 3 Task 5A — UI/UX Consistency & Polish

Task 5A completes a senior UI/UX consistency pass across the current Milestone 3 application surfaces. The polish layer standardizes Reverie's warm premium dark aesthetic with shared focus rings, selection colors, glass-panel motion, hover/press transitions, empty-state framing, dialog entrances, and responsive control behavior across Chat, Visual Novel, Growth Dashboard, Journal, Memory Browser, Training, Settings, TTS playback, Image Gallery, and Encyclopedia. Motion is intentionally subtle and is globally neutralized for `prefers-reduced-motion` users.

Accessibility decisions are now part of the core UI contract: the app shell includes a skip link and labeled main workspace, chat history behaves as a polite live log, message bubbles carry readable sender/time labels, the composer exposes keyboard hints and local-draft feedback, TTS progress is announced as a real progressbar, and memory editing supports Escape-to-close dialog behavior with labeled controls. These changes preserve local-first privacy language while making interactive feedback more consistent and keyboard/screen-reader friendly.

8GB and performance decisions remain conservative: Task 5A is CSS/Svelte UI polish only. It adds no resident models, no new dependencies, no background workers, no extra backend calls, and no unbounded rendering paths. Animations are transform/opacity based, short-lived, and reduced-motion aware so chat, voice, image jobs, and growth surfaces remain responsive on the RTX 4070 8GB mobile target. **Task 5A is complete.**


### Milestone 3 Task 5B — Performance, Reliability & 8GB Optimization

Task 5B completes a senior performance and reliability pass across Reverie's current Milestone 3 application surfaces. The optimization layer formalizes a shared local resource coordinator with proactive VRAM pressure states (`normal`, `elevated`, `critical`, `unknown`), a `/api/resources/status` diagnostic endpoint, and user-facing 8GB guardrail messaging. TTS remains the highest-priority interactive media path: image generation pauses while TTS is active, can be preempted mid-job if TTS starts, and now asks idle auxiliary models such as Orpheus to unload before exclusive ComfyUI work starts.

The image-generation queue now carries resource pressure and warning metadata through API reads and SSE events, downgrades toward the preview 8GB preset under critical VRAM pressure, interrupts ComfyUI when resource pressure becomes unsafe, caps gallery hydration on the frontend, and keeps ComfyUI/Flux GGUF work serialized as a single exclusive media job. The Svelte shell now shows calm proactive VRAM warnings, wraps major panels in a recovery boundary so one UI failure does not take down the whole app, and preserves safe fallbacks for missing telemetry, missing ComfyUI, and low-resource states.

Settings now includes an explicit 8GB resource mode with clear presets (`8GB Safe`, `Balanced`, `Quality`), background task limits, and a toggle for proactive resource warnings. The default remains conservative for RTX 4070-class 8GB laptops: preview image quality, gentle/balanced context, TTS responsiveness, one non-interactive background task, and automatic explanations when Reverie downgrades or pauses work to avoid OOM. **Task 5B is complete.**


### Milestone 3 Task 5C — Extensibility Foundations

Task 5C establishes Reverie's senior extensibility architecture without adding heavy plugin runtimes or resident model overhead. The backend now exposes a declarative `extension.v1` contract for custom panels, commands, settings sections, TTS voices, image workflows, growth modifiers, character import helpers, VN state, and memory access capabilities. Manifests are loaded from small local JSON files, invalid manifests are skipped with structured errors, and the built-in `reverie.core` contract is always available so future features can build against a stable API instead of ad hoc integrations.

The extension event/command bus is typed, scoped, and bounded. Commands must be declared by an enabled extension with the required capabilities before they are accepted, and all event payloads are size-limited before they enter recent history. This keeps a bad extension from crashing or coupling tightly to chat, VN, TTS, image generation, growth, memory, or settings internals while preserving a clear path for richer plugin runtimes later.

Character import has been upgraded from basic card-field handling toward a full preview normalization layer for SillyTavern and character-card payloads. Import previews now extract lorebooks/world-info into stable lore entries with triggers, priorities, facts, and limits; collect avatar/sprite/background/reference assets; preserve voice profile hints; surface mood and growth preferences; capture image-generation style references; preserve unknown compatible metadata for future round-trip support; and return warnings for missing review-critical data before any durable character state is written.

The Svelte frontend now has matching typed extension contracts, a lightweight local event bus with listener error isolation, an extension registry, an extension API client, and an extensible Settings page. Extensions can register declarative setting sections and fields that render inside Settings while persisting under versioned local storage separately from core settings. The default UI loads backend contracts when Settings opens, reports failures calmly, and keeps all extension diagnostics local.

Documentation for future extension developers now lives under `docs/extensions/README.md`, including the `extension.v1` manifest format, capability guidance, an example settings/command manifest, error-isolation rules, and the character-import preview contract. Runtime overhead remains minimal: the foundation uses Pydantic/TypeScript schemas, bounded in-memory event history, local JSON manifest reads, and no additional frontend or backend dependencies. **Task 5C is complete.**


### Milestone 3 Task 5D — Settings & Control Hub

Task 5D upgrades Settings from a focused memory/reflection panel into Reverie's unified Settings & Control Hub. The frontend now organizes core controls into searchable, keyboard-friendly sections for General, Appearance, TTS & Voice, Image Generation, Growth & Self-Learning, Memory, Extensibility, Performance & 8GB, and Import/Export/Backup. The hub preserves the warm premium dark design language while adding a persistent section rail, clear hierarchy, calm local-save status, and accessible form/radiogroup semantics.

The settings architecture remains lightweight and local-first: core preferences live in the typed `settingsStore`, are normalized on load, and persist in the existing versioned local storage payload with backward-compatible defaults. Appearance density/theme preferences, memory pruning posture, TTS latency/volume/speed, image defaults, growth/reflection controls, and 8GB performance presets all use explicit typed setters so future backend sync can attach without scraping component state.

Control Hub previews explain impact before users opt into heavier behavior. TTS exposes a live sample summary plus per-voice mood sliders and zero-shot voice profile creation; image presets show an 8GB-aware preview and remind users that backend VRAM checks can still downgrade ComfyUI work; performance controls explain TTS priority, serialized image jobs, background task limits, and proactive VRAM warnings. This keeps the RTX 4070 8GB mobile promise visible at the exact point of configuration.

Extensibility from Task 5C is now treated as a first-class hub section. Extension manifests can register declarative setting sections and fields that render beside core settings, while values remain isolated under extension-scoped local storage and extension errors are shown calmly without crashing the hub.

Import/export/reset controls are centralized. Users can export character-facing local keys, growth/journal/reflection/memory/training-facing local keys, settings-only payloads, or a full `reverie.*` local backup; backups can be imported with confirmation; and reset-to-defaults requires confirmation before clearing core and extension hub settings. **Task 5D is complete.**

Task 5D quick polish keeps the PR #98 hub structure while tightening responsive behavior and data-portability UX: the section rail now reports search matches, clears searches directly, provides an explicit no-results state, and becomes a horizontal snap navigation surface on tablet/mobile widths. Backup exports now include stable backup metadata, sorted local-storage keys, safer downloadable filenames, delayed object URL cleanup, clearer import validation, detailed confirmation copy, import-cancel feedback, and a typed reset phrase before destructive default restoration.

*End of Source of Truth Document v1.0*
