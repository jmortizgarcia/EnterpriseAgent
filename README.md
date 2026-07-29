# Enterprise Agent

> Multi-agent AI assistant with RAG, tool use, conversational memory, evaluation harness, guardrails, and cloud-native deployment.

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

## Features

- **RAG pipeline** — ingest, chunk, embed, retrieve with source citation (Chroma + Ollama embeddings)
- **Multi-provider LLM layer** — interchangeable Ollama (local) / Claude / OpenAI via a common interface
- **Tool use** — agent executes real actions (create ticket, query metric, search docs)
- **Conversational memory** — sliding window + summarization, persisted per session (Sprint 3)
- **Multi-agent orchestration** — supervisor routes intent to specialized sub-agents (Sprint 3)
- **Guardrails** — input validation, prompt injection detection, PII redaction (Sprint 3)
- **Evaluation harness** — accuracy, faithfulness, hallucination rate via LLM-as-judge + Ragas (Sprint 4)
- **Observability** — token tracking, cost per request, structured logging (Sprint 4)
- **CI/CD** — automated lint → test → build → deploy on push

## Quick start

### 1. Install Ollama (free, local LLM)

```powershell
# https://ollama.com — download and install
ollama pull llama3.2
ollama list  # verify it's installed
```

### 2. Start the agent

```powershell
uv sync
uv run uvicorn enterpriseagent.main:app --reload
curl http://localhost:8000/health
```

### 3. Chat with the agent

```powershell
curl -X POST localhost:8000/agent/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"dime algo interesante\",\"provider\":\"ollama\"}"
```

## Commands

| Command | Description |
|---|---|---|
| `make dev` | Dev server with hot-reload |
| `make test` | Run all tests |
| `make lint` | Lint |
| `make build` | Docker build |
| `make ingest` | Index docs into Chroma (RAG) |

## Project structure

```
├── .gitignore
├── .python-version
├── AGENTS.md
├── Dockerfile
├── Makefile
├── README.md
├── pyproject.toml
├── uv.lock
├── data/
│   └── docs/                     # RAG corpus (8 markdown files)
├── docs/
│   └── ...
├── src/
│   └── enterpriseagent/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── state.py
│       │   ├── loop.py
│       │   └── tools/
│       │       ├── __init__.py
│       │       ├── base.py
│       │       ├── search_docs.py
│       │       ├── create_ticket.py
│       │       └── query_metric.py
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── anthropic.py
│       │   ├── openai.py
│       │   └── ollama.py
│       └── rag/
│           ├── __init__.py
│           ├── vector_store.py
│           └── ingestion.py
└── tests/
    ├── __init__.py
    ├── test_health.py
    ├── test_providers.py
    ├── test_agent_loop.py
    ├── test_tools.py
    ├── test_chat.py
    └── test_ollama.py
```

## License

MIT
