# Reverie Backend

FastAPI backend foundation for Reverie, a local-first AI companion powered by Ollama.

The current backend is intentionally small and modular so future systems can be layered in cleanly:

- memory and retrieval
- character and prompt orchestration
- reflection, journaling, and growth workflows
- future local media/video integrations

## Long-Term Memory Foundation

`app.core.memory.MemoryManager` provides the backend-only foundation for persistent companion memory. It stores normalized memories in embedded LanceDB under `REVERIE_MEMORY_DB_PATH`, generates local embeddings with Ollama, and writes through mem0 when the optional SDK path is available so future adaptive extraction, reflection, and growth features can be layered in without changing route handlers.

Default settings are intentionally 8GB-friendly: no hosted services, one embedding request per memory/search operation, capped memory text size, small context retrieval limits, and no reranker in the hot path. Pull the default local embedding model before using memory:

```bash
ollama pull nomic-embed-text
```

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
```

Edit `.env` if you want to use a different Ollama host, chat model, embedding model, memory storage path, generation defaults, CORS origins, or log level.

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
