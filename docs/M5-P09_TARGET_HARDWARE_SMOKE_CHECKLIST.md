# M5-P09 Target-Hardware Smoke Checklist — RTX 4070 8GB Mobile

**Status:** Pending for M8 productization unless run on actual RTX 4070 8GB mobile or equivalent hardware. This repository environment does not expose the target GPU, TTS stack, ComfyUI stack, or packaged Tauri runtime, so these checks are not marked as passed here.

**M5-P11 closure note (June 13, 2026):** deterministic backend/frontend verification passed for capture metadata, feedback/review flows, visual memory scoping, retry/cancel metadata preservation, low/unknown VRAM fallback, and non-blocking queue contracts. This checklist remains **Pending M8-P09** for real packaged target-hardware execution with local TTS and ComfyUI available.

## Target machine

- GPU: RTX 4070 laptop GPU, 8GB VRAM, or equivalent 8GB NVIDIA mobile GPU.
- ComfyUI: launched separately with `--lowvram` and the configured Flux Schnell preview workflow.
- Reverie: packaged desktop build preferred; dev mode acceptable only if explicitly noted.
- TTS: Orpheus-CPP primary path available with `REVERIE_TTS_ORPHEUS_CPP_N_GPU_LAYERS=0`; Piper fallback path available for standard local playback.

## Smoke checks

| Check | Expected result | Status | Evidence |
|---|---|---|---|
| Chat streaming while idle | Chat streams normally; no image/capture queue blocks active chat. | Pending M8 | Attach logs/screenshot. |
| TTS playback | TTS starts promptly and enters the coordinator priority section. | Pending M8 | Attach resource event or log. |
| Capture queued while TTS active | Moment Capture is queued/paused with user-visible “paused for voice” copy. | Pending M8 | Attach UI screenshot and job event. |
| Image waits/pauses/downgrades | Low/unknown VRAM produces preview preset and clear “waiting/downgraded” copy instead of OOM. | Pending M8 | Attach VRAM snapshot/job event. |
| Cancel works | Cancel stops/interrupts image work and preserves `capture_id`, `character_id`, `session_id`, and prompt hash in job state. | Pending M8 | Attach job JSON. |
| Retry works | Retry creates a new visible job with the same capture context; no hidden automatic retry loop. | Pending M8 | Attach original/new job JSON. |
| Gallery metadata remains intact | Completed captures keep capture/character metadata and safe debug/resource metadata. | Pending M8 | Attach gallery item JSON. |
| Chat is never blocked | User can send/receive chat while image/capture jobs are queued, waiting, failed, or cancelled. | Pending M8 | Attach transcript timing notes. |

## Notes for validation

- Do **not** mark this checklist passed without real target-hardware execution.
- If hardware is unavailable during M5, leave every row `Pending M8` and carry the validation forward to M8-P09.
- Record any deviations with exact GPU, driver, ComfyUI workflow, model preset, and Reverie build mode.
