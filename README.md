# Enterprise Agent

> Multi-agent AI assistant with RAG, tool use, conversational memory, evaluation harness, guardrails, and cloud-native deployment.

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.14 + uv |
| API | FastAPI + Pydantic |
| LLMs | Anthropic Claude (primary), OpenAI (secondary) |
| Orchestration | Custom loop → LangGraph |
| RAG | Chroma (local) → pgvector (prod) |
| Eval | Custom harness + Ragas |
| Guardrails | I/O validation + Presidio (PII) |
| Container | Docker |
| Cloud | Cloud Run |
| CI/CD | GitHub Actions |

## Features

- **RAG pipeline** — ingest, chunk, embed, retrieve with source citation
- **Multi-provider LLM layer** — interchangeable Claude / OpenAI via a common interface
- **Tool use** — agent executes real actions (create ticket, query metric, search docs)
- **Conversational memory** — sliding window + summarization, persisted per session
- **Multi-agent orchestration** — supervisor routes intent to specialized sub-agents
- **Guardrails** — input validation, prompt injection detection, PII redaction
- **Evaluation harness** — accuracy, faithfulness, hallucination rate via LLM-as-judge + Ragas
- **Observability** — token tracking, cost per request, structured logging
- **CI/CD** — automated lint → test → build → deploy on push

## Quick start

```powershell
uv sync
uv run uvicorn enterpriseagent.main:app --reload
curl http://localhost:8000/health
```

## Commands

| Command | Description |
|---|---|---|
| `make dev` | Dev server with hot-reload |
| `make test` | Run all tests |
| `make lint` | Lint |
| `make build` | Docker build |

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
│       │   └── loop.py
│       └── providers/
│           ├── __init__.py
│           ├── base.py
│           ├── anthropic.py
│           └── openai.py
└── tests/
    ├── __init__.py
    ├── test_health.py
    ├── test_providers.py
    └── test_agent_loop.py
```

## License

MIT
