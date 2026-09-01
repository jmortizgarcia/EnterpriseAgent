FROM ghcr.io/astral-sh/uv:python3.14-alpine AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.14-slim
WORKDIR /app
COPY --from=builder /app/.venv ./.venv
COPY src ./src
COPY data/docs ./data/docs
EXPOSE 8080
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "enterpriseagent.main:app", "--host", "0.0.0.0", "--port", "8080"]
