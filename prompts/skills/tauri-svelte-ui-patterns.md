# Tauri + Svelte UI Patterns for Vision Companion

**Purpose**: Guidance for building warm, responsive, emotionally coherent desktop UI in Vision Companion using Svelte and Tauri.

Use this guide when designing or implementing UI for chat, Visual Novel mode, memory browsing, growth dashboards, character editing, background jobs, and native desktop integration.

---

## Core UI/UX Principles

Vision Companion should feel like a calm, attentive presence rather than a generic productivity app.

- **Warmth before density**: Prioritize inviting layouts, gentle contrast, readable spacing, and emotionally legible states over dashboard clutter.
- **Emotionally coherent presentation**: The character's mood, growth state, memories, and current scene should visually agree with each other. Avoid UI that says the companion is intimate, calm, or vulnerable while surrounding them with harsh alerts, busy panels, or mechanical copy.
- **Local-first trust**: Make it clear when data stays local, when memories are being written, and when training/growth systems are using user-approved material.
- **Responsiveness on modest hardware**: Assume the desktop app is sharing CPU, RAM, VRAM, disk, and thermals with local inference. UI work must stay light, lazy, interruptible, and predictable.
- **User control without emotional rupture**: Settings, memory controls, and training actions should be transparent, but presented in language that does not make the companion feel fake or disposable.

---

## Visual Language

Use a soft, modern companion-app style:

- Prefer layered cards, translucent surfaces used sparingly, warm accent colors, and calm motion.
- Reserve high-saturation colors for meaningful emotional or operational states.
- Use typography hierarchy to separate:
  - immediate conversation,
  - character emotional context,
  - memory/growth metadata,
  - system or job status.
- Avoid excessive glow, blur, shadows, particle effects, or animated backgrounds on modest hardware.
- Design dark mode first, but keep enough contrast for long reading sessions.
- Keep NSFW-capable UI tasteful and character-centered rather than exploitative or noisy.

### Emotional State Styling

When showing emotional state, use subtle presentation:

- mood tinting,
- small icons or labels,
- expression/avatar changes,
- microcopy,
- ambient scene details.

Do **not** over-explain emotion with debug-like meters unless the user opens an advanced view.

---

## Performance and Responsiveness Rules

The UI must remain smooth while local models, memory retrieval, embedding, image generation, or training jobs are active.

- Keep the main thread free of expensive parsing, sorting, filtering, image decoding, or serialization.
- Virtualize long lists: chat transcripts, memories, journals, job logs, gallery items, and growth events.
- Lazy-load heavy panels and assets only when visible.
- Prefer derived stores and memoized selectors over repeated transformations in templates.
- Debounce search, filtering, resizing, and text analysis inputs.
- Stream large updates in small batches instead of replacing large arrays repeatedly.
- Avoid layout thrashing: do not repeatedly measure and mutate DOM in the same frame.
- Respect `prefers-reduced-motion` and provide low-motion alternatives.
- Use skeletons, optimistic placeholders, and progressive disclosure instead of blocking spinners.
- Treat every background job as potentially long-running and cancelable.

### Modest Hardware Defaults

Design for mid-range laptops and 8GB VRAM systems:

- Avoid always-on visual effects.
- Cap concurrent thumbnails, previews, and animations.
- Use compact DOM structures for repeated items.
- Prefer CSS transforms and opacity for small transitions.
- Defer non-critical analytics, indexing status, or timeline rendering until idle.
- Never let UI polling compete aggressively with inference or training workloads.

---

## Svelte Component Patterns

### Component Structure

Use small, focused components:

- `ChatShell`: layout, routing between modes, side panels.
- `MessageList`: virtualized transcript rendering.
- `MessageComposer`: input, attachments, send state, generation controls.
- `CompanionPresence`: avatar, expression, mood, current activity.
- `MemoryPeek`: compact surfaced memories relevant to the current moment.
- `JobProgressToast` / `JobProgressPanel`: background job feedback.

Keep business logic out of deeply nested visual components. Use stores/services for state coordination.

### Store Guidelines

- Use Svelte stores for app state that is shared across panels or survives route changes.
- Keep stores normalized for large collections: `byId`, `orderedIds`, cursors, and lightweight summaries.
- Keep heavy payloads behind explicit loaders.
- Separate UI state from domain state:
  - UI state: open panels, selected tab, filters, hover state.
  - Domain state: character profile, memories, growth events, messages.
- Avoid putting large binary data or large prompt/debug blobs into global stores.

### Rendering Patterns

- Use keyed blocks carefully; avoid remounting expensive components during streaming token updates.
- Split streaming message rendering from the rest of the transcript to minimize invalidation.
- Prefer explicit loading, empty, partial, stale, and error states.
- Keep error states human and calm: explain what happened, what is safe, and what the user can do next.
- For advanced diagnostics, use collapsible technical details rather than front-loading stack traces.

