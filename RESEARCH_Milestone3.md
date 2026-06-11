# RESEARCH: Milestone 3 - Immersion, Voice, Growth Visibility & Image Integration
**Date**: June 11, 2026  
**Context**: Pre-Milestone 3 research for Reverie (local-first NSFW companion). Focus on 8GB RTX 4070 mobile floor, full custom backend (Python FastAPI + Tauri/Svelte frontend), future Futa-Vision integration, and "truly alive" characters via self-learning/memory.

This document consolidates targeted research. Key decisions are highlighted for use in DEVELOPMENT_PLAN.md, Reverie_Source_of_Truth.md, and GLOBAL_CODING_PROMPT.md.

## 1. Local LoRA Training Practices for 8GB GPUs (Unsloth vs Axolotl, Rank, Roleplay Dataset)

**Winner for our constraints (single 8GB mobile GPU)**: **Unsloth**
- 2x faster training + ~70% less VRAM than Axolotl on consumer hardware.
- Excellent for 7-9B models (our Qwen3.5-9B baseline) with QLoRA 4-bit.
- Axolotl is more feature-rich/flexible for multi-GPU or complex pipelines but heavier; has adopted some Unsloth-inspired optimizations. Use Unsloth for personal/character LoRAs; evaluate Axolotl later for global model training if needed.
- Cross-compatibility: LoRAs trained in one often load in the other.

**Optimal Rank (r)**:
- Sweet spot: **16–32** for roleplay/character growth.
  - r=8–16: Fast, low VRAM, good for simple adaptations or limited data.
  - r=16–32: Best balance of capacity vs memory/speed for personality consistency, emotional depth, niche (futa/slime physics) learning.
  - r=64+: Higher quality on complex tasks but more VRAM/slower — use sparingly or on Pro tier.
- Alpha typically 2x rank (or tuned).
- QLoRA 4-bit is mandatory for 8GB comfort.

**Dataset Curation for Roleplay (High-Signal Growth Data)**:
- Ideal size: 500–5,000+ high-quality examples (more is better but quality > quantity).
- Sources for our self-learning loop:
  - High-rated chat segments (user thumbs-up or auto-scored consistency/engagement).
  - Example dialogues from character cards.
  - Self-Distillation/Reflection outputs (character insights on behavior/preferences).
  - Journal entries + memory events (relationship milestones, kink evolution).
  - Physics/slime/futa-specific interactions for niche LoRAs.
- Curation best practices:
  - Clean, diverse, consistent personality demonstrations.
  - Structured format (instruction/response pairs or chat logs with context).
  - 1–3 epochs (1 for noisy/large sets; 3 for curated high-quality).
  - Use tools like Unsloth's dataset prep or custom scripts to filter by quality score from memory layer.
- Training schedule: Background/nightly on idle GPU, low learning rate, gradient checkpointing.

**Recommendation for Reverie**:
- Primary: Unsloth (FastLanguageModel + QLoRA) in Python backend.
- Personal LoRA per character (rank 16–32) for "grows with you" feeling.
- Global model improvement: Aggregate anonymized high-quality data → periodic Unsloth/Axolotl runs for base model updates (Free/Premium/Pro tiers).
- Add to self-learning loop: Auto-curate from Reflection/Journal/Memory.

Sources: Unsloth docs, Reddit/LocalLLaMA comparisons (2026), Axolotl optimizations, roleplay fine-tuning guides.

## 2. Best Emotional TTS Options Locally on 8GB VRAM

**Top Contenders** (ranked for emotional expressiveness + 8GB fit + integration ease):

1. **Coqui XTTS v2** (or recent forks)
   - Strengths: Strong voice cloning (6s reference audio), good emotional control, multilingual.
   - VRAM: ~4–8GB comfortable.
   - License: Practical for our use.
   - Best for: Personalized companion voices that evolve with character growth.

2. **StyleTTS 2 / Orpheus 3B variants**
   - Strengths: Excellent natural emotional speech (tags for laugh, whisper, cry, etc.). Orpheus especially praised for human-like expressiveness.
   - VRAM: 2–8GB range (Orpheus ~6–8GB recommended).
   - Great for narration + emotional delivery in roleplay.

3. **Piper** (VITS-based)
   - Strengths: Extremely fast/real-time (even on CPU/RPi), tiny footprint, 30+ languages/voices.
   - VRAM: CPU-only or minimal GPU.
   - Weakness: Less emotional depth/naturalness than above (more "robotic" in complex scenes).
   - Best as: Lightweight fallback or for quick responses.

**Other notes**:
- Kokoro: Very efficient CPU-friendly option.
- Bark: Creative (laughter, sighs, ambient) but slower/heavier — niche use.
- General: Emotional quality has improved significantly in 2026 open models. Use emotional tags/prompt engineering in backend.

**Recommendation for Reverie**:
- Primary emotional engine: **Coqui XTTS v2 or StyleTTS/Orpheus** for depth.
- Fallback: Piper for speed/low-resource.
- Integration: Python backend (subprocess or API) → expose to Tauri frontend. Tie voice emotion to memory/reflection state (e.g., more teasing tone after growth).
- Future: Voice cloning from user-provided samples or generated character audio.
- 8GB friendly: Run TTS on CPU or quantized/low-priority when GPU busy with LLM/image.

Sources: 2026 TTS comparisons (Reddit, local guides), Coqui/XTTS, StyleTTS, Piper benchmarks.

