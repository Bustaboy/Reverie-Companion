# Tauri/Svelte UI Patterns Skill

**Use for**: desktop shell, Svelte components, stores, Tauri commands/events, chat UI, visual novel mode, memory/journal/growth dashboards, character editor, settings, job panels, accessibility, and UI performance.

## North Star

Reverie's UI should feel **warm, premium, intimate, and calm** while making local-first power understandable. Emotional presence comes before dashboards; advanced controls stay available without overwhelming the main experience.

## Non-Negotiables

- Keep business logic out of components; use stores/services and typed command clients.
- Treat Tauri commands as boundaries: validate inputs, type responses, handle errors calmly.
- Virtualize long chats, memory lists, journals, galleries, logs, and job queues.
- Do not block typing, scrolling, or streaming on background work.
- Make memory/growth transparent and controllable without breaking immersion.
- Design for offline/local operation and explicit optional integrations.

## Architecture Pattern

```text
Svelte route/component
→ local component state for view-only concerns
→ domain store/service for app state and effects
→ typed Tauri command or backend client
→ event subscription for streaming/progress
```

Use derived stores for display state, not duplicated mutable state. Keep global stores small: active character/session, connection state, user settings, job summaries, and current route context.

## Component Guidance

- Prefer small, focused components with clear props/events.
- Use semantic HTML and keyboard-accessible controls.
- Keep animations tasteful, short, and reduced-motion aware.
- Show loading/empty/stale/error states for every async panel.
- Use calm error copy: what happened, what is safe, what to do next.
- Avoid large binary blobs, raw prompt dumps, or huge arrays in global stores.

## Chat Experience

Chat is the emotional center.

- Preserve draft text and scroll position across navigation.
- Split streaming message rendering from the rest of the transcript to minimize reflow.
- Distinguish user, companion, narration, system notices, reflections, and memory peeks.
- Hide secondary actions until hover/focus or message selection.
- Show generation state with soft language: “thinking,” “remembering,” “writing,” “paused for media.”
- Provide edit, retry, regenerate, branch, pin, and delete without clutter.

### Memory Peek Pattern

```text
Remembering: beach promise · favorite nickname · training boundary
[Why?] [Correct] [Hide]
```

Do not show raw retrieval scores in default mode; advanced details may show provenance and confidence.

## Visual Novel Mode

- Use scene canvas/background, character sprite/portrait, dialogue box, choices, and subdued controls.
- Keep text legible over every background.
- Maintain continuity: setting, pose, wardrobe, expression, mood, props, and intimacy state.
- Handle generation boundaries diegetically when possible: “composing the scene.”
- Cache recent assets; avoid repeated image decode or layout thrash.
- Allow return to chat without losing context.

## Memory, Journal, and Growth UI

Default language should be emotional and understandable: “memories,” “journal,” “growth,” “learning.” Advanced views can expose embeddings, datasets, adapters, and logs.

Requirements:

- Search, filters, timeline/grouped views, and provenance details.
- Approve/reject/edit/delete/rollback controls for growth-affecting artifacts.
- Clear privacy/training eligibility badges.
- Undo or confirmation for destructive actions.
- Virtualized lists and lazy-loaded details.
- Never surprise users with permanent learning.

## Character Editor

Group fields into:

- identity and presentation,
- voice and dialogue examples,
- emotional traits and relationship dynamics,
- boundaries and preferences,
- appearance/visual assets,
- lore/world links,
- memory and growth settings,
- advanced prompt/model settings.

Protect continuity:

- Warn when edits conflict with memories, journals, or training adapters.
- Support drafts, duplicate, version history, restore, and import preview.
- Keep advanced prompt fields available but not dominant.

## Job and Resource Panels

For embeddings, reflection, media, training, imports, and exports:

- Show queued/running/paused/completed/failed/canceled states.
- Include cancel/pause/resume where supported.
- Explain when chat has priority over background GPU work.
- Provide quality tiers with rough time/VRAM hints.
- Keep raw logs behind expandable details.

## Tauri Command Client Template

```ts
import { invoke } from '@tauri-apps/api/core';

export async function callCommand<TInput, TOutput>(
  command: string,
  payload: TInput,
): Promise<TOutput> {
  return invoke<TOutput>(command, payload as Record<string, unknown>);
}
```

Validate payloads at the edge when schemas exist; surface errors through a consistent notification/toast pattern.

## Testing Checklist

- [ ] Keyboard navigation and focus states.
- [ ] Reduced motion path.
- [ ] Long chat virtualization and streaming performance.
- [ ] Empty/loading/error/offline states.
- [ ] Memory/journal delete and rollback flows.
- [ ] Tauri command error handling.
- [ ] Job cancel/pause/resume UI.
