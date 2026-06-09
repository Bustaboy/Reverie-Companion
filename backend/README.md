# Reverie Backend

FastAPI backend foundation for Reverie, a local-first offline AI companion powered by Ollama.

## Features

- Async FastAPI application structure
- Local Ollama integration through the official `ollama` Python library
- Streaming `/chat` endpoint for responsive companion replies
- Lightweight `/health` endpoint for readiness checks
- Pydantic Settings configuration loaded from environment variables or `.env`
- Modular layout ready for memory, character logic, prompt orchestration, and growth systems

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

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy the example environment file and adjust values as needed:

   ```bash
   cp .env.example .env
   ```

4. Start Ollama and make sure your selected model is available:

   ```bash
   ollama serve
   ollama pull llama3.1:8b
   ```

5. Run the API server:

   ```bash
   uvicorn app.main:app --reload
   ```

## API

### `GET /health`

Returns a minimal readiness payload.

```bash
curl http://localhost:8000/health
```

### `POST /chat`

Streams a plain-text response from the configured local Ollama model.

```bash
curl -N http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are Reverie, a warm and emotionally intelligent companion."},
      {"role": "user", "content": "Say hello."}
    ]
  }'
```

Optional per-request overrides:

- `model`
- `temperature`
- `top_p`
- `num_ctx`

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `APP_NAME` | `Reverie Backend` | FastAPI display name |
| `APP_VERSION` | `0.1.0` | Backend version |
| `API_PREFIX` | empty | Optional route prefix |
| `OLLAMA_HOST` | `http://localhost:11434` | Local Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1:8b` | Default chat model |
| `OLLAMA_TEMPERATURE` | `0.8` | Default response creativity |
| `OLLAMA_TOP_P` | `0.9` | Default nucleus sampling value |
| `OLLAMA_NUM_CTX` | `8192` | Default requested context window |
| `REQUEST_TIMEOUT_SECONDS` | `120` | Ollama request timeout |

## Next Extension Points

- Add memory retrieval before generation in `app/core/ollama_client.py` or a dedicated prompt orchestration service.
- Add character definitions and emotional state models under `app/models/`.
- Add new API routers under `app/api/routes/` and register them in `app/main.py`.
- Add growth, reflection, and journaling workers as separate services so long conversations remain responsive.
