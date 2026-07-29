# AGENTS.md

## Identity

This is **Proyecto Estrella** — an enterprise AI agent built as a portfolio project targeting Accenture **AI LLM Junior Technology Architect** and **AI Software Engineer** roles.

## Source of truth

Read `docs/Guion-Proyecto-Estrella-Jose-Maria-Ortiz.md` first. It is the master narrative. `docs/plan.md` is the tactical breakdown (Spanish); `docs/Chuleta.md` is the author's interview-prep cheat sheet (Spanish).

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.14 (`.python-version`, `pyproject.toml` — docs say 3.12, repo is 3.14) |
| Package mgr | `uv` |
| API | FastAPI + pydantic |
| LLMs | Anthropic Claude (primary), OpenAI (secondary — abstraction layer) |
| Orchestration | Custom loop → LangGraph (Sprint 3) |
| RAG | Chroma (local) → pgvector (prod) |
| Eval | Custom harness + Ragas |
| Guardrails | I/O validation + Presidio (PII) |
| Container | Docker |
| Cloud | Cloud Run |
| CI/CD | GitHub Actions |

## Package layout

```
src/enterpriseagent/   # package root (matches pyproject.toml `name`)
├── __init__.py          # must define main() — entry point `enterpriseagent:main`
├── main.py              # FastAPI app
├── config.py            # pydantic-settings
├── agent/
├── providers/
│   ├── __init__.py
│   ├── base.py           # LLMProvider ABC + ToolCall/Response
│   ├── anthropic.py      # Anthropic Claude implementation
│   └── openai.py         # OpenAI GPT-4o implementation
├── rag/
├── memory/
├── guardrails/
├── evaluation/
└── observability/
```

## Essential commands

```powershell
uv sync                                 # install deps
uv run uvicorn enterpriseagent.main:app --reload   # dev server
uv run pytest -v                        # all tests
uv run pytest -v -k test_name           # single test
uv run ruff check .                     # lint
uv run ruff check --fix .               # lint + autofix
```

## Critical conventions

- **Always use `enterpriseagent.` prefix** for Python module paths (e.g. `enterpriseagent.main:app`), never `src.`.
- Python 3.14 is the real version; `docs/plan.md` and the guion say 3.12 — treat as stale on this point.
- Sprint 0 complete: CI/GitHub Actions, Makefile, Dockerfile, test_health.py committed.
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