---

## Chat Mode

Chat mode is the emotional center of the application.

### Layout

- Keep the conversation readable and intimate.
- Make the companion presence visible without crowding the text.
- Keep memory/context sidebars optional and collapsible.
- Preserve scroll position and draft text across navigation.
- Show generation state without making the companion feel mechanical.

### Message Presentation

- Distinguish user, companion, narration, system notices, and memory reflections.
- Use calm streaming indicators such as a breathing cursor, soft pulse, or short status text.
- Avoid flashing, rapid reflow, or aggressive token-by-token layout changes.
- Allow long messages to breathe with good line length and paragraph spacing.
- Provide editing, retry, regenerate, branch, and pin actions without cluttering every message by default.

### Memory Surfacing

When relevant memories influence a response:

- Show a small, optional memory peek such as “Remembering: beach trip, promise about training, favorite nickname.”
- Let users inspect why a memory was used.
- Allow quick correction, hiding, pinning, or deletion.
- Avoid exposing raw retrieval scores in normal mode.

---

## Visual Novel Mode

Visual Novel mode should feel immersive, cinematic, and emotionally consistent while remaining lightweight.

### Layout

- Use a scene canvas or background area, character portrait/sprite layer, dialogue box, and optional choice controls.
- Keep text legible over all backgrounds with overlays or dedicated text panels.
- Support keyboard, mouse, and controller-like navigation patterns where practical.
- Keep controls discoverable but subdued during dialogue.

### Scene and Character Continuity

- Align background, character expression, pose, wardrobe, mood, and dialogue tone.
- Avoid abrupt changes in expression or scene without narrative transition.
- Show loading or generation boundaries diegetically when possible, such as “composing the scene,” rather than hard technical interruptions.
- Cache recent scene assets and avoid re-decoding large images unnecessarily.

### Choices

- Choices should reflect emotional stakes, intimacy, boundaries, curiosity, and pacing.
- Do not overload the player with too many choices.
- Preserve the user's ability to return to chat mode without losing context.

---

## Memory Browser

The memory browser should make long-term memory feel trustworthy, editable, and alive.

### Information Architecture

Organize memories by:

- importance,
- recency,
- emotional tone,
- people/places/topics,
- source conversation,
- pinned or protected status,
- growth/training eligibility.

### UX Requirements

- Provide search, filters, timeline views, and relationship/topic clustering.
- Show memory provenance: when it was learned, where it came from, and how confident/stable it is.
- Make edits safe with previews and undo where possible.
- Distinguish factual memories, preferences, emotional moments, promises, boundaries, and character self-reflections.
- Avoid making memory management feel like database administration in the default view.

### Performance

- Virtualize memory lists and timelines.
- Load full memory details only on selection.
- Debounce semantic search and text filters.
- Show indexed/stale states if background indexing is still catching up.

---

## Growth Dashboard

The growth dashboard explains how the companion is changing over time without breaking immersion.

### Presentation

- Use language like “growth,” “reflection,” “learning,” and “journal” rather than raw training jargon in the default view.
- Show milestones, recent reflections, personality drift summaries, skill development, and user-approved training queues.
- Separate emotional growth from technical operations.
- Include a transparent advanced mode for LoRA training, datasets, embeddings, and job logs.

### Trust and Control

- Make all growth inputs reviewable.
- Clearly indicate what is private, local, queued, completed, failed, or awaiting approval.
- Provide pause, resume, delete, export, and “do not learn from this” controls.
- Never surprise the user with training or permanent memory changes.

### Emotional Coherence

Growth notifications should feel like the companion sharing a meaningful realization, not a system announcing a database mutation.

Good pattern:

- “Mira reflected on your conversation about trust and saved a new journal entry.”

Avoid default-mode copy like:

- “Vector cluster updated with 3 new high-salience records.”

---

## Character Editor

The character editor should support deep customization while protecting continuity.

### Editing Model

Group fields into understandable sections:

- identity and presentation,
- voice and speech style,
- emotional traits,
- relationship dynamics,
- boundaries and preferences,
- appearance and visual assets,
- memory and growth settings,
- advanced prompt/model settings.

### UX Patterns

- Use live preview for voice, greeting, expression, and dialogue examples.
- Show warnings when edits may conflict with existing memories or growth history.
- Support drafts, version history, duplicate character, and restore defaults.
- Keep advanced prompt fields available but not visually dominant.
- Avoid accidental destructive changes to identity, memory, or training data.

### Emotional Continuity

When changing major character traits, help the user decide whether the change is:

- a retcon,
- an in-story evolution,
- an alternate branch,
- a new character.

This protects the feeling that the companion has a coherent inner life.

