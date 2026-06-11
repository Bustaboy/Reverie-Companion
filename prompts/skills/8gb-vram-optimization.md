# 8GB VRAM Optimization Skill

**Use for**: model loading, inference, embeddings, reranking, queues, media generation, ComfyUI/Futa-Vision, training, long context, streaming, caching, or any change that can affect GPU/CPU/RAM, latency, thermals, or responsiveness.

## North Star

Reverie must feel smooth and intimate on an RTX 4070 laptop GPU with **8GB VRAM**. A feature is not done until it has bounded peak memory, graceful fallback, and cleanup.

Default priority: **chat responsiveness > continuity > quality tier > throughput > visual fidelity**.

## Hard Targets

- Keep normal interactive operation below **7.5GB VRAM**; reserve 300-500MB for driver/compositor/CUDA spikes.
- Never run chat inference, embeddings, media generation, and training concurrently on GPU unless explicitly budgeted.
- Prefer queueing, unloading, CPU fallback, lower tiers, or user-visible deferral over CUDA OOM.
- Assume laptop thermals, variable clocks, fragmented VRAM, and other apps competing for memory.
- Make resource settings configurable; do not hardcode model paths, batch sizes, or quality tiers.

## Budget Before You Build

Track these buckets separately:

1. Runtime overhead: Python/Tauri process, CUDA context, kernels.
2. LLM weights: quantized model, tokenizer/runtime buffers.
3. KV cache: grows with context length, batch size, and concurrency.
4. Embeddings/rerankers/classifiers.
5. ComfyUI/image/video: checkpoint, VAE, text encoders, ControlNet/IP-Adapter/LoRA/upscalers/video nodes.
6. Training: base model, optimizer, gradients, adapters, batches, validation.
7. Transients: latents, previews, audio/video frames, prompt spikes.
8. Headroom: fragmentation and OS/driver variance.

Document estimated **steady**, **peak**, and **fallback** behavior for new heavy features.

## Model Lifecycle Rules

- Load lazily, close to first use.
- Use one owner/service for residency state.
- Validate budget before load; refuse or defer before OOM.
- Stream outputs and release transient tensors promptly.
- Unload optional models after idle timeout or mode switch.
- Expose model state to UI: unavailable, loading, ready, busy, unloading, failed.
- Log load/unload, quantization, context length, batch size, and observed memory when available.

## Defaults by Workload

### Chat LLM

- Prefer 4-bit local models for 8GB.
- Use 5/6-bit only when measured KV cache and auxiliary workloads fit.
- Avoid FP16/BF16 full-weight inference except for small models with proven budget.
- Bound context length and concurrent generations.
- Treat KV cache as a first-class budget item; summarize/retrieve instead of endless context growth.

### Embeddings and Reranking

- CPU by default unless chat is idle and GPU budget is reserved.
- Small embedding models, bounded batches, resumable queues.
- Debounce indexing from UI edits and conversation bursts.
- Never block response streaming on embedding writes.

### Media / Futa-Vision / ComfyUI

- Optional, asynchronous, and unloadable.
- Use low-VRAM workflows: lower resolution, batch size 1, tiled VAE, attention slicing, CPU offload, SDPA/xformers where supported.
- Do not keep diffusion/video models resident during chat unless measured safe.
- Prefer previews and progressive quality tiers over blocking high-res output.

### Training / Adapters

- Prefer LoRA/QLoRA; never full fine-tune by default.
- Require user approval, local data provenance, and scheduler ownership.
- Use small batches, gradient accumulation, checkpointing, mixed precision, optimizer memory savings.
- Pause/unload conflicting inference/media workloads before training.
- Save intermediate artifacts so cancellation/OOM does not lose all progress.

## Scheduler Pattern

Use a central resource scheduler for expensive work.

```text
Request(job_type, priority, estimated_vram, can_run_on_cpu, cancelable)
→ admit if within budget
→ otherwise queue, downshift quality, ask user, or fail gracefully
→ emit progress/events
→ cleanup and update observed budget
```

Suggested priority:

1. Active chat generation.
2. UI-critical retrieval already needed for current response.
3. User-started media preview.
4. Memory indexing/reflection.
5. Training/export/bulk jobs.
6. Upscale/video/background maintenance.

## UI Requirements

- Show calm states: queued, preparing, generating, cooling down, paused for chat, failed safely.
- Provide cancel/pause/resume for long jobs.
- Offer quality tiers: Fast / Balanced / High, with rough VRAM/time implications.
- Avoid technical panic; advanced panels can show raw VRAM and logs.
- Preserve drafts and chat flow during background work.

## Prompt Template: Resource Review

```text
For this change, provide:
- Workloads affected:
- Estimated steady VRAM/RAM:
- Estimated peak VRAM/RAM:
- Can it run while chat is active? Why?
- Queue/cancel/unload behavior:
- Quality fallback tiers:
- Metrics/logs to add:
- Tests or manual checks:
```

## Implementation Checklist

- [ ] Explicit memory/latency budget and fallback path.
- [ ] Bounded batches, queues, context length, and concurrency.
- [ ] Lazy load/unload with cleanup hooks.
- [ ] Chat streaming remains responsive.
- [ ] Optional GPU work is cancelable and observable.
- [ ] Defaults fit 8GB; higher tiers are opt-in.
- [ ] Tests or manual checks cover queueing, cancellation, and OOM-safe refusal.

## Avoid

- Global model singletons with unclear ownership.
- Background GPU work starting without scheduler approval.
- Unbounded queues, image batches, embedding batches, or context windows.
- Silent quality degradation with no UI explanation.
- Keeping ComfyUI/video/training models warm “just in case.”
