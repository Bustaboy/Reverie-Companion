# FastAPI Backend Patterns Skill

Use this skill when implementing or extending Reverie Companion backend features. It captures the preferred local-first architecture for API routes, service orchestration, background jobs, model integrations, training workflows, and memory/growth data flow.

## Core Principles

- Keep the backend local-first by default: every feature should work without external hosted services unless the user explicitly opts in.
- Prefer clear route/service/repository boundaries over putting business logic directly in FastAPI route handlers.
- Make long-running work explicit through job APIs and background workers instead of blocking request/response cycles.
- Treat model providers, training runners, storage backends, and worker queues as replaceable adapters behind stable service interfaces.
- Design schemas and data flow so future desktop, CLI, and automation clients can reuse the same API contracts.

## Route, Service, and Data Layering

Use a layered structure for backend feature work:

1. **Routes** define HTTP behavior only.
   - Parse path/query/body parameters through Pydantic schemas.
   - Inject dependencies such as services, repositories, settings, and worker clients.
   - Return response schemas or standard error responses.
   - Avoid direct file I/O, database queries, model calls, or training orchestration.
2. **Services** own business logic and orchestration.
   - Validate domain preconditions that require application state.
   - Coordinate repositories, model adapters, job creation, and event emission.
   - Convert provider-specific errors into domain errors.
   - Keep methods small enough to test without a live FastAPI server.
3. **Repositories or stores** own persistence.
   - Encapsulate database, JSONL, SQLite, vector index, or filesystem details.
   - Expose domain-oriented methods such as `append_memory`, `list_training_runs`, or `update_job_status`.
   - Keep transaction boundaries close to data mutations.
4. **Adapters** isolate external or heavy dependencies.
   - Place Ollama, Unsloth, filesystem watcher, vector database, and subprocess logic behind interfaces.
   - Keep adapter configuration in settings objects rather than global constants.

A route handler should generally look like: receive schema -> call service -> return response schema. If it needs more than light mapping, move that logic into the service.

## Pydantic Schema Guidance

Create explicit schemas for every API boundary:

- Use `*Request`, `*Response`, `*Create`, `*Update`, and `*Status` suffixes consistently.
- Keep request schemas client-focused and response schemas stable; do not leak internal ORM or storage objects.
- Prefer typed enums for job states, model providers, training phases, memory categories, and error codes.
- Include IDs, timestamps, and status fields on resources that clients may poll or cache.
- Use validation constraints for user-provided text, file paths, batch sizes, ranks, learning rates, and scheduling options.
- Mark experimental fields clearly in schema descriptions and default them safely.
- Avoid overloading one schema for unrelated flows; separate chat, memory ingestion, training, and growth analytics payloads.

When introducing a schema, add enough field descriptions that generated OpenAPI documentation is useful to future implementers.

## Job API Pattern

Use job APIs for any operation that can take more than a few seconds, performs repeated model calls, touches large files, or launches training.

Recommended endpoints:

- `POST /jobs/{kind}` or a domain-specific create endpoint such as `POST /training/lora/runs` to enqueue work.
- `GET /jobs/{job_id}` to retrieve status, progress, timestamps, and the latest message.
- `GET /jobs/{job_id}/events` for append-only progress events when streaming is useful.
- `POST /jobs/{job_id}/cancel` to request cancellation.
- `GET /jobs?kind=&state=` for client dashboards and recovery after app restart.

Recommended job fields:

- `id`, `kind`, `state`, `progress`, `created_at`, `updated_at`, `started_at`, `finished_at`.
- `input_summary` for safe client display without storing secrets or large payloads.
- `result` for small structured outputs and `artifact_paths` for local files.
- `error_code`, `error_message`, and `retryable` for failures.
- `cancellation_requested` to let workers exit safely between steps.

Job creation should be idempotent when practical. For example, a request may include a client-generated idempotency key or deterministic source hash to avoid duplicate ingestion/training work.

## Background Worker Pattern

Background workers should run long tasks outside route handlers while preserving local-first simplicity.

- Start with an in-process worker queue for local development unless the feature clearly needs a separate process.
- Persist job records before enqueueing work so interrupted app sessions can recover or mark jobs as stale.
- Make workers checkpoint progress after each meaningful step.
- Support cooperative cancellation by checking job state between model calls, file batches, or training phases.
- Keep worker functions thin: load job input -> call service/orchestrator -> update status/events.
- Use structured logs and job events rather than print-only progress.
- Never assume GPU availability; detect CPU/GPU capabilities and reflect them in job status.
- Clean up temporary files on success, cancellation, and failure, while preserving declared artifacts.

For multi-process workers, keep the same service contracts and move only queue transport details behind an adapter.

## Ollama Integration

Treat Ollama as a local model provider adapter, not as business logic.

