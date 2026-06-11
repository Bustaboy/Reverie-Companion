# Futa-Vision Integration Skill

**Purpose**: Guide implementation of optional Futa-Vision integrations for Vision Companion while preserving clean boundaries, local-first behavior, and responsive companion interactions.

---

## Core Principle

Futa-Vision must remain **optional, decoupled, and non-blocking**.

Vision Companion should never require Futa-Vision to start, chat, render the core UI, update memory, or progress character state. If the Futa-Vision service, queue, models, or ComfyUI worker are unavailable, the application must gracefully continue with text and existing companion features.

---

## Integration Goals

- Provide a clean API surface for requesting generated visual scenes without coupling the companion core to ComfyUI internals.
- Preserve character continuity by sending structured state, relationship context, and scene metadata with every generation request.
- Keep generation asynchronous so chat, memory, and character growth remain responsive.
- Support progress updates and result events without requiring the UI or backend to poll aggressively.
- Make every integration point configurable, observable, and easy to disable.

---

## Clean API Boundaries

### Boundary Layers

1. **Companion Core**
   - Owns conversation state, memory retrieval, character state, consent/user preferences, and scene intent.
   - Emits high-level generation requests only.
   - Must not depend on ComfyUI graph formats, model filenames, LoRA paths, sampler settings, or video worker internals.

2. **Futa-Vision Adapter**
   - Translates companion-native requests into Futa-Vision job payloads.
   - Validates payloads, applies defaults, redacts unnecessary private data, and enforces user settings.
   - Handles queue submission, status mapping, progress subscriptions, cancellation, retries, and result normalization.

3. **Generation Queue**
   - Owns job lifecycle, ordering, concurrency, deduplication, persistence, and backpressure.
   - Exposes stable job status and progress events to the app.
   - Must be safe to disable or drain without impacting companion state.

4. **ComfyUI Worker**
   - Owns workflow execution and GPU-heavy rendering.
   - Accepts normalized jobs from the queue or adapter.
   - Reports progress, artifacts, errors, and resource pressure through a narrow worker protocol.

### Do Not Leak Internals

Avoid exposing these outside the Futa-Vision adapter/worker boundary:

- ComfyUI node IDs or graph implementation details.
- Local model path assumptions.
- Raw workflow JSON as a core application dependency.
- GPU scheduler implementation details.
- Worker-specific retry or checkpoint selection logic.

---

## Event Flow

Use event-driven integration rather than blocking request/response flows.

### Recommended Flow

1. **Trigger detected**
   - A user action, character moment, story beat, or manual command requests visual generation.

2. **Scene intent created**
   - Companion Core builds a high-level `SceneGenerationIntent` from current conversation, memory, and character state.

3. **Payload assembled**
   - Futa-Vision Adapter converts intent into a versioned `FutaVisionJobRequest`.

4. **Job enqueued**
   - Queue returns a `job_id` immediately.
   - Companion Core stores only the stable job reference and continues normal operation.

5. **Progress events emitted**
   - Queue/worker publishes status changes such as `queued`, `preparing`, `rendering`, `postprocessing`, `completed`, `failed`, or `cancelled`.

6. **Result normalized**
   - Adapter converts worker output into stable app-level artifact metadata.

7. **Continuity update considered**
   - Companion Core may record a memory/event summary after completion, but failed or cancelled jobs must not corrupt character continuity.

### Event Naming

Prefer explicit, versioned event names:

- `futavision.job.requested.v1`
- `futavision.job.queued.v1`
- `futavision.job.started.v1`
- `futavision.job.progress.v1`
- `futavision.job.completed.v1`
- `futavision.job.failed.v1`
- `futavision.job.cancelled.v1`

---

## Queueing Requirements

The generation queue must protect the companion experience from long-running or GPU-intensive work.

### Required Behavior

- Enqueue jobs asynchronously and return a stable `job_id` immediately.
- Support cancellation for queued and active jobs where the worker permits it.
- Track lifecycle timestamps: `requested_at`, `queued_at`, `started_at`, `finished_at`.
- Persist enough job metadata to recover visible status after app restart.
- Enforce configurable limits for queue depth, concurrent jobs, retries, and artifact retention.
- Deprioritize or pause generation when core companion performance is at risk.
- Never block chat response generation, memory writes, or core UI rendering.

### Backpressure

