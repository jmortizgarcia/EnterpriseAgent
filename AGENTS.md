# AGENTS.md

## Identity

This is **Proyecto Estrella** — an enterprise AI agent built as a portfolio project targeting Accenture **AI LLM Junior Technology Architect** and **AI Software Engineer** roles.

## Source of truth

Read `docs/Guion-Proyecto-Estrella-Jose-Maria-Ortiz.md` first. It is the master narrative. `docs/plan.md` is the tactical breakdown (Spanish); `docs/Chuleta.md` is the author's interview-prep cheat sheet (Spanish).

## Stack

| Layer | Choice |
|---|---|---|
| Language | Python 3.14 (`.python-version`, `pyproject.toml`) |
| Package mgr | `uv` |
| API | FastAPI + pydantic |
| LLMs | Ollama (local, default), Anthropic Claude, OpenAI (abstraction layer) |
| Orchestration | LangGraph + multi-agent supervisor |
| RAG | Chroma (local) / pgvector (prod), config-driven |
| Eval | Custom harness + LLM-as-judge |
| Guardrails | I/O validation + regex PII |
| Container | Docker (Alpine build → slim runtime) |
| Cloud | Cloud Run |
| CI/CD | GitHub Actions (CI + Cloud Run deploy) |

## Package layout

```
├── .github/workflows/
│   ├── ci.yml              # Ruff → pytest on every push
│   └── deploy.yml           # Cloud Run deploy via WIF
├── src/enterpriseagent/     # package root (matches pyproject.toml `name`)
├── __init__.py          # must define main() — entry point `enterpriseagent:main`
├── main.py              # FastAPI app
├── config.py            # pydantic-settings
├── agent/
│   ├── __init__.py
│   ├── state.py           # AgentState dataclass
│   ├── loop.py            # run_agent bucle + streaming
│   ├── graph.py           # LangGraph StateGraph (Sprint 3)
│   ├── orchestrator.py    # Intent classifier + tool filtering (Sprint 3)
│   └── tools/
│       ├── __init__.py
│       ├── base.py        # Tool ABC
│       ├── search_docs.py # RAG tool (Chroma real, Sprint 2)
│       ├── create_ticket.py
│       └── query_metric.py
├── providers/
│   ├── __init__.py
│   ├── base.py           # LLMProvider ABC + ToolCall/Response
│   ├── anthropic.py      # Anthropic Claude implementation
│   ├── openai.py         # OpenAI GPT-4o implementation
│   └── ollama.py         # Ollama (local LLM) implementation
├── rag/
│   ├── __init__.py
│   ├── vector_store.py   # ChromaStore + PgVectorStore + get_vector_store()
│   └── ingestion.py      # chunk_markdown + ingest pipeline
├── memory/
│   └── conversation.py   # SQLite-backed session memory (Sprint 3)
├── guardrails/
│   ├── input.py          # Input validation + prompt injection (Sprint 3)
│   ├── output.py         # Output validation (Sprint 3)
│   └── pii.py            # PII detection + redaction (Sprint 3)
├── evaluation/
│   ├── dataset.py        # 40 eval questions (Sprint 4)
│   ├── harness.py        # run_evaluation + EvalReport (Sprint 4)
│   └── metrics.py        # llm_judge, faithfulness, cost (Sprint 4)
└── observability/
    ├── cost.py           # Pricing tables + calculate_cost (Sprint 4)
    ├── logger.py         # Structured JSON logging (Sprint 4)
    └── tracing.py        # LangSmith tracer (Sprint 4)
```

## Essential commands

```powershell
uv sync                                 # install deps
uv run uvicorn enterpriseagent.main:app --reload   # dev server
uv run pytest -v                        # all tests
uv run pytest -v -k test_name           # single test
uv run ruff check .                     # lint
uv run ruff check --fix .               # lint + autofix
uv run python -m enterpriseagent.rag.ingestion   # index docs into Chroma
uv run python -m enterpriseagent.evaluation.harness --output eval-report.md  # run eval
docker compose up -d                    # start pgvector
ollama pull nomic-embed-text             # embedding model for RAG
```

## Critical conventions

- **Always use `enterpriseagent.` prefix** for Python module paths (e.g. `enterpriseagent.main:app`), never `src.`.
- Python 3.14 is the real version; `docs/plan.md` and the guion say 3.12 — treat as stale on this point.
- Sprint 0 complete: CI/GitHub Actions, Makefile, Dockerfile, test_health.py committed.
- Sprint 1 complete: Multi-provider, agent loop, tools, FastAPI integration (60 tests).
- Sprint 2 complete: RAG pipeline (Chroma + Ollama embeddings + markdown chunking, 45 chunks indexed).
- Sprint 3 complete: Memory, LangGraph, guardrails, multi-agent orchestrator.
- Sprint 4 complete: Evaluation harness (40 questions), observability (cost/logger/tracing), /stats endpoint. 173 tests.
- Sprint 5 complete: pgvector, production Dockerfile, Cloud Run deploy, CI/CD. (Manual GCP setup pending.)
- `docs/Chuleta.md` is the author's personal interview-prep doc (renamed from `docs/README.md`), not a project README.

## Project rules (from the guion)

- Each sprint ends with something runnable. Small and real > big and fake.
- Commit early, commit often. The public repo is the CV.
- Use AI assistants and document their impact — this is a stated job requirement.
- Build the agent loop manually first; adopt LangGraph at Sprint 3.
- **Commit reminders** — during development, the agent will proactively suggest commits at logical boundaries (feature done, sprint milestone, meaningful state) and ask before executing.

## Files to read first

1. `docs/Guion-Proyecto-Estrella-Jose-Maria-Ortiz.md` — master narrative
2. `docs/plan.md` — detailed implementation plan
3. `pyproject.toml` — single source of truth for deps and entry points
4. `docs/Chuleta.md` — author's interview notes (Spanish)
