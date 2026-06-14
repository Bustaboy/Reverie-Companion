# Reverie Backend

FastAPI backend for Reverie, a local-first AI companion powered by Ollama, durable memory, private reflection, and transparent growth controls.

The backend is intentionally modular so chat, memory, reflection, journaling, Personal LoRA review, and future media integrations can evolve without route handlers becoming product logic.

## Current Capabilities

- **Chat service**: non-streaming and SSE streaming chat through Ollama with bounded character, memory, and reflection context injection.
- **Character runtime**: versioned `CharacterBlueprint` schemas, SQLite persistence, CRUD routes, compact prompt compilation, and character-scoped memory hooks.
- **Moment Capture & visual continuity**: character-linked capture orchestration through `MomentCaptureService`, bounded `VisualPromptCompiler` prompt bundles, durable `MomentCaptureRecord` metadata, feedback actions, reviewable `VisualChangeEvent` canon proposals, rollback support, and character-scoped visual memory writeback.
- **Image generation and gallery metadata**: local image jobs retain conversation, character, source message, capture, prompt hash, feedback, review/canon, resource, and saved-asset metadata with tombstone-aware deletion and character/conversation filtering.
- **Long-term memory**: `app.core.memory.MemoryManager` stores normalized memories in embedded LanceDB under `REVERIE_MEMORY_DB_PATH`, generates local Ollama embeddings, and can write through mem0 when available.
- **Reflection journal**: `app.core.reflection.ReflectionManager` writes local, inspectable journal entries from bounded conversation windows and can promote high-confidence insights into memory.
- **Growth orchestration**: `app.core.growth.GrowthOrchestrator` coordinates memory retrieval, journal context, rare growth notifications, background reflection scheduling, and optional Personal LoRA candidate collection.
- **Personal LoRA foundation**: `app.core.lora.PersonalLoRATrainer` persists reviewable examples, explicit opt-in settings, approved-only training jobs, and rollback-friendly adapter manifests. The current job runner is a conservative foundation, not a heavyweight fine-tuner yet.
- **Local-first controls**: no hosted services are required for chat, memory, reflection, journal reads, Moment Capture metadata, visual review state, or Personal LoRA review state.

## Growth Loop Overview

The chat path stays responsive by using already persisted growth artifacts and scheduling heavier work after prompt preparation:

1. `ChatService` receives a chat request, optionally loads the selected `character_id`, and compiles compact CharacterBlueprint identity/relationship context.
2. The service delegates growth preparation to `GrowthOrchestrator`.
3. The orchestrator retrieves compact character-scoped memory context from `MemoryManager` and recent journal context from `ReflectionManager` in bounded background threads.
4. The prepared prompt receives character identity first, memory next, then reflection context, so durable facts remain clearer than tentative growth hypotheses.
5. After prompt preparation, the orchestrator schedules reflection only when cadence, cooldown, and meaningful-turn gates allow it.
6. Reflection output may become journal-only, promote a high-confidence memory, surface a rare growth notification on a later turn, or enter the Personal LoRA review queue if collection is explicitly enabled.

This keeps the active token path free of training, unbounded scans, and hidden cloud calls.

## 8GB-Friendly Defaults

- One local Ollama embedding request per memory write/search.
- Embedded LanceDB persistence on local disk.
- Capped memory text, retrieval count, journal entries, and context character budgets.
- Reflection is throttled background work, not active response-path work.
- Personal LoRA collection/training defaults to opt-out, rank 8, batch size 1, short sequence lengths, and one background job at a time.
- Moment Capture uses the existing image queue/resource coordinator, preserves retry/cancel metadata, pauses for TTS priority, downgrades to preview under low/unknown VRAM, and keeps chat non-blocking.
- No resident reranker, hosted telemetry, or mandatory external service.

## Backend Model Stack

The current backend model inventory is:

| Purpose | Model/artifact | Backend setting |
|---|---|---|
| Chat | `llama3.1:8b` | `REVERIE_OLLAMA_MODEL` |
| Memory embeddings | `nomic-embed-text` | `REVERIE_MEMORY_EMBEDDING_MODEL` |
| Memory extraction/reflection LLM | Reuses `REVERIE_OLLAMA_MODEL` unless set | `REVERIE_MEMORY_LLM_MODEL` |
| Primary TTS | Orpheus `orpheus-3b-0.1-ft-q4_k_m.gguf` | `REVERIE_TTS_PRIMARY_BACKEND="orpheus"` |
| Orpheus source model | `canopylabs/orpheus-3b-0.1-ft` | `REVERIE_TTS_ORPHEUS_MODEL_ID` |
| TTS fallback | Piper `en_US-lessac-medium.onnx`, stored as `reverie_default.onnx` | `REVERIE_TTS_PIPER_MODEL_PATH` |
| Default image generation | `flux1-schnell-fp8.safetensors` from `Comfy-Org/flux1-schnell` | `REVERIE_IMAGE_GENERATION_COMFYUI_WORKFLOW_PATH` |

See [Tech Stack and Model Inventory](../docs/TECH_STACK_MODELS.md) for optional
GGUF/text encoder references, legacy SD 1.5 workflow notes, and license notes.

## Key Settings

Edit `.env` to tune these values. All variables use the `REVERIE_` prefix.

### Chat and Ollama

- `REVERIE_OLLAMA_HOST`: local Ollama host, default `http://localhost:11434`
- `REVERIE_OLLAMA_MODEL`: chat model, default `llama3.1:8b`
- `REVERIE_DEFAULT_TEMPERATURE`, `REVERIE_DEFAULT_TOP_P`, `REVERIE_DEFAULT_NUM_PREDICT`: generation defaults

### Characters

- `REVERIE_CHARACTER_DB_PATH`: local SQLite path for durable CharacterBlueprint storage, default `./data/characters/characters.sqlite3`

### Memory

- `REVERIE_MEMORY_ENABLED`: disables retrieval/write attempts when `false`
- `REVERIE_MEMORY_DB_PATH`: local directory for LanceDB plus mem0 history data
- `REVERIE_MEMORY_EMBEDDING_MODEL`: local Ollama embedding model, default `nomic-embed-text`
- `REVERIE_MEMORY_MAX_CONTEXT_MEMORIES`, `REVERIE_MEMORY_CONTEXT_MAX_CHARS`: prompt-context budgets
- `REVERIE_MEMORY_MEM0_ENABLED`: toggles best-effort mem0 write-through while preserving direct LanceDB storage

### Reflection and Journal

- `REVERIE_REFLECTION_ENABLED`: master toggle for journal context and background reflection
- `REVERIE_REFLECTION_FREQUENCY`: `low`, `balanced`, or `high`
- `REVERIE_REFLECTION_SENSITIVITY`: `conservative`, `balanced`, or `responsive`
- `REVERIE_REFLECTION_USER_MESSAGE_INTERVAL`: baseline user-message cadence
- `REVERIE_REFLECTION_MIN_INTERVAL_SECONDS`: wall-clock cooldown
- `REVERIE_REFLECTION_HISTORY_MESSAGE_LIMIT`: evidence-window cap
- `REVERIE_REFLECTION_CONTEXT_ENTRY_LIMIT`, `REVERIE_REFLECTION_CONTEXT_MAX_CHARS`: prompt-context limits

### Growth Notifications

- `REVERIE_GROWTH_NOTIFICATIONS_ENABLED`: enables rare UI growth notices
- `REVERIE_GROWTH_NOTIFICATION_MIN_USER_MESSAGES`: minimum conversation depth before notices
- `REVERIE_GROWTH_NOTIFICATION_MESSAGE_INTERVAL`: coarse turn gate
- `REVERIE_GROWTH_NOTIFICATION_MIN_INTERVAL_SECONDS`: wall-clock quiet period
- `REVERIE_GROWTH_NOTIFICATION_MIN_CONFIDENCE`, `REVERIE_GROWTH_NOTIFICATION_MIN_EVIDENCE_COUNT`: quality gates

### Personal LoRA