When resources are constrained:

- Reject new jobs with a clear recoverable error, or mark them as deferred.
- Notify the UI with an actionable status message.
- Avoid unbounded memory growth from queued prompts, images, or intermediate artifacts.
- Prefer dropping optional preview work over delaying core companion actions.

### Retry Policy

Retries should be conservative and explicit:

- Retry transient worker connection failures or recoverable queue errors.
- Do not repeatedly retry deterministic workflow validation failures.
- Include retry counts and last error summaries in job status.
- Keep retries non-blocking and cancellable.

---

## ComfyUI Worker Expectations

The ComfyUI worker is an external capability provider, not a core dependency.

### Worker Contract

A worker should provide:

- Health checks that report readiness, loaded workflow support, and coarse resource availability.
- A job submission endpoint or queue consumer that accepts normalized `FutaVisionJobRequest` payloads.
- Progress callbacks or status polling that can be adapted into app-level progress events.
- Artifact reporting with stable paths, media types, dimensions, duration, seed, and workflow metadata.
- Structured errors with machine-readable codes and user-safe messages.

### Resource Expectations

- Respect the target hardware profile and avoid starving the local LLM or companion UI.
- Make model loading lazy or configurable where possible.
- Expose resource pressure signals when VRAM, RAM, disk, or worker concurrency is constrained.
- Clean up intermediate files according to retention policy.

### Failure Expectations

The worker may be missing, offline, busy, incompatible, or out of memory. Each case must be treated as recoverable from the companion app perspective.

Required failure modes:

- `worker_unavailable`
- `workflow_unsupported`
- `invalid_payload`
- `resource_exhausted`
- `generation_timeout`
- `artifact_write_failed`
- `cancelled_by_user`

---

## Character State Payloads

Generation requests should carry enough structured character state to preserve identity and continuity without sending unnecessary private data.

### Recommended `character_state` Shape

```json
{
  "schema_version": "1.0",
  "character_id": "stable-character-id",
  "display_name": "Character Name",
  "identity_tags": ["core identity", "visual identity", "personality anchor"],
  "appearance": {
    "body_type": "short stable descriptor",
    "hair": "style/color descriptor",
    "eyes": "descriptor",
    "skin": "descriptor",
    "distinctive_features": ["stable visual detail"]
  },
  "wardrobe": {
    "current_outfit": "current outfit descriptor",
    "persistent_accessories": ["accessory"]
  },
  "personality": {
    "current_mood": "mood label",
    "emotional_tone": "tone descriptor",
    "relationship_stance": "relationship state descriptor"
  },
  "continuity": {
    "recent_events_summary": "brief relevant summary",
    "long_term_anchors": ["important continuity fact"],
    "do_not_contradict": ["hard continuity constraint"]
  }
}
```

### Payload Rules

- Use stable IDs instead of display names for references.
- Keep summaries concise and relevant to the requested scene.
- Separate durable traits from temporary mood, outfit, or scene details.
- Include negative continuity constraints when needed to prevent contradictions.
- Avoid dumping raw chat logs into generation payloads.

---

## Scene Metadata

Every request should include scene metadata that is independent of any specific renderer.

### Recommended `scene` Shape

```json
{
  "schema_version": "1.0",
  "scene_id": "stable-scene-id",
  "conversation_id": "conversation-id",
  "trigger_type": "manual",
  "intent": "portrait | scene | short_video | memory_recap | expression_update",
  "time_context": {
    "in_world_time": "optional story time",
    "real_requested_at": "ISO-8601 timestamp"
  },
  "setting": {
    "location": "scene location",
    "lighting": "lighting descriptor",
    "mood": "visual mood",
    "weather": "optional weather"
  },
  "composition": {
    "shot_type": "portrait | medium | full_body | cinematic",
    "camera_angle": "optional angle",
    "focus_subjects": ["character-id"]
  },
  "continuity_refs": {
    "previous_artifact_ids": ["artifact-id"],
    "related_memory_ids": ["memory-id"],
    "active_story_arc_ids": ["arc-id"]
  }
}
```

### Metadata Rules

- Metadata must be renderer-agnostic.
- Scene IDs should be stable for tracing and memory association.
- Avoid making generated artifacts authoritative until completion is confirmed.
- Store enough metadata to explain why a generation was requested later.

---

## Trigger Types

