# Backend

Python FastAPI backend for Vision Companion.

This is where the core logic lives:
- LLM integration (Ollama)
- Memory & RAG system (mem0 + Cognee + LanceDB)
- Self-learning / growth engine
- Character management
- Prompt engineering
- Future Personal LoRA training pipeline

## Structure (planned)

```
backend/
├── app/
│   ├── main.py
│   ├── core/
│   ├── memory/
│   ├── character/
│   ├── prompts/
│   └── training/
├── requirements.txt
└── README.md
```