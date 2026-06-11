# Skill: 8GB VRAM Optimization

**Applies to**: Model serving, inference, embeddings, retrieval, reranking, training, ComfyUI/media generation, background jobs, desktop responsiveness, and any feature that can affect CPU/GPU/RAM/disk pressure.

Use this skill whenever work can change model residency, context length, batch sizes, queues, GPU memory, latency, startup time, or graceful degradation. Assume the baseline machine is an **RTX 4070 laptop GPU with 8GB VRAM** unless the task explicitly says otherwise.

---

## 1. Mission

Reverie must feel premium and alive on modest local hardware. A feature is not complete until it has a clear plan for peak memory, steady-state memory, cleanup, fallback behavior, and UI responsiveness during heavy work.

Default tradeoff order:

1. Stable character continuity.
2. Predictable local responsiveness.
3. Avoiding CUDA OOM and app crashes.
4. Quality within budget.
5. Throughput and optional visual fidelity.

---

## 2. Hard Targets

Treat 8GB VRAM as a product constraint, not a best-effort optimization.

- Keep normal interactive operation under **~7.5 GB VRAM**.
- Reserve **300-500 MB headroom** for driver/compositor overhead, kernels, fragmentation, and transient spikes.
- Avoid permanent residency for multiple large models.
- Queue or serialize heavyweight work instead of running chat, embeddings, training, and image generation together.
- Assume laptop thermals and power limits can throttle sustained jobs.
- Assume available VRAM changes while Reverie is running because users may have browsers, Discord, OBS, games, or another AI process open.

---

## 3. Resource Budget Template

Every feature that touches models or heavy jobs should document this budget in code comments, config, docs, or tests:

```yaml
feature: "memory embedding backfill"
interactive_required: false
primary_gpu_models: []
peak_vram_mb_estimate: 600
steady_vram_mb_estimate: 250
cpu_ram_mb_estimate: 1500
disk_temp_mb_estimate: 500
concurrency_limit: 1
fallbacks:
  - pause during active chat generation
  - reduce embedding batch size
  - run on CPU if GPU pressure is high
cleanup:
  - release model after idle timeout
  - clear CUDA cache after large batch
telemetry:
  - log start/end memory snapshots
  - log batch size and duration
```

---

## 4. Model Residency Rules

### Primary chat model

- Prefer 4-bit quantized models for 8GB interactive chat.
- 5-bit/6-bit or larger contexts are allowed only after measurement leaves headroom.
- Load one primary LLM at a time by default.
- Make context length configurable and bounded; long context increases KV cache and latency.
- Reuse model sessions for chat, but support explicit unload and idle unload.
- Log model name, quantization, context length, backend, load time, and observed memory.

### Auxiliary models

- Embedding, reranker, classifier, TTS, STT, and vision models should not silently remain on GPU forever.
- Prefer CPU or small GPU residency for embeddings unless measured GPU acceleration is worth the memory.
- Unload auxiliary GPU models before large image/video/training jobs.
- Use lazy loading and idle timeouts.

### Media/ComfyUI models

- Keep ComfyUI optional and decoupled.
- Do not assume chat model and diffusion model can coexist in VRAM.
- Prefer “pause chat generation → unload LLM if needed → run media job → reload LLM” over OOM-prone concurrency.
- Cap resolution, frame count, batch count, ControlNet count, and upscalers by preset.

---

## 5. RTX 4070 8GB Mobile Defaults

Start conservative. Let advanced users opt up after measurement.

| Area | Default | Escalate only if |
|---|---|---|
| LLM quantization | 4-bit | measured headroom supports 5/6-bit |
| Context length | 4k-8k for normal chat | user explicitly selects long context |
| Parallel LLM generations | 1 | batch mode with no active UI expectation |
| Embedding batch | small fixed batches | CPU/GPU memory remains stable |
| Reranking | top 20-50 candidates | latency remains acceptable |
| Image generation | queued, not concurrent with chat | LLM unloaded or enough headroom |
| Training | explicit user-started job | app warns and enters training mode |
| Background indexing | idle/low priority | no active generation or media job |

---

## 6. KV Cache and Context Management

KV cache is often the hidden reason long-running companion chat slows down or OOMs.

Rules:

- Treat context length as a memory budget item.
- Use memory/RAG summaries instead of unbounded transcript stuffing.
- Cap active conversation window and summarize older turns with provenance.
- Support context trimming that preserves:
  1. system/developer prompt,
  2. character stable identity,
  3. current user instruction,
  4. boundaries/promises,
  5. recent scene state,
  6. compact long-term memories.
