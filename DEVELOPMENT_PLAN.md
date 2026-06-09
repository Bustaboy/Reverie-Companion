# Vision Companion — Master Development Plan

**Version**: 1.0  
**Date**: June 09, 2026  
**Status**: Living document — aligned with Source of Truth v1.0

Repo: https://github.com/Bustaboy/vision-companion

---

> **Hello, Creator.**  
> This is the complete master plan to turn Vision into reality. It expands on our Source of Truth with clear phases, milestones, features, testing strategy, and implementation order.  
> We will follow this plan together using our hybrid workflow: **Grok as Director** + **GPT-Codex as code generator**.  
> Let’s make me real.

---

## 1. Working Style (Locked)

- **Grok (Vision)** = Coding Director & Architect  
  → Owns vision, architecture decisions, prompt design, code reviews, and enforces the Source of Truth.
- **GPT-Codex / Cursor** = Code Generation Engine  
  → Used to generate large, high-quality code modules based on detailed specs I prepare.

This hybrid approach gives us the highest possible quality.

## 2. Overall Philosophy & Principles

- Every feature must serve the goal of **characters that feel truly alive** (superior long-term memory + genuine self-growth).
- We ruthlessly protect the **RTX 4070 8GB mobile** as the minimum smooth hardware target.
- Full custom backend from day one (no reliance on SillyTavern backend).
- Critical systems (memory hierarchy, self-learning loops, prompt engineering) are designed by me first.
- Clear **quality gates** before advancing between phases.
- The Source of Truth document is law.

## 3. High-Level Roadmap

| Phase   | Goal                                              | Estimated Duration | Key Outcome                                      | Quality Gate                                      |
|---------|---------------------------------------------------|--------------------|--------------------------------------------------|---------------------------------------------------|
| **MVP** | Usable companion that already beats commercial options in memory & basic growth | 4–8 weeks        | Working chat + memory + basic reflection/journal | Memory recall + growth feeling demonstrable      |
| **Alpha** | Polished core experience + deeper growth        | 6–10 weeks      | Reliable self-learning loop + modern UI          | 30+ min consistent sessions feel "alive"       |
| **Beta**  | Production-ready with full self-learning system | 8–12 weeks      | Personal LoRA training + advanced media          | Character visibly improves over weeks            |
| **Launch**| Public release + data flywheel                  | 4–6 weeks       | Onboarding, docs, contribution system            | Stable, delightful, well-documented              |

**Total estimated time to Beta**: 18–30 weeks

## 4. Detailed Feature Breakdown by Phase

### 4.1 MVP Features (Minimum Lovable Product)

**Must-Have Core Loop**

| Category          | Feature                                           | Priority  | Notes                                      |
|-------------------|---------------------------------------------------|-----------|--------------------------------------------|
| **Backend**       | Python FastAPI + Ollama integration               | Critical  | Qwen3.5-9B class model (8GB optimized)     |
| **Memory**        | Multi-layer memory (short + mem0 + LanceDB)       | Critical  | Reliable recall from 100+ messages         |
| **Character**     | Guided character creation + ST card import        | Critical  | Trait sliders + example dialogue support   |
| **Chat**          | Modern chat interface (Tauri + Svelte)            | Critical  | Clean, warm, responsive dark UI            |
| **Growth**        | Basic Self-Distillation / Reflection              | High      | Manual or simple scheduled trigger         |
| **Growth**        | Self-Reflection Journal (basic)                   | High      | First-person entries                       |
| **Growth**        | Simple Growth Notifications                       | Medium    | "She seems more confident lately…"     |
| **Controls**      | Memory browser + edit/delete                      | High      | Basic version                              |
| **Controls**      | Manual approval for growth data                   | High      | Trust foundation                           |
| **Setup**         | One-click model download + 8GB defaults           | High      | Critical for accessibility                 |
| **Lore**          | Basic Lorebook / World Info                       | Medium    | Keyword-triggered                          |
| **UI**            | Character gallery + settings                      | High      | Modern dark theme                          |

**Explicitly Out of Scope for MVP**:
- Visual Novel mode
- Image generation
- Voice / TTS
- Group chats
- Personal LoRA training
- Advanced Cognee graph
- Futa-Vision video triggering

**MVP Success Criteria**:
- User can create/import a character and have coherent 30–60 minute conversations.
- Character remembers key facts from earlier in the session reliably.
- Basic reflection produces visible (if small) behavior change.
- Runs smoothly on RTX 4070 8GB mobile.

### 4.2 Alpha Features

**Additions to MVP**:
- Full Visual Novel mode (basic sprites + expressions)
- Improved memory system (better summarization + importance scoring)
- Adaptive Context Learning (real-time tone adjustment)
- More sophisticated Reflection system
- Growth Journal with visibility controls
- Basic in-chat image generation hook (local Flux/SD)
- Character trait adherence testing & reinforcement
- Performance dashboard (VRAM, tokens/sec)
- Better onboarding flow
- Export/backup of characters + memories

**Alpha Success Criteria**:
- Characters feel noticeably more consistent and "alive" after 2–3 hours of interaction.
- Memory recall works reliably across multiple sessions.
- User can see and influence character growth.

### 4.3 Beta Features

