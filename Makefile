.PHONY: dev test lint build
dev:
	uv run uvicorn enterpriseagent.main:app --reload
test:
	uv run pytest -v
lint:
	uv run ruff check .
build:
	docker build -t enterpriseagent .
