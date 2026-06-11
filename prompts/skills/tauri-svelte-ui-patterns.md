# Skill: Tauri + Svelte UI Patterns

**Applies to**: Reverie desktop UI, Svelte components/stores, Tauri commands/events, chat, streaming, Visual Novel mode, memory browser, journal/growth dashboard, character editors, settings, and job progress.

Use this skill whenever work changes the user-facing desktop experience.

---

## 1. Mission

Reverie's UI should feel warm, premium, intimate, and trustworthy while remaining fast on local 8GB systems. The interface should make the companion feel alive without hiding the user's control over memory, reflection, training, and privacy.

Default priority order:

1. Emotional clarity and character continuity.
2. User trust and local-first transparency.
3. Responsiveness under local AI workloads.
4. Accessibility and readability.
5. Visual richness within budget.

---

## 2. Visual Language

Design dark mode first with a soft premium feel.

- Use warm near-black backgrounds, layered cards, subtle borders, and restrained accent gradients.
- Prefer readable spacing over dense dashboards.
- Use motion sparingly: soft fades, gentle presence pulses, smooth panel transitions.
- Avoid heavy blur, particles, animated backgrounds, and constant glow on modest laptops.
- Reserve saturated color for important emotional or operational states.
- Keep NSFW-capable UI tasteful, character-centered, and not noisy.

Suggested tone:

- “Remembering…” not “RAG hit.”
- “Reflecting on what mattered” not “Running extraction pipeline.”
- “Needs your review” not “Policy gate failed.”

Advanced views may expose raw IDs, scores, logs, and schemas.

---

## 3. Component Organization

Keep visual components small and business logic in stores/services.

```text
src/lib/components/chat/
  ChatShell.svelte
  MessageList.svelte
  MessageBubble.svelte
  MessageComposer.svelte
  StreamingMessage.svelte
  MemoryPeek.svelte

src/lib/components/journal/
  JournalTimeline.svelte
  JournalEntryCard.svelte
  PromotionReviewPanel.svelte

src/lib/components/memory/
  MemoryBrowser.svelte
  MemoryCard.svelte
  MemoryProvenanceDrawer.svelte

src/lib/components/jobs/
  JobProgressToast.svelte
  JobProgressPanel.svelte

src/lib/stores/
  chatStore.ts
  memoryStore.ts
  journalStore.ts
  jobStore.ts
  uiStore.ts
```

Rules:

- Components render; stores coordinate; API clients communicate.
- Keep domain state separate from UI state.
- Keep large payloads out of global stores unless normalized.
- Lazy-load heavy panels such as memory browser, gallery, and growth dashboard.

---

## 4. Store Patterns

Use normalized state for large or long-lived collections.

```ts
type EntityState<T> = {
  byId: Record<string, T>;
  orderedIds: string[];
  loading: boolean;
  error?: AppError;
  cursor?: string;
};
```

Separate stores by domain:

- `chatStore`: active conversation, streaming state, draft, branch, retry/cancel.
- `memoryStore`: search results, selected memory, provenance, edit/delete state.
- `journalStore`: entries, promotion review, rollback status.
- `jobStore`: background jobs, progress events, resource locks.
- `uiStore`: panels, tabs, modals, reduced motion, density.

Rules:

- Use derived stores for view models.
- Avoid repeated filtering/sorting in templates.
- Debounce search and editor validation.
- Store message IDs and summaries; load full details on demand.

---

## 5. Tauri Boundary

Keep the frontend/backend contract explicit.

- Wrap Tauri commands/events in typed client modules.
- Do not call `invoke` from deeply nested components.
- Use event subscriptions for streaming tokens and job progress.
- Unsubscribe on component destroy.
- Validate payloads at boundaries when practical.
- Handle backend restarts and reconnects gracefully.

Example client pattern:

```ts
export async function searchMemories(input: MemorySearchRequest): Promise<MemorySearchResponse> {
  return invoke<MemorySearchResponse>('memory_search', { input });
}
```

---

## 6. Chat UI

Chat is the emotional center of Reverie.

Requirements:

- Preserve draft text, scroll position, and active branch across navigation.
- Show companion presence without crowding reading space.
- Stream tokens smoothly without re-rendering the whole transcript.
- Keep retry, edit, regenerate, branch, pin, and delete actions discoverable but not cluttered.
- Distinguish user, companion, narration, memory notice, reflection notice, and system/job messages.
- Treat cancellation as normal and reversible.

