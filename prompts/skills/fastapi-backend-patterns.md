# FastAPI Backend Patterns Skill

**Use for**: API routes, Pydantic schemas, service/repository layers, persistence, migrations, jobs, workers, streaming, adapters, health checks, tests, and local-first backend architecture.

## North Star

The backend is Reverie's durable companion core. Keep it modular, typed, testable, local-first, and boringly reliable so memory, growth, chat, media, and UI can evolve without rewrites.

## Non-Negotiables

- Thin routes; business logic belongs in services/domain modules.
- Validate all boundaries with Pydantic or equivalent schemas.
- Preserve provenance for memory, journal, growth, datasets, and media artifacts.
- Long-running work must be queued, cancelable, observable, and resource-bounded.
- Optional providers and ComfyUI integrations must not be required for core chat/memory.
- No hidden network calls or telemetry; offline core must function.
- Do not put try/catch blocks around imports.

## Layering Pattern

```text
API route
→ request/response schema
→ service/use-case
→ repository/storage adapter
→ external adapter or worker queue (optional)
```

Routes handle auth/local session context, validation, status codes, and response shape. Services enforce domain rules. Repositories own persistence details. Adapters isolate model servers, ComfyUI, filesystem, and optional cloud providers.

## Suggested Module Shape

```text
backend/app/
  api/              # FastAPI routers
  schemas/          # Pydantic request/response models
  services/         # chat, memory, reflection, growth, media
  repositories/     # database/filesystem access
  workers/          # queues, jobs, schedulers
  adapters/         # LLM, embeddings, ComfyUI, import/export
  core/             # config, logging, errors, lifecycle
  tests/
```

Follow existing project structure if it differs; do not force a rewrite.

## API Design Rules

- Use explicit resource names: `/characters/{id}/memories`, `/jobs/{id}`.
- Return stable IDs and timestamps for durable artifacts.
- Use pagination for lists and cursoring for long histories.
- Stream chat tokens/events; do not buffer entire responses unnecessarily.
- Use consistent error envelopes with human-safe messages and optional debug details.
- Make destructive actions explicit and auditable.
- Version schemas/migrations when persisted shape changes.

## Job Pattern

For reflection, indexing, media, training, import/export:

```json
{
  "id": "job_...",
  "type": "reflection|embedding|media|training|import|export",
  "status": "queued|running|paused|completed|failed|canceled",
  "progress": 0.0,
  "resource_estimate": {"vram_mb": 0, "ram_mb": 0},
  "created_at": "...",
  "updated_at": "...",
  "error": null
}
```

Jobs must support idempotent creation when possible, cancellation, progress events, cleanup, and safe restart after app relaunch.

## Local-First Data Rules

- Store user data locally by default.
- Keep exports explicit and user-initiated.
- Ensure deletion cascades to indexes, summaries, journals, growth, datasets, and media metadata.
- Encrypt or protect sensitive stores when project settings require it.
- Avoid logging raw private prompts, NSFW content, or secrets by default.

## Resource and Lifecycle Rules

- Backend startup should not eagerly load heavy models.
- Use lifespan hooks for lightweight setup and clean shutdown.
- Model/media/training work goes through scheduler/resource manager.
- Surface health: database, model server, embedding index, ComfyUI availability, queue depth.
- Use bounded worker pools and backpressure.

## Route Template

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

router = APIRouter(prefix="/characters", tags=["characters"])

class MemoryCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

class MemoryResponse(BaseModel):
    id: str
    text: str
    confidence: float

@router.post("/{character_id}/memories", response_model=MemoryResponse)
async def create_memory(
    character_id: str,
    request: MemoryCreateRequest,
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    return await service.create_memory(character_id, request)
```

Adapt names to the existing codebase.

## Testing Checklist

- [ ] Route validation and error envelopes.
- [ ] Service rules for provenance, deletion, rollback, and permissions.
- [ ] Repository migrations and round trips.
- [ ] Streaming and cancellation.
- [ ] Queue/job state transitions and restart safety.
- [ ] Offline mode and optional provider unavailable states.
- [ ] 8GB scheduler admission/refusal for heavy jobs.
