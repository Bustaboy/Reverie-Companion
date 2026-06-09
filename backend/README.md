# Reverie Backend

FastAPI backend foundation for Reverie, a local-first AI companion powered by Ollama.

The backend is intentionally small and modular so memory, character logic, prompt orchestration, reflection, and growth systems can be added without rewriting the API foundation.

## Features

- Async FastAPI application
- Local Ollama integration through the official `ollama` Python library
- Streaming `/chat` endpoint for responsive companion replies
- Non-streaming `/chat` mode for simple integrations and tests
- `/health` endpoint for service checks
- Pydantic Settings configuration with `.env` support
- Modular structure for future memory, character, and growth layers

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
│       └── chat.py
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Install Ollama and pull your configured model:

```bash
ollama pull llama3.1:8b
```

## Run

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Health Check

```bash
curl http://127.0.0.1:8000/health
```

## Chat Endpoint

Streaming is enabled by default and returns `text/plain` chunks as the model generates text.

```bash
curl -N http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are Reverie, a warm local AI companion."},
      {"role": "user", "content": "Say hello."}
    ]
  }'
```

For a complete JSON response, set `stream` to `false`:

```bash
curl http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "stream": false,
    "messages": [
      {"role": "user", "content": "Say hello."}
    ]
  }'
```

## Configuration

All settings are prefixed with `REVERIE_` and can be set in `.env` or the process environment.

| Variable | Default | Description |
| --- | --- | --- |
| `REVERIE_APP_NAME` | `Reverie Backend` | FastAPI application name |
| `REVERIE_APP_VERSION` | `0.1.0` | Application version |
| `REVERIE_ENVIRONMENT` | `development` | Runtime environment label |
| `REVERIE_API_HOST` | `127.0.0.1` | Suggested API host for local development |
| `REVERIE_API_PORT` | `8000` | Suggested API port for local development |
| `REVERIE_OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama server URL |
| `REVERIE_OLLAMA_MODEL` | `llama3.1:8b` | Default local model |
| `REVERIE_OLLAMA_REQUEST_TIMEOUT` | `120` | Ollama request timeout in seconds |
| `REVERIE_DEFAULT_TEMPERATURE` | `0.8` | Default generation temperature |
| `REVERIE_DEFAULT_TOP_P` | `0.9` | Default nucleus sampling value |
