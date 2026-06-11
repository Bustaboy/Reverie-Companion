# 8GB VRAM Optimization Skill

**Applies to**: Performance-sensitive backend, UI, model-serving, training, embedding, retrieval, media-generation, and ComfyUI work.

Use this skill whenever a change can affect GPU memory, latency, throughput, responsiveness, model selection, generation quality, training jobs, embedding pipelines, image/video workflows, or long-running background tasks. Assume the baseline target is an RTX 4070 laptop GPU with 8GB VRAM unless a task explicitly states otherwise.

---

## Core Principle

Design for smooth local-first operation under tight GPU memory pressure. A feature is not complete until it has an explicit plan for:

- Peak VRAM use.
- Steady-state VRAM use.
- CPU RAM fallback behavior.
- UI responsiveness during heavy work.
- Cleanup after model, training, embedding, or ComfyUI jobs.
- Graceful degradation when the 8GB budget is not enough.

Prefer predictable, bounded resource usage over maximum quality or raw throughput.

---

## Hardware Constraints

Treat 8GB VRAM as a hard product constraint, not an optional optimization target.

### Required Targets

- Keep normal interactive operation below **7.5GB VRAM**.
- Leave **300-500MB VRAM headroom** for driver overhead, desktop compositor usage, CUDA kernels, fragmentation, and short spikes.
- Avoid loading multiple large GPU models at the same time unless their combined peak memory has been measured and budgeted.
- Prefer fast model swaps, unload/reload flows, and queued execution over permanent residency of every model.
- Never assume desktop-class sustained clocks, power limits, or thermals; laptop GPUs can throttle during long generation or training sessions.

### Design Assumptions

- Users may run the app alongside a browser, Discord, OBS, media players, or another local AI process.
- Available VRAM can change while the app is running.
- Windows, Linux, and driver versions can report memory differently.
- Fragmentation can cause allocation failures even when reported free VRAM appears sufficient.

---

## VRAM Budgeting

Every performance-sensitive feature should document or encode a resource budget.

### Budget Categories

Track these categories separately where possible:

1. **Base runtime overhead**: Python process, CUDA context, framework allocations, kernels.
2. **Primary language model**: Weights, KV cache, activations, tokenizer/runtime buffers.
3. **Embedding model**: Weights, batch buffers, vectorization queues.
4. **Reranker or classifier models**: Any auxiliary model loaded for retrieval or filtering.
5. **Image/video/ComfyUI models**: Checkpoints, VAEs, CLIP/text encoders, ControlNet, LoRA, upscalers.
6. **Training jobs**: Base model, optimizer states, gradients, LoRA adapters, batches, validation pass.
7. **Transient buffers**: Prompt processing spikes, image tensors, latent buffers, preview renders, audio/video frames.
8. **Safety headroom**: Reserved memory for fragmentation and OS/driver overhead.

### Budget Rules

- Define a peak budget before adding a model or batch process.
- Prefer explicit batch limits over dynamically growing queues.
- Use sequential pipelines when parallel execution would exceed the budget.
- Treat KV cache growth as a first-class VRAM consumer during long conversations.
- Add guardrails that refuse, defer, downscale, unload, or queue work before CUDA out-of-memory occurs.
- Log model load/unload events, selected quantization, estimated VRAM, and actual observed memory when available.

---

## Quantization Guidance

Quantization is the default strategy for fitting capable models into 8GB VRAM.

### Language Models

- Prefer **4-bit quantized models** for primary local chat on 8GB VRAM.
- Use **5-bit or 6-bit quantization** only when measured memory leaves enough headroom for the required context length and auxiliary models.
- Avoid FP16/BF16 full-weight LLM inference on 8GB unless the model is very small and the total budget is proven safe.
- Expose quantization as configuration, but choose conservative defaults.
- Tune context length, batch size, and KV cache precision together; quantized weights do not eliminate KV cache pressure.

### Embedding and Reranking Models

- Prefer small, fast embedding models with predictable memory use.
- Keep embedding models on CPU by default if GPU residency would interfere with chat or generation responsiveness.
- Batch embeddings conservatively; use queue-based processing instead of large one-shot batches.
- Allow GPU acceleration for embeddings only when the main model is idle or after reserving enough VRAM headroom.