Supported triggers should be explicit and user-configurable.

### Recommended Trigger Types

- `manual`: User explicitly requests generation.
- `scene_transition`: Conversation enters a new location or visual state.
- `emotion_peak`: Character reaches a meaningful emotional moment.
- `relationship_milestone`: A durable relationship state changes.
- `memory_recap`: The app visualizes a remembered event.
- `idle_ambient`: Optional low-priority background generation.
- `expression_update`: Lightweight visual update for mood or pose.
- `developer_test`: Non-user-facing integration or workflow validation.

### Trigger Requirements

- Default to manual triggers unless the user enables automation.
- Make automated triggers rate-limited and easy to disable.
- Never let automatic visual generation interrupt or delay chat.
- Record trigger type with each job for auditability and tuning.

---

## Progress Updates

Progress should be useful to the UI while hiding worker complexity.

### Recommended Status Model

```json
{
  "job_id": "futavision-job-id",
  "status": "queued | preparing | rendering | postprocessing | completed | failed | cancelled",
  "progress_percent": 42,
  "stage_label": "Rendering frames",
  "eta_seconds": 120,
  "preview_artifact_id": "optional-preview-id",
  "retry_count": 0,
  "message": "Short user-safe status message"
}
```

### Progress Rules

- Treat progress as best-effort; do not require exact percentages.
- Prefer stage labels when exact progress is unknown.
- Debounce noisy worker updates before sending them to the UI.
- Include user-safe error messages and machine-readable error codes on failure.
- Keep progress subscriptions optional so clients can reconnect and fetch latest status.

---

## Continuity Requirements

Futa-Vision outputs must support character continuity instead of overriding it.

### Required Continuity Behavior

- Character memory and relationship state remain authoritative over generated artifacts.
- Generation prompts should be derived from current character state, not the other way around.
- Completed artifacts may become memory references only after validation or user acceptance when appropriate.
- Failed, cancelled, or partial generations should not create durable story facts.
- If a generated image or video contradicts established continuity, preserve the established continuity and mark the artifact as non-canonical or regenerate.

### Canonical vs. Non-Canonical Artifacts

Track artifact continuity status:

- `pending_review`: Generated but not yet accepted as part of continuity.
- `canonical`: Accepted and safe to reference in memory or future scenes.
- `non_canonical`: Kept as media but ignored for continuity.
- `discarded`: Removed or hidden according to retention settings.

---

## Optional Configuration

All Futa-Vision integration should be gated behind configuration.

Recommended settings:

- `futavision.enabled`
- `futavision.worker_url`
- `futavision.auto_triggers_enabled`
- `futavision.max_queue_depth`
- `futavision.max_concurrent_jobs`
- `futavision.default_timeout_seconds`
- `futavision.artifact_retention_days`
- `futavision.allow_background_generation`
- `futavision.pause_when_llm_busy`

Defaults should favor safety and responsiveness:

- Disabled unless configured or explicitly enabled.
- Manual triggers only.
- Low concurrency.
- Conservative timeouts.
- No required startup dependency on worker health.

---

## Implementation Checklist

Before merging Futa-Vision integration code, verify that:

- The app runs normally with Futa-Vision disabled.
- The app runs normally when the worker URL is missing or unreachable.
- Chat, memory writes, and UI updates continue while jobs are queued or rendering.
- Queue limits prevent unbounded resource usage.
- Job status can be recovered after restart.
- Progress and failure messages are user-safe.
- Payload schemas are versioned and validated.
- Character state is summarized rather than copied from raw chat logs.
- Generated artifacts do not automatically rewrite canonical memory.
- Automated triggers are opt-in, rate-limited, and cancellable.

---

## Anti-Patterns to Avoid

- Blocking a chat response while waiting for video generation.
- Importing ComfyUI-specific modules into Companion Core.
- Treating Futa-Vision as a required backend service.
- Storing raw workflow graphs as character memory.
- Allowing generated artifacts to silently override character identity.
- Retrying failed jobs indefinitely.
- Letting background generation consume resources needed by the LLM.
- Requiring cloud services for generation, queueing, or artifact storage.

---

## Summary

Futa-Vision should enhance immersion without weakening the companion architecture. Keep it behind stable interfaces, process work asynchronously, protect local resources, and preserve character continuity. The companion must remain fully usable when visual generation is disabled, unavailable, or busy.
