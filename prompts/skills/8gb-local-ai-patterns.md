---
name: 8gb-local-ai-patterns
description: Use for 8GB VRAM optimized local AI integration patterns in Reverie including Unsloth QLoRA training rank and dataset choices, ComfyUI Flux GGUF lowvram workflows, emotional TTS selection with Coqui StyleTTS Piper, and Svelte Tauri Visual Novel custom sprite reactive state management
---

# 8gb Local AI Patterns

Use this skill when implementing performance-critical local components on strict 8GB RTX 4070 mobile hardware for the Reverie companion. Always combine with current RESEARCH_Milestone3.md and Reverie_Source_of_Truth.md.

## LoRA Training (Unsloth Primary)
- Default to Unsloth + QLoRA 4-bit for all personal and character growth LoRAs on 8GB.
- Recommended rank: 16 for speed and limited data, 32 as sweet spot for roleplay personality consistency and physics learning. Avoid 64+ unless on Pro tier or larger GPU.
- Dataset curation: Pull high-signal examples only from Reflection outputs, Journal entries, high-rated chats, and futa/slime physics scenes. Target 500-5000 quality examples. Use 1-3 epochs.
- Run training in background or overnight with low learning rate and gradient checkpointing.
- Cross-check compatibility when mixing with Axolotl later.

## Emotional TTS Integration
- Primary choice for emotional depth: Coqui XTTS v2 or StyleTTS 2 / Orpheus 3B variants (support emotional tags like laugh, whisper, possessive tone).
- Fast lightweight fallback: Piper (CPU real-time, excellent for quick responses).
- Tie TTS emotion and prosody directly to memory state, Reflection insights, and growth notifications.
- Run TTS on CPU or low-priority when GPU is occupied by LLM or image generation.

## Visual Novel Mode (Svelte + Tauri)
- Prefer custom sprite sheets with expression and pose switching over Live2D for 8GB performance and simplicity.
- Implement reactive state with Svelte 5 $state runes + context or dedicated stores for current emotion, scene, dialogue history, and VN mode toggle.
- Map memory/reflection outputs to expression changes. Trigger subtle visual evolution on growth events.
- Use lazy asset loading and low-res sprites by default. Provide upgrade path for higher quality on Pro tier.
- Keep VN mode as a toggle alongside standard chat. Expose clean hooks for future Futa-Vision video clip triggering from scenes.

## Local Image Generation
- Primary engine: ComfyUI with Flux GGUF (Q4 or Q5) or FP8 quantized models for best quality on complex futa/slime scenes.
- Strict 8GB optimizations: Always launch with --lowvram, use layer/model offloading, keep batch size 1, and restart ComfyUI between heavy generations.
- Fast fallback: SDXL Turbo or SD 1.5 variants when speed matters more than maximum fidelity.
- Expose a clean Python service (e.g. generate_scene_image) that accepts prompts enriched by memory and character state.
- Cache models intelligently and prefer low-res previews with optional upscale.

## General 8GB Performance Rules
- Every new feature must include explicit performance notes or graceful degradation path.
- Offload heavy work (training, image gen, TTS) to background/idle time or CPU when possible.
- Validate on actual RTX 4070 8GB mobile hardware before merging.
- When in doubt, default to lighter quantized/custom sprite approaches over heavier full-precision or Live2D options.

## Integration with Self-Learning & Future Vision
- All patterns must reinforce the multi-layer memory + growth loop (Reflection → Journal → Personal LoRA → Global model improvement).
- Design every component with clear extension points for Futa-Vision reactive video clips triggered from chat or VN scenes.
- Update RESEARCH_Milestone3.md when new 2026 tools or benchmarks emerge.