### Image, Video, and ComfyUI Models

- Prefer memory-efficient checkpoints and workflows designed for 8GB cards.
- Use quantized, pruned, tiled, or low-VRAM variants when available.
- Avoid keeping large image/video models resident while chat inference is active unless explicitly budgeted.
- Prefer lower resolution, lower batch count, tiled VAE decode, CPU offload, attention slicing, and xformers/SDPA-style memory-efficient attention where supported.
- Treat upscalers, ControlNet, IP-Adapter, AnimateDiff/video nodes, and multiple LoRAs as significant memory additions.

### Training and Fine-Tuning

- Prefer LoRA/QLoRA-style training over full fine-tuning.
- Use low-rank adapters, small batch sizes, gradient accumulation, mixed precision, checkpointing, and optimizer memory savings.
- Never start training while interactive generation is using the GPU unless the scheduler has explicitly paused/unloaded the conflicting workload.
- Save intermediate artifacts often enough to survive cancellation or OOM without losing all progress.

---

## Model Lifecycle Rules

Models must have explicit lifecycle ownership.

### Load Rules

- Load models lazily, close to first use.
- Validate available VRAM before loading.
- Prefer a single owner/service responsible for model residency and eviction.
- Avoid hidden global model instances that cannot be unloaded.
- Record which component requested each model and why it remains loaded.

### Unload Rules

- Unload models when they are idle and another high-priority workload needs VRAM.
- Release references, clear framework caches when appropriate, and verify memory drops where possible.
- Use cooldowns to avoid thrashing when a model is needed repeatedly.
- Provide cancellation points for long-running jobs so unload requests do not wait indefinitely.

### Eviction Priority

When memory pressure rises, unload or move resources in this order unless the current user task requires otherwise:

1. Preview, cache, and temporary tensors.
2. Idle upscalers, VAEs, ControlNet, adapters, and ComfyUI nodes.
3. Idle embedding/reranker models.
4. Idle training state or paused training workers.
5. Idle image/video generation model.
6. Secondary language model.
7. Primary interactive chat model last.

---

## Background Job Scheduling

Long-running GPU work must go through a scheduler instead of competing directly for VRAM.

### Job Types

Schedule and prioritize:

- Chat inference.
- Memory summarization and reflection.
- Embedding generation and re-indexing.
- Reranking and retrieval enrichment.
- Image generation and ComfyUI workflows.
- Video generation, frame interpolation, and upscaling.
- LoRA training and validation.
- Model downloads, conversions, quantization, and cache warming.

### Priority Rules

- User-visible interactive chat and UI actions have highest priority.
- Background memory, embedding, and reflection tasks must yield to active interaction.
- Training, batch media generation, and re-indexing should run only when the system is idle or when the user explicitly starts them.
- Use backpressure: bounded queues, rate limits, and cancellation rather than unlimited task accumulation.
- Persist job state so the app can resume or explain interrupted work after restart.

### Scheduling Patterns

- Use one GPU-heavy job at a time by default on 8GB systems.
- Allow CPU-only jobs to continue if they do not degrade UI responsiveness.
- Split large jobs into resumable chunks.
- Check memory and thermal/latency signals between chunks.
- Provide progress, estimated time, pause, resume, and cancel controls for long jobs.

---

## Context Management

Long context is valuable, but unbounded context will consume VRAM and degrade latency.

### Conversation Context

- Keep active prompt context bounded by a configurable token budget.
- Summarize older turns into memory layers instead of expanding the live context indefinitely.
- Retrieve only the most relevant memories for the current turn.
- Prefer compact, information-dense memory snippets over raw transcript stuffing.
- Monitor KV cache size and generation latency as context grows.

### Retrieval Context

- Cap the number and length of retrieved memories.
- Deduplicate overlapping memories before insertion.
- Prefer staged retrieval: cheap lexical/vector search first, rerank only a small candidate set.
- Run embeddings and reranking in background queues where possible.
- Use CPU fallback for retrieval models if GPU contention would hurt chat responsiveness.

### ComfyUI and Media Context