- Centralize Ollama base URL, timeout, default model, context length, and streaming options in settings.
- Provide a health check that reports whether Ollama is reachable and which configured models are available.
- Keep prompt construction in domain services or prompt modules, then pass final messages/options to the adapter.
- Support streaming and non-streaming generation with a shared response shape.
- Normalize provider errors into domain errors such as model unavailable, context too large, timeout, or generation failed.
- Validate requested model names against local configuration or discovered models before starting expensive work.
- Make embedding and generation separate interfaces so memory retrieval can evolve independently from chat generation.
- Prefer local model calls by default; never silently fall back to a hosted provider.

When a feature depends on Ollama, expose clear setup or readiness errors so the UI can guide the user without crashing.

## Unsloth LoRA Training Orchestration

LoRA training should be orchestrated as resumable, observable jobs.

- Model training routes should create training-run resources and enqueue workers, not launch training inline.
- Validate dataset paths, output directories, base model names, max sequence length, rank, learning rate, batch size, epochs, and quantization options before enqueueing.
- Store a training manifest that captures input datasets, hyperparameters, base model, adapter output path, environment facts, and code version when available.
- Split orchestration into phases: prepare dataset, validate environment, launch training, checkpoint adapter, evaluate or smoke-test, register artifact.
- Wrap Unsloth execution behind a runner adapter that can use an imported Python API or subprocess command without changing route contracts.
- Stream progress by parsing trainer logs into job events and coarse progress percentages.
- Support cancellation between phases and, when possible, by terminating the subprocess or trainer gracefully.
- Keep artifacts local and explicit: adapters, tokenizer files, merged model outputs, evaluation reports, and logs should have known paths.
- Never delete prior adapters automatically; create versioned run directories and let cleanup be an explicit user action.

If training prerequisites are missing, fail early with actionable local setup guidance instead of starting a doomed job.

## Memory and Growth Data Flow

Memory and growth features should preserve provenance and keep the user in control.

1. **Capture** events from chat turns, reflections, files, or explicit user notes through ingestion endpoints.
2. **Normalize** raw input into typed memory candidates with source metadata, timestamps, privacy flags, and confidence.
3. **Review or policy-check** candidates before promoting them when the feature involves sensitive or identity-shaping data.
4. **Persist** promoted memories in the memory store and record embeddings or search indexes as derived data.
5. **Retrieve** relevant memories through a service that combines filters, semantic search, recency, and importance.
6. **Apply** retrieved memories to prompts through prompt builders, not directly inside route handlers.
7. **Measure growth** by writing structured observations, user feedback, model outcomes, and training examples to append-only logs or versioned stores.

Keep raw memories, embeddings, summaries, and training examples distinguishable. Derived data should be rebuildable from local source records whenever possible.

## Error Handling

Use consistent domain errors and response mapping:

- Define domain exception classes or error result types for validation, missing resources, provider unavailability, job conflicts, cancellation, and internal failures.
- Map known domain errors to stable HTTP status codes and machine-readable error codes.
- Include human-readable messages that are safe to show in the UI.
- Do not expose stack traces, local secrets, full prompts, or sensitive file contents in API responses.
- Preserve detailed diagnostics in local logs and job events when safe.
- For background jobs, record failure state on the job before re-raising or logging the exception.
- Make retryability explicit for transient errors such as Ollama timeouts, locked files, or temporary GPU/resource contention.

Prefer returning a structured error schema over ad hoc dictionaries so clients can handle failures consistently.

## Local-First Operation

Every backend feature should respect local-first expectations:

- Store user data, memory records, model artifacts, training datasets, and logs on local paths controlled by settings.
- Avoid network calls except to local services such as Ollama unless the user has configured a remote integration.
- Provide readiness checks for optional local dependencies instead of making them hard startup requirements.
- Make features degrade gracefully when GPU, Ollama, Unsloth, or optional indexes are unavailable.
- Keep secrets in local configuration or OS keychains; never write them to job events, manifests, or logs.
- Support restart recovery by persisting job and artifact metadata.
- Prefer deterministic, inspectable file formats such as JSON, JSONL, SQLite, and manifest files for user-owned data.
- Document any cleanup, migration, or export behavior that touches user data.

## Implementation Checklist

Before opening a backend feature PR, verify that:

- Routes are thin and delegate orchestration to services.
- Request and response schemas are explicit, typed, and documented.
- Long-running work uses a job API and background worker path.
- Ollama and Unsloth logic is isolated behind adapters.
- Memory/growth writes preserve provenance and separate raw from derived data.
- Errors use stable codes and do not leak sensitive local details.
- The feature works locally by default and has clear readiness messaging for optional dependencies.
- Tests cover service logic, schema validation, job state transitions, and provider/runner failure paths.
