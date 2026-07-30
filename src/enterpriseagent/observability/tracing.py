from __future__ import annotations

import logging

from enterpriseagent.config import settings

_tracer = None


def _noop(*args, **kwargs):
    pass


class _NoOpTracer:
    create_run = _noop
    update_run = _noop


def get_tracer():
    global _tracer
    if _tracer is not None:
        return _tracer

    if settings.langsmith_api_key:
        try:
            from langsmith import Client as LangSmithClient
            _tracer = LangSmithClient(api_key=settings.langsmith_api_key)
        except Exception as exc:  # noqa: BLE001
            logging.getLogger("enterpriseagent.tracing").warning("LangSmith init failed: %s", exc)
            _tracer = _NoOpTracer()
    else:
        _tracer = _NoOpTracer()

    return _tracer


async def trace_agent_run(
    session_id: str,
    question: str,
    response_content: str | None,
    provider_name: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost: float = 0.0,
    duration_ms: float = 0.0,
    tool_calls: list[str] | None = None,
) -> None:
    tracer = get_tracer()
    if isinstance(tracer, _NoOpTracer):
        return
    try:
        tracer.create_run(
            name="agent_chat",
            run_type="chain",
            inputs={"question": question},
            outputs={"response": response_content},
            extra={
                "session_id": session_id,
                "provider": provider_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "duration_ms": duration_ms,
                "tool_calls": tool_calls or [],
            },
        )
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("enterpriseagent.tracing").warning("LangSmith trace failed: %s", exc)
