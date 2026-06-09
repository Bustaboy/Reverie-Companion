# Reverie Backend

FastAPI backend foundation for Reverie, a local-first AI companion powered by Ollama.

The current backend is intentionally small and modular so future systems can be layered in cleanly:

- memory and retrieval
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
```

Edit `.env` if you want to use a different Ollama host, model, or generation defaults.

## Run

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

## Endpoints

### `GET /health`

Checks that the API is running and verifies that Ollama is reachable.

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

For a non-streaming response, set `"stream": false`.

## Project Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── ollama_client.py
│   ├── api/
│   │   └── routes/
│   │       └── chat.py
│   └── models/
├── requirements.txt
├── .env.example
└── README.md
```
