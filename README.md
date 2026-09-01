# Enterprise AI Agent

> 🧠 Self-study project exploring production-grade AI agent architectures

Enterprise-ready AI assistant with RAG, multi-provider LLM support, tool use, and cloud-native deployment. Built from scratch as a portfolio project to demonstrate end-to-end agent engineering — from local development to production deployment.

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.14 + uv |
| API | FastAPI + Pydantic |
| LLMs | Ollama (local, default), Anthropic Claude, OpenAI |
| Orchestration | LangGraph + multi-agent supervisor |
| RAG | Chroma (local) / pgvector (prod), config-driven |
| Eval | Custom harness + LLM-as-judge |
| Guardrails | I/O validation + regex PII |
| Container | Docker (Alpine build → slim runtime) |
| Cloud | Cloud Run (config-driven vector store, WIF auth) |
| CI/CD | GitHub Actions (CI + Cloud Run deploy via Workload Identity Federation) |

## ✅ Implemented

- **Multi-provider LLM layer** — Ollama (local), Claude, OpenAI via a common abstract interface; swap providers with a single config change
- **LangGraph orchestration** — perception-decide-act cycle with StateGraph, retry logic, provider fallback, and multi-agent supervisor
- **Tool use** — three real tools: `search_docs` (RAG), `create_ticket`, `query_metric`; extensible via `Tool` ABC
- **RAG pipeline** — markdown ingestion with semantic chunking, ChromaDB vector store, Ollama embeddings (`nomic-embed-text`); 8 documentation pages indexed and searchable
- **Conversational memory** — sliding window (20 turns) + LLM summarization, persisted per session via SQLite
- **Multi-agent supervisor** — intent classification by keywords routes to Docs Agent or Actions Agent
- **Guardrails** — input validation, prompt injection detection (regex), PII redaction (DNI, email, phone) via FastAPI middleware
- **Streaming chat** — Server-Sent Events (SSE) endpoint for real-time responses
- **Evaluation harness** — 40-question dataset, LLM-as-judge accuracy, faithfulness scoring, cost tracking
- **Observability** — structured JSON logging, per-request token/cost tracking, LangSmith tracing (config-driven)
- **Session stats** — `GET /agent/stats/{session_id}` with aggregated tokens, cost, duration, tools used
- **pgvector support** — `PgVectorStore` with IVFFlat indexing, config-driven via `VECTOR_STORE` env var
- **Production Dockerfile** — multi-stage (Alpine build → slim runtime), `:8080` port, Cloud Run ready
- **CI/CD** — GitHub Actions CI (ruff + pytest) + Cloud Run deploy with Workload Identity Federation
- **173 passing tests** — provider interface, agent loop, LangGraph, tool execution, RAG, memory, guardrails, orchestrator, evaluation, observability

## 🔜 Roadmap

- Monitorización — Cloud Monitoring dashboard + Terraform infra as code

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

```powershell
curl -X POST localhost:8000/agent/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"¿cuál es el SLA del plan enterprise?\",\"provider\":\"ollama\"}"

# → "El plan Enterprise tiene un SLA del 99.99% de disponibilidad mensual [1]..."
```

El agente responde con fuentes citadas desde el corpus RAG de 8 documentos.

## Deployment (manual setup)

El CI/CD está listo en `.github/workflows/deploy.yml`. Para activarlo:

