FROM python:3.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.14-slim
WORKDIR /app
COPY --from=builder /app/.venv ./.venv
COPY src ./src
EXPOSE 8000
CMD [".venv/bin/uvicorn", "enterpriseagent.main:app", "--host", "0.0.0.0", "--port", "8000"]