## 3. Visual Novel Best Practices in Svelte + Tauri (Sprite Systems, Live2D vs Custom, State Management)

**Stack Validation**: Tauri 2 + Svelte/SvelteKit is excellent and commonly used for performant desktop apps. Svelte's compiler + reactivity shines for VN-style UIs.

**Sprite Systems & Live2D vs Custom**:
- **Recommended: Custom sprite sheets + expression/pose switching** (lighter, 8GB-friendly).
  - Use `<img>` or canvas/WebGL for sprites.
  - Preload expression variants (happy, teasing, dominant, etc.) mapped to emotion state from memory/self-learning.
  - Backgrounds: Dynamic via lorebook/memory (scene keywords trigger assets).
  - Advantages: Low resource, easy to implement, sufficient for high "alive" feeling when combined with dialogue + growth notifications.
- **Live2D**: Possible via Three.js/WebGL integration in Svelte, but heavier on CPU/GPU. Use only if we need advanced animation later (Pro tier or optional). Custom sprites win for our 8GB floor and speed.

**State Management Best Practices (Svelte)**:
- Use Svelte 5 `$state` + runes for reactive character/dialogue state.
- Context API or dedicated stores (e.g., `characterStore`, `sceneStore`, `memoryStore`) for shared state across components.
- Avoid prop drilling; use context for dialogue history, current emotion, VN mode toggle.
- Efficient updates: Only re-render affected parts (expressions, dialogue box). Lazy-load assets.
- Tauri specifics: SPA mode (no SSR), static adapter for SvelteKit. Expose Rust/Python backend via Tauri commands for heavy lifting (LLM, memory, image gen).

**VN Mode UX**:
- Toggle between Chat mode ↔ Visual Novel mode.
- Side panel or full-screen: Sprite + background + expression overlays.
- Dialogue box with typewriter effect, choices (if branching), emotion indicators.
- Tie to self-learning: Expressions react to Reflection insights or Journal entries. Growth notifications can trigger visual "evolution" (subtle sprite updates).

**Recommendation**:
- Start with custom sprites + Svelte reactive state.
- Modular components: `VNScene.svelte`, `ExpressionSprite.svelte`, `DialogueBox.svelte`.
- Asset pipeline: Local folder per character (sprites, backgrounds) + metadata in character card.
- Performance: Preload low-res, upgrade on demand. Heavy image gen offloaded.

Sources: Tauri + Svelte guides (2025-2026), Svelte best practices, VN dev patterns.

## 4. Local Image Generation Integration Patterns (Flux vs SDXL Turbo, Memory-Efficient Workflows)

**Quality Winner 2026**: **Flux** (especially Flux.1-schnell or GGUF quantized variants) for superior coherence, anatomy, complex scenes (great for futa/slime/physics).
- SDXL Turbo / SD 1.5 variants: Faster inference, lower baseline VRAM — good for quick in-chat previews or when speed > max quality.

**8GB VRAM Strategies (ComfyUI recommended)**:
- **Quantization**: GGUF Q4/Q5 or FP8 for Flux — dramatically reduces footprint while keeping high quality.
- **ComfyUI flags**: `--lowvram`, `--cpu-text-encoder` or VAE offload, layer/model offloading.
- **Workflow patterns**:
  - Low-res preview first → upscale if needed.
  - Batch size 1, restart ComfyUI between heavy generations to clear fragmentation.
  - Sequential processing for tight VRAM.
- Flux on 8GB: Feasible with GGUF + optimizations (slower but usable; ~26s for 1024x1024 in some reports). SD 1.5/Turbo much faster/lighter.
- Integration: Python backend runs ComfyUI as subprocess or via API (ComfyUI has good HTTP/WebSocket API). Expose "generate_scene_image(prompt, emotion, character_id)" endpoint.

**Recommendation for Reverie**:
- Primary: **Flux GGUF (Q5 or better)** via ComfyUI for in-chat images and VN backgrounds/sprites (when generative needed).
- Fallback: SDXL Turbo or SD 1.5 for speed on 8GB.
- Memory-efficient: Always use quantized + offloading. Cache models smartly. For Pro tier: Higher quality settings or cloud offload option.
- Tie to app: Image gen triggered from chat/memory (e.g., "generate visual of this scene") or VN mode. Future: Feed into Futa-Vision video pipeline.
- In-chat: Button to generate/attach image that discusses in context (vision support if model allows).

Sources: ComfyUI 2026 guides, Flux low-VRAM optimizations, GGUF workflows.

## Overall Tech Decisions for Milestone 3 & Beyond
- **LoRA**: Unsloth primary (personal + global).
- **TTS**: Coqui XTTS / StyleTTS primary for emotion; Piper fallback.
- **VN/Visuals**: Custom sprites + Svelte reactive state (Live2D later if needed).
- **Image Gen**: ComfyUI + Flux GGUF (quantized) with heavy optimizations.
- All must stay strictly 8GB-friendly with graceful degradation.
- Future-proof: Modular Python backend services; clear hooks for Futa-Vision video triggering from chat/VN scenes.

## Next Steps
1. Incorporate key points into `Reverie_Source_of_Truth.md` and `DEVELOPMENT_PLAN.md`.
2. Add "Research-Backed Choices" section to `prompts/GLOBAL_CODING_PROMPT.md`.
3. Use this research to refine the first coding prompt for Visual Novel foundation.
4. Revisit/update this doc after each milestone as new 2026 tools emerge.

This centralized research ensures consistent, high-quality decisions aligned with our vision of truly alive, local-first companions.