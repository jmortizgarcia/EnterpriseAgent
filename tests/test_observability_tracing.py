import pytest

from enterpriseagent.observability.tracing import (
    _NoOpTracer,
    get_tracer,
    trace_agent_run,
)


class TestNoOpTracer:
    def test_noop_does_not_raise(self):
        tracer = _NoOpTracer()
        tracer.create_run(name="test")
        tracer.update_run(name="test")

    def test_get_tracer_without_api_key(self):
        tracer = get_tracer()
        assert isinstance(tracer, _NoOpTracer)


class TestTraceAgentRun:
    @pytest.mark.asyncio
    async def test_trace_without_api_key_does_not_raise(self):
        await trace_agent_run(
            session_id="test",
            question="hello",
            response_content="world",
            provider_name="ollama",
        )
