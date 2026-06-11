# Reverie Backend

FastAPI backend foundation for Reverie, a local-first AI companion powered by Ollama.

The current backend is intentionally small and modular so future systems can be layered in cleanly:

- memory and retrieval (mem0 + embedded LanceDB)
- character and prompt orchestration
- reflection, journaling, and growth workflows
- future local media/video integrations

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

Edit `.env` if you want to use a different Ollama host, model, generation defaults, CORS origins, log level, or local memory storage path.

## Run

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.


## Local Memory Foundation

The backend includes a backend-only `MemoryManager` in `app/core/memory.py` for long-term memory. It uses:

- `mem0` for adaptive user/session memory extraction and retrieval
- embedded LanceDB under `REVERIE_DATA_DIR/memory/lancedb` for local vector persistence
- Ollama embeddings through `REVERIE_MEMORY_EMBEDDING_MODEL` (default: `nomic-embed-text`) so no cloud provider is required

The memory manager is lazy-loaded and is not wired into API routes yet. Future chat orchestration can call:

```python
from app.core.memory import MemoryManager

memory = MemoryManager()
memory.add_memory(
    "The user prefers emotionally warm, detailed companion responses.",
    {"memory_type": "semantic", "source": "chat", "session_id": "default_session"},
)
context = memory.get_relevant_context("How should I respond to the user?")
```

Keep Ollama running and pull the embedding model before first use:

```bash
ollama pull nomic-embed-text
```

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