- `REVERIE_PERSONAL_LORA_ENABLED`: enables local review/training controls
- `REVERIE_PERSONAL_LORA_DATA_PATH`: local JSONL/settings/manifest directory
- `REVERIE_PERSONAL_LORA_RANK`, `REVERIE_PERSONAL_LORA_MAX_RANK`: conservative adapter rank controls
- `REVERIE_PERSONAL_LORA_MIN_CONFIDENCE`, `REVERIE_PERSONAL_LORA_MIN_EVIDENCE_COUNT`: candidate quality gates
- `REVERIE_PERSONAL_LORA_MAX_EXAMPLE_CHARS`, `REVERIE_PERSONAL_LORA_MAX_EXAMPLES_PER_JOB`: dataset/job caps

### TTS and Voices

- `REVERIE_TTS_ENABLED`: enables the `/api/tts/generate` route
- `REVERIE_TTS_PRIMARY_BACKEND`: default `orpheus`; set `piper` only to force the fallback backend
- `REVERIE_TTS_ORPHEUS_RUNTIME`: default `cpp` for the local Orpheus-CPP runtime
- `REVERIE_TTS_ORPHEUS_MODEL_ID`: upstream Orpheus source model id, default `canopylabs/orpheus-3b-0.1-ft`
- `REVERIE_TTS_ORPHEUS_CPP_MODEL_ID`: active GGUF model id, default `isaiahbjork/orpheus-3b-0.1-ft-Q4_K_M-GGUF`
- `REVERIE_TTS_ORPHEUS_CPP_N_GPU_LAYERS`: default `0` to keep Orpheus on CPU; increase only after CPU smoke testing is degraded
- `REVERIE_TTS_ORPHEUS_CPP_N_CTX`: default `4096` to avoid the Orpheus-CPP `n_ctx=0` full-context RAM spike
- `REVERIE_TTS_PIPER_BINARY_PATH`: optional absolute path to `piper.exe` when Uvicorn is not launched from an activated venv
- `REVERIE_TTS_PIPER_MODEL_PATH`: local Piper `.onnx` voice model, default `./models/piper/reverie_default.onnx`
- `REVERIE_TTS_PIPER_TIMEOUT_SECONDS`: CPU synthesis timeout for one request

See [TTS Setup](../docs/TTS_SETUP.md) for the Orpheus/Piper model downloads and smoke test.

### Image Generation and ComfyUI

- `REVERIE_IMAGE_GENERATION_ENABLED`: disables Moment Capture/image routes when `false`
- `REVERIE_IMAGE_GENERATION_COMFYUI_URL`: local ComfyUI URL, default `http://127.0.0.1:8188`
- `REVERIE_IMAGE_GENERATION_DEFAULT_PRESET`: `preview_8gb`, `balanced_8gb`, or `high_8gb`
- `REVERIE_IMAGE_GENERATION_MIN_FREE_VRAM_MB`: minimum free VRAM floor before preview jobs run
- `REVERIE_IMAGE_GENERATION_COMFYUI_WORKFLOW_PATH`: optional ComfyUI workflow exported with `File -> Export (API)`
- `REVERIE_IMAGE_GENERATION_COMFYUI_*_NODE_ID`: optional node/input mapping so Reverie can patch prompt, negative prompt, width, height, steps, guidance/cfg, seed, and filename prefix into the exported workflow

See [ComfyUI Setup](../docs/COMFYUI_SETUP.md) for the project-specific 8GB Flux Schnell setup.

## Visual Consistency Eval Harness

M5-P08 adds a lightweight, deterministic eval harness that runs inside the backend pytest suite. It does not call CLIP, cloud scoring, ComfyUI, or any external image service. Instead it checks the contract data that should make visual comparison reliable across Codex Run A vs Run B:

- identity anchors are present in positive prompt bundles and prompt metadata
- rejected or wrong traits remain out of positive prompts and appear in negative prompts
- scene changes alter scene details without mutating identity anchors
- the same character stays stable across scenes, while distinct characters produce distinct prompt hashes and traits
- feedback actions affect future prompts only through reviewable flows
- wrong-appearance corrections, make-canon approvals, outfit reuse, and character-scoped visual memory are validated
- 8GB queue pressure stays non-blocking and degrades gracefully without GPU work

