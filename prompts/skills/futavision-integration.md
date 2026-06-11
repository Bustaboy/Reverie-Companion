# Futa-Vision Integration Skill

**Use for**: optional ComfyUI/Futa-Vision bridges, image/video scene requests, visual metadata, media jobs, imports, progress events, prompt mapping, galleries, availability checks, and GPU scheduling.

## North Star

Futa-Vision should extend Reverie's alive characters into coherent visuals without becoming a required backend. Media generation is optional, asynchronous, local-first, and subordinate to chat continuity and 8GB responsiveness.

## Non-Negotiables

- Chat, memory, character management, and growth must work without Futa-Vision/ComfyUI installed.
- Media jobs never block chat streaming or durable memory writes.
- Use structured scene metadata first; generate prompts from metadata, not prompt blobs.
- Keep NSFW/futa/slime physical continuity consistent with character body facts, consent style, scene state, and relationship context.
- Route GPU work through the resource scheduler; default to 8GB-safe workflows.
- Store media provenance, prompts/metadata, model/workflow IDs, seeds, and deletion links.

## Integration Boundary

```text
Reverie scene/media request
→ MediaService
→ ResourceScheduler
→ FutaVisionAdapter / ComfyUIAdapter (optional)
→ job progress events
→ local asset store + metadata
→ UI gallery/VN/chat attachment
```

The adapter owns ComfyUI protocol details. Domain services own character, scene, and privacy rules.

## Scene Request Schema

```json
{
  "id": "scene_req_...",
  "character_id": "...",
  "conversation_id": "...",
  "mode": "portrait|scene|vn_background|sprite|short_video",
  "intent": "capture current emotional beat",
  "character_state": {
    "expression": "soft teasing smile",
    "pose": "leaning against the doorway",
    "wardrobe": "...",
    "body_facts": ["..."]
  },
  "scene_state": {
    "location": "...",
    "lighting": "...",
    "props": ["..."],
    "intimacy_level": "..."
  },
  "style": {"preset": "warm premium anime-real", "quality": "balanced"},
  "constraints": ["preserve horns", "no extra limbs"],
  "negative_constraints": ["identity drift", "wrong anatomy"],
  "seed": null,
  "privacy": {"local_only": true, "training_eligible": false}
}
```

## Job Lifecycle

Statuses:

```text
queued → preparing → generating → postprocessing → completed
queued/running → paused_for_chat | canceled | failed
```

Requirements:

- Progress events for UI.
- Cancel button and cleanup of partial files.
- Retry with same seed/workflow when possible.
- Pause or downshift when chat needs VRAM.
- Clear unavailable state when ComfyUI/Futa-Vision is missing.

## Prompt Mapping Rules

- Start from character stable identity and visual facts.
- Add current scene state, mood, pose, wardrobe, expression, and relationship tone.
- Add style preset and workflow-specific tokens last.
- Keep negative prompts targeted: anatomy errors, identity drift, unwanted style artifacts.
- Never let generated media metadata rewrite character identity or memory without review.
- For adult scenes, preserve emotional stakes and continuity; avoid mechanical tag soup as the only representation.

## 8GB Defaults

- Batch size 1.
- Conservative resolution presets with optional upscaling as a second job.
- Unload or pause chat model before heavy diffusion/video if scheduler requires it.
- Use tiled VAE, attention slicing, CPU offload, and low-VRAM workflows when available.
- Avoid video/AnimateDiff defaults on 8GB unless explicitly queued with warnings.
- Cache workflow availability, not large model weights inside Reverie.

## UI Requirements

- Media panel shows optional provider status: not installed, disconnected, ready, busy, failed.
- Quality tiers: Fast / Balanced / High with rough time/VRAM notes.
- Attach generated images to chat/VN without breaking conversation flow.
- Allow regenerate, reuse seed, edit scene metadata, delete, export, and mark private.
- Hide technical ComfyUI graph complexity in default mode; advanced users can inspect workflow details.

## Metadata to Store

- Character/conversation/message links.
- Scene request JSON and derived prompt/negative prompt.
- Workflow ID/version, model/checkpoint names, LoRA/control inputs, seed, dimensions, duration.
- Job timestamps, status, errors, and resource estimates.
- Local file path/content hash and deletion dependencies.
- Whether asset is eligible for future training/reference use.

## Test Cases

- App works when ComfyUI is absent.
- Media job queues while chat is generating and resumes afterward.
- Cancel removes partial files and updates job state.
- Generated prompt preserves character body facts and scene continuity.
- Deleted character/conversation cascades or detaches media according to policy.
- 8GB-safe defaults avoid concurrent diffusion and chat residency.