- Keep workflow graphs minimal for the requested output.
- Avoid carrying unnecessary high-resolution tensors between nodes.
- Use previews and lower-resolution drafts before expensive final renders.
- Clear workflow caches after completion when they are not needed for immediate iteration.

---

## UI Responsiveness

The UI must remain responsive even when GPU jobs are slow.

### Required Patterns

- Never block the UI thread on model loading, inference, training, embedding, or ComfyUI execution.
- Show explicit loading, queued, running, paused, and cancelling states.
- Stream chat tokens or progress updates whenever possible.
- Surface memory-pressure messages in user-friendly language.
- Allow users to cancel heavy jobs without restarting the app.
- Keep optimistic UI updates reversible if the backend job fails.

### Latency Expectations

- Prefer immediate acknowledgement over silent waiting.
- If model loading or generation may take more than a few seconds, show progress or staged status updates.
- Debounce UI actions that could enqueue duplicate GPU jobs.
- Disable or explain controls that cannot run under the current memory budget.

---

## Graceful Degradation Patterns

When resources are insufficient, degrade quality or defer work instead of crashing.

### Degradation Ladder

Apply one or more of these steps before failing:

1. Reduce batch size.
2. Shorten max generation tokens.
3. Reduce live context length.
4. Lower image/video resolution.
5. Lower image/video step count.
6. Disable high-cost extensions such as ControlNet, upscalers, video interpolation, or extra LoRAs.
7. Move embedding/reranking to CPU.
8. Unload idle models or adapters.
9. Queue the job until the active model is idle.
10. Ask the user to choose between quality and speed/memory profiles.

### Failure Behavior

- Catch expected OOM and allocation failures at job boundaries.
- Clean up partial state after failure.
- Preserve user input, job configuration, and recoverable intermediate outputs.
- Explain what was reduced, retried, queued, or skipped.
- Offer actionable next steps such as lower resolution, shorter context, fewer LoRAs, or retry after another job finishes.

---

## Backend Implementation Checklist

For backend changes, verify:

- Model load/unload paths are explicit and testable.
- GPU-heavy functions are cancellable or chunked.
- Queues have bounded length and clear priority.
- Memory estimates are checked before starting jobs.
- OOM handling releases resources and reports a useful error.
- Metrics/logs include model name, quantization, context size, batch size, and observed memory where available.
- CPU fallback exists for non-interactive or background work when practical.

---

## UI Implementation Checklist

For UI changes, verify:

- Heavy operations are asynchronous.
- The user can see job status and progress.
- The user can cancel, pause, or defer long jobs where appropriate.
- Controls communicate why a high-cost option is disabled or risky.
- Quality/performance presets are clear and reversible.
- The UI does not encourage launching multiple conflicting GPU jobs accidentally.

---

## Model, Training, and Embedding Checklist

For model pipeline changes, verify:

- Quantization and precision choices fit the 8GB target.
- Context length, batch size, and cache settings are bounded.
- Training uses LoRA/QLoRA-style methods unless a larger budget is explicitly available.
- Embedding and indexing jobs are incremental and resumable.
- Validation jobs do not secretly double memory use by loading extra models.
- Artifacts are saved in formats that do not require full reloads for simple inspection.

---

## ComfyUI Checklist

For ComfyUI or media generation work, verify:

- Workflows have an 8GB-safe default profile.
- High-cost nodes are optional and clearly labeled.
- Resolution, batch count, steps, VAE mode, and adapter count are budgeted.
- Chat/model-serving workloads are paused, unloaded, or scheduled around heavy media generation.
- Preview generation is cheaper than final generation.
- Failed jobs clean up temporary tensors and partial outputs.

---

## Default Recommendation

When uncertain, choose the safer 8GB profile:

- 4-bit LLM inference.
- Conservative context length.
- CPU or idle-time embeddings.
- One GPU-heavy job at a time.
- Low-VRAM ComfyUI workflow defaults.
- LoRA/QLoRA training only when the scheduler can reserve the GPU.
- Explicit progress, cancellation, and recovery paths.

A slower but stable app is preferable to a faster app that crashes, freezes, or silently evicts the user's active experience.
