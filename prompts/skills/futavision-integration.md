# Skill: Futa-Vision Integration

**Applies to**: Optional ComfyUI/image/video bridges, scene-to-media requests, media job queues, progress events, asset metadata, availability checks, and future Futa-Vision interoperability.

Use this skill when Reverie needs to prepare for or integrate optional visual generation without coupling core chat, memory, or character systems to a specific media backend.

---

## 1. Mission

Futa-Vision should enhance Reverie's alive companion experience with optional visuals while staying cleanly decoupled from core chat. Media generation must respect character canon, scene continuity, user consent, local-first privacy, and 8GB resource limits.

Default priority order:

1. Character and scene continuity.
2. Local-first privacy and explicit user control.
3. Decoupled APIs and replaceable backends.
4. 8GB-safe scheduling.
5. Visual quality.

---

## 2. Decoupling Rules

- Core chat must work without Futa-Vision, ComfyUI, or any media backend installed.
- Media generation is an adapter behind a service interface, not a dependency of memory/chat/domain models.
- Store media metadata in Reverie-owned schemas; store backend-specific workflow data separately.
- Use capability checks instead of hard assumptions.
- Fail softly when unavailable: hide advanced controls or show setup guidance.
- Never let image/video generation mutate memory, journal, or character canon unless an explicit save action does so.

Interface shape:

```text
SceneMediaService
  check_capabilities()
  create_job(scene_request)
  cancel_job(job_id)
  get_job(job_id)
  list_assets(character_id, conversation_id?)
```

---

## 3. Scene Request Contract

Use structured scene requests, not raw prompt strings as the only source of truth.

```json
{
  "request_id": "media_req_...",
  "character_id": "char_...",
  "conversation_id": "conv_...",
  "scene_id": "scene_...",
  "mode": "image",
  "intent": "illustrate_current_scene",
  "character_canon": {
    "name": "",
    "adult": true,
    "body_facts": [],
    "nsfw_body_facts": [],
    "visual_anchors": []
  },
  "scene_state": {
    "location": "",
    "mood": "",
    "outfit": "",
    "pose": "",
    "lighting": "",
    "continuity_notes": []
  },
  "style": {
    "preset": "warm_cinematic",
    "negative_prompt_policy": "default",
    "reference_asset_ids": []
  },
  "safety": {
    "adult_content": true,
    "user_confirmed": true,
    "privacy": "local_only"
  },
  "resource_preset": "balanced_8gb"
}
```

Rules:

- Character adult status must be explicit for NSFW media.
- Scene state should come from current conversation/VN state, not broad memory dumps.
- Keep raw prompts generated from structured fields and traceable to the request.
- Do not include private unrelated memories in media prompts.

---

## 4. 8GB Resource Presets

Media generation often conflicts with chat inference. Be conservative.

| Preset | Behavior |
|---|---|
| `preview_8gb` | lower resolution, single image, no upscaler, fastest cleanup |
| `balanced_8gb` | moderate resolution, single image or tiny batch, optional lightweight refiner |
| `quality_manual` | user-confirmed, may unload chat model, longer runtime |
| `video_experimental` | explicit warning, exclusive lock, checkpoint/progress required |

Rules:

- Queue media jobs through the shared backend scheduler.
- Acquire an exclusive GPU lock unless measured safe.
- Pause idle memory indexing during media jobs.
- Unload the LLM if required and tell the user chat may pause.
- Release models/temp files after completion or cancellation.

---

## 5. Job Lifecycle and Events

Media jobs should be visible, cancelable, and recoverable.

Lifecycle:

1. `queued`
2. `checking_capabilities`
3. `preparing_prompt`
4. `waiting_for_gpu_lock`
5. `generating`
6. `postprocessing`
7. `saving_asset`
8. `completed` / `failed` / `cancelled`

Event example:

```json
{
  "event": "media.progress",
  "job_id": "job_...",
  "phase": "generating",
  "progress": 0.55,
  "message": "Composing the scene locally",
  "preview_asset_id": null
}
```

UI copy should be calm and diegetic when appropriate.

---

## 6. Asset Metadata

Store generated assets with enough metadata to preserve continuity and auditability.

```json
{
  "asset_id": "asset_...",
  "character_id": "char_...",
  "conversation_id": "conv_...",
  "scene_id": "scene_...",
  "created_at": "2026-06-11T22:00:00Z",
  "kind": "image",
  "file_path": "local://assets/...",
  "thumbnail_path": "local://thumbs/...",
  "request_id": "media_req_...",
  "backend": "comfyui",
  "workflow_version": "futa_vision_bridge.v1",
  "resource_preset": "balanced_8gb",
  "canon_snapshot": {
    "body_facts": [],
    "visual_anchors": []
  },
  "prompt_metadata": {
    "positive_hash": "...",
    "negative_hash": "...",
    "seed": 12345
  },
  "privacy": "local_only"
}
```

Do not store full sensitive prompts in normal logs unless the user enables debug capture.

---

## 7. Character and NSFW Continuity

For adult visual scenes:

- Preserve character adult status, anatomy, pronouns, body canon, and visual anchors.
- Preserve current outfit, pose, location, lighting, expression, and emotional tone when requested.
- Track temporary transformations or slime/futa-specific details as scene state unless explicitly saved to canon.
- Do not let generated media establish new canon automatically.
- If the model output conflicts with canon, mark the asset as non-canonical or let the user discard/regenerate.

Prompt-building should prioritize canonical body facts over generic tags.

---

## 8. Availability and Setup

Capability checks should be cheap and explicit.

Report:

- backend installed/reachable,
- supported modes: image/video/upscale/reference,
- available workflows/models,
- estimated resource tier,
- last error,
- version compatibility.

If unavailable, the UI should say:

```text
Visual generation is optional and not currently connected. Chat, memory, and growth still work normally. Connect a local Futa-Vision/ComfyUI backend in Settings when you want scene images.
```

---

## 9. Testing Checklist

- Reverie starts and chats normally with no media backend installed.
- Capability checks do not block startup.
- Media job queues, cancels, and releases GPU locks.
- Chat model is not forced to coexist with diffusion models under 8GB pressure.
- Asset metadata links to character/conversation/scene without mutating canon.
- NSFW media requests require adult character status and explicit user action.
- Failed backend connection returns a typed, user-safe error.
- Deleted/private conversations do not leak into media prompts or metadata.

---

## 10. Anti-Patterns

- Importing ComfyUI-specific objects into core chat or character modules.
- Treating generated images as canonical memories automatically.
- Running media generation concurrently with chat and hoping 8GB is enough.
- Storing raw sensitive prompts in logs by default.
- Blocking the entire app because optional media backend is unavailable.
- Building a prompt from all memories instead of current scene/canon.