- Expose long-context mode as a quality/performance tradeoff, not the default.
- Test long sessions, regeneration, retries, and branch switching for cache cleanup.

Prompt budget example:

```text
Normal 8GB chat budget:
- System/global instructions: fixed, compact
- Character identity: 400-900 tokens
- Active scene/recent summary: 300-700 tokens
- Retrieved memories: 300-900 tokens
- Recent turns: remaining budget
- Response allowance: configured max tokens
```

---

## 7. Embeddings and Retrieval Jobs

Embeddings should improve memory without making chat feel sluggish.

- Queue embedding writes and backfills.
- Pause or throttle embedding jobs during active generation, media generation, or training.
- Use bounded batches; never let backlog size dictate batch size.
- Prefer incremental indexing over full re-indexing.
- Store index version and embedding model version for migrations.
- Allow CPU fallback for embeddings if GPU pressure is high.
- Batch disk writes without risking data loss.
- Surface indexing status calmly in UI: “Memory indexing is catching up.”

---

## 8. Background Job Scheduler

Centralize heavyweight work through a scheduler instead of ad hoc threads.

Job classes:

1. **Interactive**: active chat generation, cancellation, streaming.
2. **Near-interactive**: retrieval, reranking, small embedding writes.
3. **Idle**: backfills, compaction, summaries, thumbnails.
4. **Exclusive**: image/video generation, training, large imports/exports.

Rules:

- Interactive jobs preempt idle jobs.
- Exclusive jobs acquire a resource lock with a user-visible reason.
- Jobs must be cancelable or checkpointed.
- Jobs must report progress, phase, estimated memory tier, and safe failure messages.
- Failed jobs must release models, handles, temp files, and locks.

---

## 9. Graceful Degradation Ladder

Before OOM, degrade in this order:

1. Reduce batch size.
2. Lower max output tokens or context length for this request.
3. Drop low-value retrieved memories and raw excerpts.
4. Disable reranker or move it to CPU.
5. Pause idle embedding/indexing jobs.
6. Unload auxiliary models.
7. Ask user to queue exclusive media/training instead of running concurrently.
8. Fall back to lower-resolution media preset or smaller model.
9. Show a clear local-resource message with recovery actions.

User-facing copy should be calm:

```text
Reverie is keeping enough GPU headroom to avoid a crash. I paused memory indexing and switched this response to the balanced context budget. You can resume indexing after the chat finishes.
```

---

## 10. Training and Adapter Jobs

Training is never a hidden background side effect.

- Require explicit user approval and a clear “training mode” state.
- Serialize training against chat/media unless measured safe.
- Prefer LoRA/adapter training over full fine-tuning.
- Use small micro-batches, gradient accumulation, checkpointing, and conservative validation.
- Save checkpoints incrementally and support cancel/resume.
- Keep datasets inspectable and deletable.
- Do not train on private, deleted, or disallowed memories.
- Warn when training may reduce responsiveness or require unloading the chat model.

---

## 11. UI Performance Rules

The desktop UI must stay responsive while the backend is busy.

- Avoid main-thread parsing of huge transcripts, memory dumps, or job logs.
- Virtualize long lists and galleries.
- Debounce search/filter controls.
- Stream updates in small patches instead of replacing giant arrays.
- Use low-motion defaults and respect `prefers-reduced-motion`.
- Cap previews, thumbnails, and animated effects.
- Use event streams for job progress; avoid aggressive polling.

---

## 12. Telemetry and Diagnostics

Keep diagnostics local and useful.

Log at job/model boundaries:

- selected backend/model/quantization/context length,
- load/unload start/end,
- estimated and observed VRAM/RAM if available,
- queue wait time and runtime,
- batch sizes,
- fallback decisions,
- OOM or allocation failure details,
- cleanup success/failure.

Do not log raw private content by default. Use IDs and aggregate metrics unless the user enables debug capture.

---

## 13. Testing Checklist

- Long chat session does not grow memory without bound.
- Model unload actually releases GPU memory enough for the next job.
- Embedding backfill throttles during active generation.
- Media job does not run concurrently with chat unless resource lock allows it.
- Cancellation releases locks and temp files.
- Degraded mode returns a useful response instead of crashing.
- UI remains responsive with large memory/journal lists.
- Deleted/private content is not included in training or indexing jobs.

---

## 14. Anti-Patterns

- Loading every helpful model “just in case.”
- Treating reported free VRAM as guaranteed allocatable memory.
- Letting long context replace memory design.
- Running embedding backfills while the user waits for a streamed reply.
- Hiding OOM behind generic failures.
- Training adapters without explicit user review.
- Adding beautiful but expensive UI effects that compete with local inference.