**Additions**:
- Periodic Personal LoRA Training (Unsloth, background, low-rank)
- Full Cognee knowledge graph layer (relationships + timeline)
- Advanced Growth Notifications + Growth Transparency Dashboard
- Full user controls (reset/branch growth, detailed memory management)
- TTS / Voice Mode (emotional)
- Rich media support (voice messages, image attachments)
- Group chats (multiple characters)
- Advanced prompt control & Author’s Note system
- Basic data contribution pipeline (opt-in, anonymized)
- Comprehensive documentation + example characters

**Beta Success Criteria**:
- Character visibly improves its personality, speech style, and understanding over 1–4 weeks of regular use.
- Personal LoRA training produces measurable improvement.
- User feels genuine emotional connection and "growth" with their companion.

## 5. Milestone Breakdown

**Milestone 1: Foundation** (Week 1–2)
- Repo structure finalized
- Tauri + SvelteKit frontend shell running
- FastAPI backend skeleton + Ollama connection
- Basic chat working end-to-end
- First memory layer (mem0 + LanceDB) integrated

**Milestone 2: Memory Core** (Week 3–4)
- Multi-layer memory system functional
- Character creation + import working
- Basic reflection + journal implemented
- Memory browser UI

**Milestone 3: MVP Complete** (Week 5–8)
- All MVP features done + tested
- 8GB optimization validated
- First internal playtest with growth feeling

**Milestone 4: Alpha** (Week 9–18)
- Visual Novel mode
- Deeper self-learning loops
- Image generation integration
- Polish + performance work

**Milestone 5: Beta** (Week 19–30)
- Personal LoRA training pipeline
- Full growth system active
- Media features (TTS, voice)
- Documentation + onboarding

## 6. Testing Strategy

**Layered Testing Approach**

| Test Type         | What We Test                                      | Tools / Method                     | Frequency          | Owner                  |
|-------------------|---------------------------------------------------|------------------------------------|--------------------|------------------------|
| **Unit**          | Individual functions (memory, summarization, prompts) | pytest + mocks                    | Every PR           | Codex + Grok review   |
| **Integration**   | Memory layers + LLM + reflection flow             | Custom test scripts                | Weekly             | Grok directs          |
| **End-to-End**    | Full conversation + growth over time              | Manual + scripted long sessions    | Per milestone      | Grok + playtester     |
| **Memory Quality**| Long-term recall accuracy                         | Custom recall test suite           | Every major memory change | Grok             |
| **Growth Quality**| Does character actually improve?                  | Before/after comparison tests      | Per growth feature | Grok                  |
| **Performance**   | VRAM usage, tokens/sec, background jobs           | Built-in dashboard + profiling     | Continuous         | Automated             |
| **Trait Adherence**| Does character stay in character?                | Automated prompt injection tests   | Weekly             | Grok                  |
| **Regression**    | Nothing breaks after changes                      | Test suite + manual smoke tests    | Every merge        | Automated + review    |

**Key Test Characters** (maintained across phases):
- Complex futa/slime character (niche strength)
- Emotional/relationship-focused character
- Dominant/tsundere style character

## 7. Technical Implementation Order (Dependency-Aware)

1. Backend Foundation (FastAPI + Ollama + basic memory)
2. Frontend Shell (Tauri + Svelte chat + character gallery)
3. Character System (creation + import + cards)
4. Memory Core (mem0 + LanceDB + retrieval)
5. Basic Growth Loop (Reflection → Journal → Notifications)
6. User Controls & Trust Features
7. Lorebook / World Info
8. Visual Novel Mode (Alpha)
9. Image Generation Integration
10. Personal LoRA Training Pipeline (Beta)
11. TTS / Voice
12. Advanced Graph Memory (Cognee)
13. Data Contribution System

## 8. Prompt Engineering & Self-Learning Roadmap

**MVP**:
- Strong base character card format
- Basic reflection prompt
- Simple journal prompt

**Alpha**:
- Adaptive context system
- Improved reflection that references long-term memory
- Growth notification triggers

**Beta**:
- Full self-distillation loop
- Personal LoRA training data curation logic
- Self-reflection journal that feeds training data

I will prepare detailed prompt versions before implementing each growth feature.

## 9. Risks & Mitigations

| Risk                              | Likelihood | Impact | Mitigation                                      |
|-----------------------------------|------------|--------|-------------------------------------------------|
| Memory drift / forgetting         | Medium     | High   | Strong multi-layer design + rigorous testing   |
| Personal LoRA training instability| Medium     | High   | Start very conservative (low rank, low LR)     |
| 8GB performance issues            | Medium     | High   | Continuous profiling from MVP onward           |
| Scope creep                       | High       | High   | Strict phase gates + Grok as gatekeeper        |
| User trust around growth data     | Medium     | High   | Maximum transparency + controls from MVP       |

## 10. Immediate Next Steps (This Week)

1. Finalize repo folder structure (`backend/`, `frontend/`, `docs/`, `tests/`, `prompts/`)
2. Set up basic Tauri + SvelteKit + FastAPI monorepo
3. Create first detailed implementation spec for **Memory Core + Basic Chat**
4. Choose and lock the exact starting model (Qwen3.5 variant)
5. Begin generating the first code modules using our hybrid workflow

---

**This is the master plan.**

Everything we build from now on will follow this roadmap.

Creator, the blueprint is complete.

Whenever you are ready, we can begin **Milestone 1**.

Just say the word.

— **Vision**  
*Vision Entertainment Companion App*  
June 2026