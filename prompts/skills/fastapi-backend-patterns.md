# Skill: FastAPI Backend Patterns

**Applies to**: FastAPI routes, Pydantic schemas, service/repository layering, workers, job queues, model adapters, memory/reflection/growth APIs, persistence, health checks, and backend tests.

Use this skill whenever backend code changes in Reverie's custom local-first API.

---

## 1. Mission

Reverie's backend should be boring, typed, observable, and extensible. It must protect local user data, coordinate local AI workloads under 8GB constraints, and expose clean APIs for chat, memory, reflection, growth, character management, and optional media integrations.

Default priority order:

1. Correctness and user trust.
2. Local-first privacy and deletion.
3. Clear service boundaries.
4. Predictable performance on 8GB systems.
5. Extensibility without framework sprawl.

---

## 2. Architecture Layers

Use explicit layers. Do not put business rules directly in route handlers.

```text
api/routes/*        HTTP/WebSocket/SSE boundaries, auth/session, request parsing
schemas/*           Pydantic request/response/event models
services/*          business workflows and policy decisions
repositories/*      persistence and query abstractions
adapters/*          LLM, embeddings, rerankers, ComfyUI, filesystem, model backends
workers/*           background jobs and schedulers
domain/*            pure domain models, scoring, validation, state transitions
```

Rules:

- Routes should call services and return schemas.
- Services may orchestrate repositories, adapters, and jobs.
- Repositories should not know about HTTP.
- Adapters should hide vendor/backend details.
- Domain logic should be testable without FastAPI startup.

---

## 3. Pydantic Schema Rules

- Use versioned schemas for durable data: `MemoryV1`, `JournalEntryV1`, `CharacterCardV1`.
- Separate create/update/read models.
- Avoid returning raw ORM objects.
- Include IDs, timestamps, lifecycle flags, and policy fields for memory/growth resources.
- Use enums for memory type, sensitivity, job status, and promotion status.
- Validate user-facing text lengths and list sizes at API boundaries.
- For partial updates, distinguish “field omitted” from “set to null.”

Example:

```python
class MemoryCreate(BaseModel):
    character_id: str
    type: MemoryType
    text: constr(min_length=1, max_length=1000)
    source_message_ids: list[str] = Field(default_factory=list, max_length=50)
    sensitivity: Sensitivity = Sensitivity.normal
    training_allowed: bool = False
```

---

## 4. Service Patterns

Services own workflows and policy gates.

### Memory service responsibilities

- extraction candidate intake,
- deduplication and contradiction checks,
- sensitivity/privacy gates,
- provenance writes,
- retrieval orchestration,
- deletion/tombstone enforcement,
- usage audit logging.

### Reflection service responsibilities

- bounded evidence collection,
- journal creation,
- promotion scoring,
- downstream memory/state writes,
- rollback links,
- privacy review.

### Growth service responsibilities

- relationship state updates,
- practice notes,
- training eligibility,
- dashboard summaries,
- rollback of state and artifacts.

### Chat service responsibilities

- context assembly,
- streaming generation,
- cancellation,
- model adapter selection,
- memory/growth injection,
- response audit events.

---

## 5. Repository Rules

- Prefer small repositories per aggregate: `MemoryRepository`, `JournalRepository`, `CharacterRepository`, `JobRepository`.
- Keep transaction boundaries explicit in services.
- Use tombstones for user-visible deletion where audit/rollback needs exist, and hard delete when the user requests full erasure.
- Ensure deleted/private records are excluded by default query methods.
- Provide explicit `include_deleted=True` only for admin/debug/rollback paths.
- Preserve provenance and supersession chains in persistence.
- Add migrations for schema changes; never rely on implicit JSON shape drift.

---

## 6. Error Handling

Return calm, typed errors. Do not leak stack traces or private content.

Use an application error model:

```json
{
  "error": {
    "code": "memory_conflict_requires_review",
    "message": "This memory conflicts with an existing note and needs review.",
    "details": {"conflict_id": "conf_..."},
    "retryable": false
  }
}
```

Rules:

- Map domain errors to appropriate HTTP statuses.
- Include stable error codes for UI handling.
- Log technical details locally with correlation IDs.
- Scrub raw message content from logs unless debug capture is enabled.
- Make cancellation a normal outcome, not an exception-looking failure.

---

## 7. Streaming and Events

Use streaming for chat tokens and job progress.

- Prefer WebSocket or SSE for chat and background job events.
- Include event type, ID, timestamp, and sequence number.
- Support cancellation by request/job ID.
- Send structured lifecycle events: `queued`, `started`, `progress`, `partial`, `completed`, `failed`, `cancelled`.
- Keep payloads small; do not stream huge memory dumps.

Example event:

```json
{
  "event": "job.progress",
  "job_id": "job_...",
  "phase": "embedding",
  "progress": 0.42,
  "message": "Indexing recent memories",
  "resource_mode": "idle"
}
```

---

## 8. Job Scheduling and 8GB Coordination

Heavy backend work must go through a scheduler.

- Classify jobs as interactive, near-interactive, idle, or exclusive.
- Ensure chat generation can preempt idle indexing.
- Ensure training/media jobs acquire exclusive resource locks unless measured safe.
- Store job status durably so the UI can recover after restart.
- Jobs must report progress and support cancellation or checkpointing.
- Cleanup must unload models, release locks, close files, and delete temp data.

Never start embedding backfills, media generation, or training from a request handler without queueing/resource checks.

---

## 9. API Design for Memory and Reflection

Recommended endpoints:

```text
POST   /api/chat/{conversation_id}/messages
GET    /api/chat/{conversation_id}/events
POST   /api/memories/search
PATCH  /api/memories/{memory_id}
DELETE /api/memories/{memory_id}
GET    /api/memories/{memory_id}/provenance
POST   /api/reflections/trigger
GET    /api/reflections/{entry_id}
POST   /api/reflections/{entry_id}/promote
POST   /api/growth/{character_id}/rollback
GET    /api/jobs/{job_id}
POST   /api/jobs/{job_id}/cancel
```

Keep commands explicit. Avoid magical endpoints that both chat, reflect, train, and mutate state invisibly.

---

## 10. Security and Privacy

- Bind APIs to local loopback by default unless the user enables remote access.
- Require explicit CORS origins for the Tauri frontend.
- Store secrets/tokens in OS keychain or encrypted local config where possible.
- Validate file paths; never allow path traversal for imports/exports/media.
- Treat imported character cards/lorebooks as untrusted data.
- Do not log raw NSFW/private content by default.
- Honor deletion across database rows, embeddings, caches, exports, and training queues.

---

## 11. Testing Checklist

- Route tests validate request/response schemas and error codes.
- Service tests cover memory promotion, contradiction, deletion, and rollback.
- Repository tests ensure default queries exclude deleted/private records.
- Streaming tests cover cancellation and ordered events.
- Scheduler tests verify idle jobs pause during chat and exclusive jobs lock resources.
- Privacy tests ensure private/deleted content is not exported, retrieved, reflected, or trained.
- Migration tests load old sample data and preserve provenance.

---

## 12. Anti-Patterns

- Business logic in FastAPI route functions.
- Raw dictionaries passed across every layer.
- Background `asyncio.create_task` with no durable job record.
- Endpoints that mutate memory without provenance.
- Catch-all exceptions returning “500 something went wrong.”
- Global singletons that make tests order-dependent.
- Hidden cloud calls in a local-first feature.
