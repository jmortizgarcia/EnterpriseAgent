.PHONY: dev test lint build ingest eval
dev:
	uv run uvicorn enterpriseagent.main:app --reload
test:
	uv run pytest -v
lint:
	uv run ruff check .
build:
	docker build -t enterpriseagent .
ingest:
	uv run python -m enterpriseagent.rag.ingestion
eval:
	uv run python -m enterpriseagent.evaluation.harness --output eval-report.md