Run the harness directly:

```bash
cd backend
python -m pytest tests/test_visual_consistency_evals.py -q
```

Run it with the full backend test suite:

```bash
cd backend
python -m pytest
```

## Requirements

- Python 3.11+
- Ollama installed and running locally
- Orpheus-CPP and Piper are installed by `requirements.txt`; download the Orpheus GGUF/SNAC files and Piper fallback voice when testing voice playback
- A local Ollama chat model, for example:

```bash
ollama pull llama3.1:8b
```

- The default local embedding model:

```bash
ollama pull nomic-embed-text
```

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` if you want to use different Ollama models, storage paths, generation defaults, CORS origins, log level, or memory/growth budgets.

## Run

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

## Endpoints

### `GET /health`

Checks that the API is running and returns system plus Ollama diagnostics, including whether Ollama is reachable, which model is configured, whether that model is available locally, and whether Ollama reports it as currently loaded.

### `POST /chat`

Generates a chat response with Ollama. Streaming is enabled by default using Server-Sent Events.

Streaming response events:

- `message`: incremental text chunks
- `growth_notification`: optional rare growth notice metadata
- `done`: final completion marker
- `error`: meaningful stream failure details if Ollama fails after streaming starts

For a non-streaming response, set `"stream": false`. Include `"character_id": "..."` to ground chat in a saved companion and scope memory retrieval to that character plus explicitly shared memories.

### Character runtime

- `POST /api/characters`: creates a local versioned CharacterBlueprint from high-priority identity, relationship, and personality fields.
- `GET /api/characters`: lists saved companions for selection.
- `GET /api/characters/{character_id}`: loads one full blueprint.
- `PATCH /api/characters/{character_id}`: updates basic runtime fields without introducing a full creator wizard.
- `DELETE /api/characters/{character_id}`: removes a local blueprint.

The M4 migration stub lives at `app/migrations/versions/0001_character_blueprints.sql`; the repository also creates the same lightweight SQLite table/indexes on first use for local-first development.

### Moment Capture

- `POST /api/moment-capture`: queues a selected-character capture through the existing image generation service and returns the durable capture/job metadata.
- `POST /api/moment-capture/{capture_id}/feedback`: records visual feedback such as `looks_right`, `wrong_appearance`, `make_canon`, `use_outfit_again`, `just_this_scene`, or `reject_style_trait`.
- `GET /api/moment-capture/visual-changes`: lists reviewable visual canon proposals.
- `POST /api/moment-capture/visual-changes/{event_id}/approve`
- `POST /api/moment-capture/visual-changes/{event_id}/reject`
- `POST /api/moment-capture/visual-changes/{event_id}/rollback`

Canon-affecting feedback stays pending until reviewed. Approved changes update `VisualIdentityProfile` with provenance and rollback metadata; rejected or rolled-back changes do not enter future positive prompt guidance. Visual memory writeback is character-scoped and not training-eligible by default.

### `GET /journal/entries`

Returns recent local self-reflection journal entries for the Journal UI.

### `GET /growth/personal-lora`

Returns Personal LoRA settings, current job, example counts, and review queue items.

### Personal LoRA actions

- `PATCH /growth/personal-lora/settings`
- `POST /growth/personal-lora/examples/{item_id}/approve`
- `POST /growth/personal-lora/examples/{item_id}/reject`
- `DELETE /growth/personal-lora/examples/{item_id}`
- `POST /growth/personal-lora/start`
- `POST /growth/personal-lora/stop`

## Project Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── api/routes/          # Thin FastAPI route modules
│   ├── core/                # Memory, reflection, growth, LoRA, Ollama clients
│   ├── models/              # Pydantic request/response schemas
│   ├── repositories/        # SQLite/file persistence boundaries
│   ├── schemas/             # Durable versioned Pydantic schemas
│   └── services/            # Chat and character orchestration services
├── tests/                   # Backend service and route tests
├── requirements.txt
└── README.md
```
