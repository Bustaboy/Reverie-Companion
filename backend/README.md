# Reverie Backend

FastAPI backend foundation for Reverie, a local-first AI companion powered by Ollama.

The current backend is intentionally small and modular so future systems can be layered in cleanly:

- memory and retrieval (mem0 + embedded LanceDB)
- character and prompt orchestration
- reflection, journaling, and growth workflows
- future local media/video integrations

## Long-Term Memory Foundation

`app.core.memory.MemoryManager` provides the backend-only foundation for persistent companion memory. It stores normalized memories in embedded LanceDB under `REVERIE_MEMORY_DB_PATH`, generates local embeddings with Ollama, and writes through mem0 when the optional SDK path is available so future adaptive extraction, reflection, journaling, pruning, and growth features can be layered in without changing route handlers.

The memory manager is not wired into API routes yet. Future chat orchestration or prompt-building services can use it like this:

```python
from app.core.memory import MemoryManager

memory = MemoryManager()
memory.add_memory(
    "The user prefers emotionally warm, detailed companion responses.",
    {"memory_type": "semantic", "source": "chat"},
)
context = memory.get_relevant_context("How should I respond to the user?")
```

Default settings are intentionally 8GB-friendly:

- no hosted services or mandatory cloud calls
- embedded LanceDB on local disk for restart-safe vector persistence
- one local Ollama embedding request per memory write/search
- best-effort mem0 extraction, with direct LanceDB recall remaining available if mem0 fails
- capped memory text, retrieval count, and context character budgets
- no reranker or resident Python embedding model in the hot path

Pull the default local embedding model before using memory:

```bash
ollama pull nomic-embed-text
```

Key memory settings in `.env`:

- `REVERIE_MEMORY_ENABLED`: disables retrieval/write attempts when set to `false`
- `REVERIE_MEMORY_DB_PATH`: local directory for LanceDB plus mem0 history data
- `REVERIE_MEMORY_EMBEDDING_MODEL`: local Ollama embedding model
- `REVERIE_MEMORY_MAX_CONTEXT_MEMORIES` and `REVERIE_MEMORY_CONTEXT_MAX_CHARS`: prompt-context budget controls
- `REVERIE_MEMORY_MEM0_ENABLED`: toggles best-effort mem0 write-through while preserving direct LanceDB storage

## Reflection Scheduling Controls

Reflection and growth journaling are enabled by default, but they are scheduled conservatively so chat stays responsive. The chat service reads existing journal notes for continuity, then queues any new reflection as background work after natural learning moments; the current response never waits for journaling.

Key reflection settings in `.env`:

- `REVERIE_REFLECTION_ENABLED`: disables journal context and background reflection when set to `false`
- `REVERIE_REFLECTION_FREQUENCY`: `low`, `balanced`, or `high`; adjusts the message interval, cooldown, and evidence window size
- `REVERIE_REFLECTION_SENSITIVITY`: `conservative`, `balanced`, or `responsive`; controls whether salient or sensitive turns can auto-trigger reflection
- `REVERIE_REFLECTION_USER_MESSAGE_INTERVAL`: base user-message interval for scheduled reflections
- `REVERIE_REFLECTION_MIN_INTERVAL_SECONDS`: base wall-clock cooldown between background reflections
- `REVERIE_REFLECTION_HISTORY_MESSAGE_LIMIT`: maximum recent messages copied into a journal evidence window

## Requirements

- Python 3.11+
- Ollama installed and running locally
- A local Ollama model, for example:

```bash
ollama pull llama3.1:8b
```

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
ollama pull nomic-embed-text
```

Edit `.env` if you want to use a different Ollama host, chat model, embedding model, memory storage path, generation defaults, CORS origins, log level, or memory context budget.

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

Request example:

```json
{
  "messages": [
    {"role": "system", "content": "You are Reverie, a warm and emotionally intelligent companion."},
    {"role": "user", "content": "Hi, how are you feeling today?"}
  ],
  "stream": true
}
```

Streaming response events:

- `message`: incremental text chunks
- `done`: final completion marker
- `error`: meaningful stream failure details if Ollama fails after streaming starts

For a non-streaming response, set `"stream": false`.

## Project Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── memory.py
│   │   └── ollama_client.py
│   ├── api/
│   │   └── routes/
│   │       └── chat.py
│   └── models/
├── requirements.txt
├── .env.example
└── README.md
```
