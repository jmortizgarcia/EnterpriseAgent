# Enterprise AI Agent

> 🧠 Self-study project exploring production-grade AI agent architectures

Enterprise-ready AI assistant with RAG, multi-provider LLM support, tool use, and cloud-native deployment. Built from scratch as a portfolio project to demonstrate end-to-end agent engineering — from local development to production deployment.

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.14 + uv |
| API | FastAPI + Pydantic |
| LLMs | Ollama (local, default), Anthropic Claude, OpenAI |
| Orchestration | Custom loop → LangGraph |
| RAG | Chroma (local) → pgvector (prod) |
| Eval | Custom harness + Ragas |
| Guardrails | I/O validation + Presidio (PII) |
| Container | Docker |
| Cloud | Cloud Run |
| CI/CD | GitHub Actions |

## ✅ Implemented

- **Multi-provider LLM layer** — Ollama (local), Claude, OpenAI via a common abstract interface; swap providers with a single config change
- **Agent loop** — perception → decision → action → observation cycle with tool calling, error handling (timeout, retry, exponential backoff), and provider fallback
- **Tool use** — three real tools: `search_docs`, `create_ticket`, `query_metric`; extensible via `Tool` ABC
- **RAG pipeline** — markdown ingestion with semantic chunking, ChromaDB vector store, Ollama embeddings (`nomic-embed-text`); 8 documentation pages indexed and searchable
- **Streaming chat** — Server-Sent Events (SSE) endpoint for real-time responses
- **CI/CD** — GitHub Actions workflow: `ruff check` → `pytest` → `docker build` on every push
- **8 passing tests** — provider interface, agent loop, tool execution, RAG chunking, chat endpoints

## 🔜 Roadmap

- Conversational memory — sliding window + LLM summarization, persisted per session
- Multi-agent orchestration — supervisor routes intent to specialized sub-agents (docs vs. actions)
- Guardrails — input validation, prompt injection detection, PII redaction
- Evaluation harness — accuracy, faithfulness, hallucination rate via LLM-as-judge + Ragas
- Observability — token tracking, cost per request, structured logging
- Cloud Run deployment — automated CI/CD with Secret Manager, pgvector, and monitoring

## Quick Start

### Prerequisites

```powershell
# Install Ollama (free, local LLM)
# https://ollama.com
ollama pull llama3.2
ollama pull nomic-embed-text
```

### Run

```powershell
uv sync
uv run uvicorn enterpriseagent.main:app --reload
```

### Verify

```powershell
curl http://localhost:8000/health
# {"status": "ok", "environment": "development"}
```

### Chat

```powershell
curl -X POST localhost:8000/agent/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"¿cuál es el SLA del plan enterprise?\",\"provider\":\"ollama\"}"
```

## Demo

> 📸 *Screenshot coming soon — agent responding with cited sources from the RAG corpus*

## Commands

| Command | Description |
|---|---|
| `make dev` | Dev server with hot-reload |
| `make test` | Run all tests |
| `make lint` | Lint with ruff |
| `make build` | Docker build |
| `make ingest` | Index docs into Chroma (RAG) |

## Project Structure

```
├── pyproject.toml          # Deps + entry points
├── Dockerfile
├── Makefile
├── data/
│   └── docs/               # RAG corpus (8 markdown files)
├── src/
│   └── enterpriseagent/
│       ├── main.py         # FastAPI app + endpoints
│       ├── config.py       # pydantic-settings
│       ├── agent/
│       │   ├── state.py    # AgentState
│       │   ├── loop.py     # Agent loop
│       │   └── tools/
│       │       ├── base.py
│       │       ├── search_docs.py
│       │       ├── create_ticket.py
│       │       └── query_metric.py
│       ├── providers/
│       │   ├── base.py     # LLMProvider ABC
│       │   ├── anthropic.py
│       │   ├── openai.py
│       │   └── ollama.py
│       └── rag/
│           ├── vector_store.py  # ChromaDB wrapper
│           └── ingestion.py     # Chunking + embed + index
└── tests/
    ├── test_health.py
    ├── test_providers.py
    ├── test_agent_loop.py
    ├── test_tools.py
    ├── test_chat.py
    ├── test_ollama.py
    └── test_rag.py
```

## License

MIT