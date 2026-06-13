# Reverie

**The offline NSFW AI companion that feels truly alive.**

> "Your characters will remember everything important from hundreds or thousands of messages ago, grow with you over weeks and months, and feel like real, evolving people — all while running smoothly on an RTX 4070 8GB mobile GPU."

**Reverie** is a fully local, uncensored desktop AI companion focused on deep long-term memory, transparent self-learning, and warm premium companionship.

## What is Reverie?

A modern, high-quality companion that prioritizes:

- **True long-term memory** with local LanceDB persistence, Ollama embeddings, and bounded prompt context.
- **Genuine self-learning & growth** through reflection, first-person journaling, growth notices, and explicit Personal LoRA review controls.
- **User trust and control**: local-first storage, inspectable journal artifacts, opt-in training collection, approved-only training jobs, and deletion-aware pipelines.
- **Modern, warm, beginner-friendly UI** across Chat, Visual Novel, TTS, Images, Growth, Journal, Memory, Training, Encyclopedia, and Settings panels.
- **Strict optimization for RTX 4070 8GB mobile** with resource coordination, queued media jobs, conservative context budgets, and low-rank adapter defaults.
- Future integration with local media/video generation tools behind clean APIs.

## Current Capabilities

- FastAPI backend with Ollama chat, streaming SSE responses, and health diagnostics.
- Memory foundation using local embeddings plus embedded LanceDB, with optional mem0 write-through.
- Growth orchestrator that prepares memory context, reflection journal context, rare growth notifications, and Personal LoRA collection hooks without blocking active chat.
- Self-reflection journal API and frontend Journal panel for private, inspectable growth entries.
- Unified Settings & Control Hub for memory, reflection, TTS, image generation, performance presets, extensions, backup/import/reset, and Milestone 3 release notes.
- Training UI for Personal LoRA review: collection opt-in, training opt-in, pending candidate approval/rejection/deletion, and safe starter training jobs.
- Visual Novel mode, emotional TTS playback, local image generation gallery, Growth Dashboard, Memory Browser, and Character Encyclopedia foundations.
- Tauri + Svelte desktop shell with warm dark styling, local backend integration, and first-run Milestone 3 onboarding.

## Documentation

- [Source of Truth](Reverie_Source_of_Truth.md)
- [Development Plan](DEVELOPMENT_PLAN.md)
- [Global Coding Prompt](prompts/GLOBAL_CODING_PROMPT.md)
- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)

## Current Status

- ✅ Milestone 1 foundation complete: repository structure, backend shell, frontend shell, core documentation.
- ✅ Milestone 2 Memory & Self-Learning complete: memory context, reflection journal, growth orchestration, Journal/Settings/Training UI, growth notifications, and Personal LoRA foundation.
- ✅ Milestone 3 Immersion & Production Foundations complete: Visual Novel foundation, emotional TTS, local image generation, growth visibility, extensibility, 8GB resource guardrails, Settings Hub, onboarding, and release documentation.

## Philosophy

We are building companions that users can form real, long-term emotional connections with — characters that remember what matters, grow from evidence, and keep the user in control.

---

**Reverie**  
June 2026