Streaming pattern:

- Append incoming tokens to a dedicated `StreamingMessage` state.
- Commit final message to normalized history when complete.
- Batch UI updates if token events are too frequent.
- Keep auto-scroll opt-in when the user has scrolled away.

---

## 7. Memory Peek and Trust UI

When memory influences a response, show it gently.

```text
Remembering: your slow-burn pacing preference, the lighthouse promise, her apology from last night.
```

User controls should include:

- inspect why this memory was used,
- hide for this chat,
- edit,
- delete/forget,
- pin/protect,
- mark “do not learn from this.”

Do not show raw similarity scores in default mode. Show source IDs and extractor details in advanced/provenance views.

---

## 8. Journal and Growth UI

Growth should feel meaningful, not mechanical.

Journal timeline:

- cards for reflections, milestones, repairs, and learned preferences,
- source conversation links,
- promotion status,
- sensitivity/privacy labels,
- rollback affordances.

Promotion review:

- show proposed memory/state change,
- show evidence snippets sparingly,
- explain why review is needed,
- allow approve, edit, reject, delete source, or mark private.

Growth dashboard:

- separate emotional growth from technical training jobs,
- show adapter/dataset controls only in advanced mode,
- use calm copy and clear consequences.

---

## 9. Visual Novel Mode

VN mode should be immersive but lightweight.

- Use a scene canvas/background, character layer, dialogue panel, and choices.
- Keep text legible over all backgrounds.
- Cache recent assets and avoid re-decoding large images.
- Align mood, expression, pose, wardrobe, background, and dialogue tone.
- Make generation/loading states diegetic where possible: “composing the scene.”
- Preserve ability to return to chat without losing scene state.

---

## 10. Character Editor

Character editing must protect stable identity while making creation enjoyable.

- Separate stable identity, lore, voice, examples, NSFW canon, and mutable relationship state.
- Show warnings for edits that affect continuity.
- Validate adult status before NSFW sections are enabled.
- Provide import preview and field mapping for character cards.
- Preserve unknown import fields for round-trip export.
- Offer voice example tests from inside the editor.

---

## 11. Performance Rules

The UI must remain smooth while local inference runs.

- Virtualize transcripts, memory lists, journal timelines, job logs, and galleries.
- Lazy-load heavy routes and panels.
- Avoid main-thread JSON parsing of huge exports/imports.
- Use workers for expensive client-side transforms if needed.
- Debounce search, resize, filters, and validation.
- Use CSS transforms/opacity for animations.
- Respect `prefers-reduced-motion`.
- Avoid aggressive polling; use events or low-frequency refresh.
- Cap concurrent thumbnails/previews.

---

## 12. Error and Empty States

Errors should preserve trust.

Good error copy:

```text
Memory indexing paused to keep the chat responsive. Nothing was lost; Reverie will continue when the current generation finishes.
```

Rules:

- Explain what happened, what is safe, and what the user can do.
- Avoid dumping stack traces in default UI.
- Provide retry/cancel/details actions.
- Use technical details in collapsible advanced sections.

---

## 13. Accessibility

- Maintain readable contrast in dark mode.
- Support keyboard navigation for chat, modals, lists, and editors.
- Use semantic buttons/inputs and labels.
- Keep focus management correct when panels open/close.
- Do not rely on color alone for status.
- Respect reduced motion and text scaling.

---

## 14. Testing Checklist

- Streaming a long response does not re-render the whole transcript.
- Memory browser handles thousands of entries with virtualization.
- Journal rollback UI shows source and consequence clearly.
- Tauri event subscriptions clean up on navigation.
- Backend disconnect/reconnect does not lose draft text.
- Reduced-motion mode disables nonessential animation.
- Keyboard-only user can send, edit, retry, inspect memory, and cancel jobs.
- UI remains responsive during simulated indexing/media/training job events.

---

## 15. Anti-Patterns

- Raw `invoke` calls scattered across components.
- One global store containing every message, memory, journal, and job payload.
- Token streaming that invalidates the entire app tree.
- Debug language in intimate UI moments.
- Beautiful effects that steal GPU/CPU from inference.
- Memory controls hidden so deeply that users cannot trust learning.
