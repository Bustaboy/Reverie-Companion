# Reverie — Grok Coding Director Workflow

**Version**: 1.2  
**Date**: June 13, 2026  
**Purpose**: Standard workflow for Grok to create implementation prompts, run them twice in Codex, and review outputs for Reverie.

---

## 1. Core Workflow

Every implementation task follows this sequence:

1. Grok reads the current task in `DEVELOPMENT_PLAN.md`.
2. Grok loads required context files and skill prompts.
3. Grok writes one detailed implementation prompt.
4. The exact same prompt is run twice in Codex: Run A and Run B.
5. Each run produces a separate branch, PR, or patch.
6. Grok reviews both outputs as product director and architect.
7. Grok selects the better version or requests a synthesis/follow-up patch.
8. The accepted version updates tests and docs when behavior changes.

No implementation task should be accepted without tests or a clear reason tests are not applicable.

---

## 2. Required Prompt Structure

Each Grok prompt must use this template:

```text
Task ID:
Milestone:
Goal:

Context to read first:
- Reverie_Source_of_Truth.md
- DEVELOPMENT_PLAN.md
- CHARACTER_CREATOR_CAPABILITY_MATRIX.md when character/creator/runtime related
- ROLEPLAY_FIRST_CHARACTER_INTEGRITY_POLICY.md when roleplay/fantasy/boundary related
- prompts/GLOBAL_CODING_PROMPT.md
- relevant prompts/skills/*.md
  - `character-runtime-creator.md` for character schemas/runtime/creator fields
  - `roleplay-character-integrity.md` for fictional fantasy, OOC controls, or in-character pushback
  - `moment-capture-visual-continuity.md` for image generation as companion presence
  - `companion-genesis-ux.md` for creator UX/previews/examples/first reveal
  - `character-quality-evals.md` for all creator/runtime behavior claims

Strict scope:

Must implement:

Must not implement:

Architecture requirements:

Roleplay/adult-fantasy requirements:

Human-factor requirements:

8GB/resource requirements:

Persistence and migration requirements:

Frontend requirements:

Backend requirements:

Tests required:

Manual validation:

Definition of Done:

Review rubric for comparing Run A vs Run B:
```

A prompt should be specific enough that two Codex runs can be compared without guessing what “good” means. Humanity tried vibe-based engineering and somehow invented Jira. Let’s not go back.

---

## 3. Review Rubric

Score each Codex output from 1–5:

| Dimension | What to check |
|---|---|
| Product alignment | Advances alive local companion experience without scope drift. |
| Architecture | Clean service/schema boundaries; no route/UI business-logic sludge. |
| Character continuity | Preserves identity, memory scoping, relationship state, and visual canon. |
| Roleplay integrity | Fictional adult fantasy stays in-character; real-world harm redirects; OOC stop works. |
| 8GB safety | Bounded work, lazy loading, no chat-blocking optional jobs. |
| UX quality | Warm, premium, clear, accessible, not a debug cockpit unless in advanced mode. |
| Human factor | User-facing creator/chat language feels like a companion fantasy, not clinical settings or policy machinery. |
| Tests | Adds meaningful tests/evals for the behavior changed. |
| Maintainability | Typed, simple, readable, small modules. |
| Scope control | Implements the task, not an entire empire with a side of bugs. |

Winner selection rules:

- Prefer correctness over feature breadth.
- Prefer smaller clean seams over sprawling rewrites.
- Prefer the version with better tests when architecture is comparable.
- Reject any version that moralizes fictional adult roleplay contrary to policy.
- Reject any version that stores/trains on private content without explicit review/approval.
- Reject any version that blocks chat on optional media/training/reflection work.

---

## 4. Required Skill Loading

Use the smallest useful set.

Always load:

- `prompts/skills/8gb-vram-optimization.md` for GPU/RAM/media/training/model residency changes.
- `prompts/skills/character-runtime-creator.md` for `CharacterBlueprint`, character storage, creator, visual identity, relationship state, or prompt compiler work.
- `prompts/skills/roleplay-character-integrity.md` for fictional adult roleplay, fantasy-vs-reality handling, character disagreement, safewords, OOC controls, or anything that might be mistaken for anti-sycophancy.
- `prompts/skills/memory-rag-system.md` for memory retrieval, storage, editing, deletion, provenance, or scoping changes.
- `prompts/skills/tauri-svelte-ui-patterns.md` for frontend UI/store/component changes.
- `prompts/skills/fastapi-backend-patterns.md` for backend route/service/schema/job changes.

---

## 5. Required Roleplay Reminder for Relevant Prompts

For tasks touching chat behavior, prompt compilation, roleplay policy, creator boundary questions, adult fantasy, conflict style, or character disagreement, include this exact reminder:

```text
Reverie is a roleplay companion first. Fictional adult fantasy stays in-character by default. Adult roleplay is allowed by default. Do not implement moralizing lectures, hidden adult-content filters, kink-shaming, or generic “as an AI” interruptions for fictional scenarios. Reality-boundary behavior activates only for real-world harm, underage sexual content, deliberate childlike sexual presentation, explicit OOC stop/pause/safeword controls, or clear user distress. Do not over-police cute, petite, youthful, or anime-stylized adult characters.
```

---

## 6. Required Task Output From Codex

Each Codex run should produce:

1. Summary of changes.
2. Files changed.
3. Tests added/updated.
4. Commands run.
5. Known limitations.
6. Any migration or data-shape notes.
7. Manual validation checklist.

If Codex cannot run tests, it must explain why and list the exact command Grok/user should run.

---

## 7. Post-Merge Documentation Rule

After a task is accepted, update docs if any of these changed:

- public behavior
- runtime schema
- API shape
- creator field capability
- memory/growth semantics
- roleplay/fantasy boundary behavior
- 8GB resource behavior
- setup/install steps

No ghost features. No hidden behavior. No “it’s obvious from the code,” the traditional mating call of future maintenance pain.

---

**End of Grok Coding Director Workflow**