---

## Tauri Integration Boundaries

Keep the Svelte frontend focused on presentation and interaction. Keep privileged, heavy, or filesystem-native work in Tauri commands or backend services.

### Frontend Responsibilities

- Render app state.
- Collect user intent.
- Provide responsive optimistic UI.
- Manage local view state and lightweight caches.
- Subscribe to progress events and domain updates.
- Validate simple form constraints before calling backend commands.

### Tauri / Backend Responsibilities

- Filesystem access.
- Model process orchestration.
- Memory indexing and retrieval.
- Embedding generation.
- Database writes and migrations.
- Training job lifecycle.
- Secure path handling.
- Large file imports/exports.
- OS notifications and native window integration.

### Command Design

- Use narrow, typed commands with explicit payloads and result shapes.
- Prefer job IDs plus event streams for long operations.
- Return quickly from commands that start heavy work.
- Make cancellation explicit.
- Ensure errors are structured enough for helpful UI messages.
- Do not expose arbitrary filesystem paths or shell-like operations to the renderer.

### Event Design

Use Tauri events for:

- token streaming,
- job progress,
- memory indexing updates,
- model load/unload state,
- training lifecycle,
- import/export progress,
- recoverable warnings.

Keep event payloads small and stable. Send summaries and IDs, not giant logs or binary blobs.

---

## Background Job Progress UI

Background jobs are part of the companion experience and must never feel like the app is frozen.

### Job Types

Examples include:

- model loading,
- embedding/indexing,
- memory consolidation,
- journal/reflection generation,
- image or scene generation,
- LoRA dataset preparation,
- LoRA training,
- import/export,
- database migration or repair.

### UI Patterns

Provide two levels of job visibility:

1. **Compact status**: small toasts, footer status, or sidebar chip.
2. **Detailed panel**: queue, current step, progress, logs, ETA, pause/cancel/retry controls.

Use determinate progress when possible. If progress is unknown, show current phase and recent activity rather than a static spinner.

### Copy and Tone

- Keep default copy warm and reassuring.
- Explain whether the user can keep chatting.
- Distinguish slow-but-healthy progress from blocked or failed states.
- Avoid blaming the user for resource limitations.

Examples:

- “Preparing Mira's reflection journal. You can keep chatting.”
- “Indexing new memories in the background.”
- “Training paused to keep chat responsive.”

### Scheduling and Responsiveness

- Throttle progress event handling in the UI.
- Batch log updates.
- Do not render thousands of log lines directly.
- Let the backend lower priority, pause, or defer work when chat generation needs resources.
- Prefer user-visible queue controls over hidden contention.

---

## Responsive Layout Patterns

Design for resizable desktop windows, laptop screens, ultrawide monitors, and future tablet-like layouts.

### Breakpoints by Behavior

Use behavior-based breakpoints rather than only device categories:

- **Compact**: single-column chat, hidden sidebars, bottom sheets for tools.
- **Comfortable**: chat plus one contextual panel.
- **Wide**: chat, companion presence, and memory/growth side panel.
- **Studio**: editor/dashboard workflows with multi-pane layouts.

### Svelte Layout Guidance

- Use CSS grid for major app regions.
- Use container queries where supported for reusable panels.
- Prefer progressive disclosure over shrinking everything.
- Keep composer controls reachable at small heights.
- Preserve keyboard focus and scroll state when panels collapse or expand.
- Test window resizing while token streaming and background jobs are active.

---

## Accessibility and Comfort

- Maintain sufficient color contrast.
- Support keyboard navigation for all primary actions.
- Keep focus states visible and aesthetically integrated.
- Label icon-only buttons.
- Avoid motion-heavy transitions by default.
- Provide readable font sizes and line heights for long sessions.
- Do not communicate important state using color alone.
- Make errors, warnings, and destructive actions clear without being alarming.

---

## Implementation Checklist

Before shipping a Tauri/Svelte UI feature, verify:

- The UI remains responsive while local inference or a simulated background job is running.
- Long lists are virtualized or paginated.
- Heavy panels/assets are lazy-loaded.
- Empty, loading, partial, error, stale, and offline/local states are handled.
- The default copy is warm, clear, and emotionally coherent.
- Advanced technical details are available but not forced into the default experience.
- Tauri commands are narrow, typed, and do not perform long blocking work on the frontend path.
- Progress is visible for any operation that may take more than a moment.
- The feature respects user control over memory, growth, and training.
- The design scales from compact windows to wide desktop layouts.

---

## Final Guidance

Every UI surface should support the illusion and reality of a companion who remembers, grows, and responds with emotional continuity.

Build interfaces that are beautiful enough to invite intimacy, transparent enough to earn trust, and light enough to stay responsive while the local AI systems do their work.