```powershell
# 1. GCP project + APIs
gcloud projects create enterprise-agent --name="Enterprise Agent"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

# 2. Crear repositorio Docker
gcloud artifacts repositories create enterprise-agent ^
  --repository-format=docker --location=europe-west1

# 3. Subir API keys como secrets
echo -n "sk-ant-..." | gcloud secrets create anthropic-api-key --data-file=-
echo -n "sk-proj-..." | gcloud secrets create openai-api-key --data-file=-
echo -n "..." | gcloud secrets create langsmith-api-key --data-file=-

# 4. Base de datos con pgvector (opción recomendada: Neon serverless)
#    Crear cuenta en neon.tech → copiar DATABASE_URL

# 5. Workload Identity Federation para GitHub Actions
#    https://docs.github.com/en/actions/security-for-github-actions/
#      security-hardening-your-deployments/
#      configuring-openid-connect-in-google-cloud-platform

# 6. Setear secrets en GitHub → Settings > Secrets and variables > Actions
#    GCP_PROJECT_ID (var), WIF_PROVIDER (secret),
#    DEPLOY_SERVICE_ACCOUNT (secret), DATABASE_URL_PG (secret)

# 7. Push a main → deploy automático
git add . && git commit -m "Ready for production" && git push origin main
```

## Commands

| Command | Description |
|---|---|
| `make dev` | Dev server with hot-reload |
| `make test` | Run all tests |
| `make lint` | Lint with ruff |
| `make build` | Docker build |
| `make ingest` | Index docs into Chroma (RAG) |
| `make eval` | Run evaluation (40 questions, LLM-as-judge) |
| `docker compose up -d` | Start pgvector for production-like dev |

## Project Structure

```
├── pyproject.toml          # Deps + entry points
├── Dockerfile              # Multi-stage (Alpine build → slim)
├── docker-compose.yml      # pgvector for production-like dev
├── Makefile
├── .github/
│   └── workflows/
│       ├── ci.yml          # lint + test on push
│       └── deploy.yml      # Cloud Run via WIF (requires manual GCP setup)
├── data/
│   └── docs/               # RAG corpus (8 markdown files)
├── src/
│   └── enterpriseagent/
│       ├── main.py         # FastAPI app + endpoints + guardrails middleware
│       ├── config.py       # pydantic-settings
│       ├── agent/
│       │   ├── state.py    # AgentState
│       │   ├── loop.py     # Agent loop (delegates to graph)
│       │   ├── graph.py    # LangGraph StateGraph
│       │   ├── orchestrator.py  # Intent classifier + tool filtering
│       │   └── tools/
│       │       ├── base.py
│       │       ├── search_docs.py  # RAG tool (ChromaDB)
│       │       ├── create_ticket.py
│       │       └── query_metric.py
│       ├── providers/
│       │   ├── base.py     # LLMProvider ABC
│       │   ├── anthropic.py
│       │   ├── openai.py
│       │   └── ollama.py
│       ├── memory/
│       │   └── conversation.py  # SQLite-backed session memory
│       ├── guardrails/
│       │   ├── input.py    # Input validation + prompt injection
│       │   ├── output.py   # Output validation
│       │   └── pii.py      # PII detection + redaction
│       ├── evaluation/
│       │   ├── dataset.py  # 40 eval questions (4 categories)
│       │   ├── harness.py  # run_evaluation + EvalReport
│       │   └── metrics.py  # llm_judge, faithfulness, cost, precision
│       ├── observability/
│       │   ├── cost.py     # Pricing tables + calculate_cost
│       │   ├── logger.py   # Structured JSON logging
│       │   └── tracing.py  # LangSmith tracer (config-driven)
│       └── rag/
│           ├── vector_store.py  # ChromaStore + PgVectorStore + factory
│           └── ingestion.py     # Chunking + embed + index
└── tests/
    ├── test_health.py
    ├── test_providers.py
    ├── test_agent_loop.py
    ├── test_tools.py
    ├── test_chat.py
    ├── test_ollama.py
    ├── test_rag.py
    ├── test_memory.py
    ├── test_guardrails.py
    ├── test_orchestrator.py
    ├── test_evaluation_dataset.py
    ├── test_evaluation_metrics.py
    ├── test_evaluation_harness.py
    ├── test_observability_cost.py
    ├── test_observability_logger.py
    ├── test_observability_tracing.py
    └── test_stats_endpoint.py
```

## License

MIT