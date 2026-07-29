import pytest

from enterpriseagent.agent.loop import (
    MaxIterationsError,
    find_tool,
    run_agent,
    run_agent_stream,
)
from enterpriseagent.agent.state import AgentState
from enterpriseagent.providers.base import LLMProvider, Response, ToolCall


class MockTextProvider(LLMProvider):
    async def generate(self, messages, tools=None, **kwargs):
        return Response(content="Hello from mock")

    async def generate_stream(self, messages, tools=None, **kwargs):
        yield {"type": "text", "delta": "Hello from mock"}

    def count_tokens(self, text):
        return len(text) // 4


class MockToolProvider(LLMProvider):
    def __init__(self):
        self.call_count = 0

    async def generate(self, messages, tools=None, **kwargs):
        self.call_count += 1
        if self.call_count == 1:
            return Response(
                content=None,
                tool_calls=[
                    ToolCall(id="call_1", name="mock_tool", arguments={"msg": "hi"}),
                ],
                finish_reason="tool_use",
            )
        return Response(content="Done after tool")

    async def generate_stream(self, messages, tools=None, **kwargs):
        yield {"type": "text", "delta": "streaming"}

    def count_tokens(self, text):
        return len(text) // 4


class MockFailingProvider(LLMProvider):
    async def generate(self, messages, tools=None, **kwargs):
        msg = "Mock error"
        raise RuntimeError(msg)

    async def generate_stream(self, messages, tools=None, **kwargs):
        msg = "Mock error"
        raise RuntimeError(msg)

    def count_tokens(self, text):
        return 0


class MockRetryProvider(LLMProvider):
    def __init__(self):
        self.call_count = 0

    async def generate(self, messages, tools=None, **kwargs):
        self.call_count += 1
        if self.call_count < 3:
            msg = f"Attempt {self.call_count} failed"
            raise RuntimeError(msg)
        return Response(content="Success after retry")

    async def generate_stream(self, messages, tools=None, **kwargs):
        yield {"type": "text", "delta": "ok"}

    def count_tokens(self, text):
        return 0


class MockTool:
    def __init__(self):
        self.executed = False
        self.last_args = None

    @property
    def name(self):
        return "mock_tool"

    @property
    def description(self):
        return "A mock tool for testing"

    @property
    def input_schema(self):
        return {
            "type": "object",
            "properties": {"msg": {"type": "string"}},
            "required": ["msg"],
        }

    async def execute(self, msg: str = "") -> str:
        self.executed = True
        self.last_args = {"msg": msg}
        return f"Executed: {msg}"


class MockFailingTool:
    @property
    def name(self):
        return "failing_tool"

    @property
    def description(self):
        return "A tool that fails"

    @property
    def input_schema(self):
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, **kwargs):
        msg = "Tool failure"
        raise RuntimeError(msg)


class TestAgentState:
    def test_default_state(self):
        state = AgentState()
        assert state.messages == []
        assert state.context == {}
        assert state.current_provider == "claude"

    def test_state_with_initial_messages(self):
        state = AgentState(messages=[{"role": "user", "content": "hello"}])
        assert len(state.messages) == 1


class TestFindTool:
    def test_find_existing_tool(self):
        tool = MockTool()
        result = find_tool("mock_tool", [tool])
        assert result is tool

    def test_find_missing_tool(self):
        result = find_tool("nonexistent", [MockTool()])
        assert result is None

    def test_find_empty_list(self):
        result = find_tool("anything", [])
        assert result is None


class TestRunAgent:
    @pytest.mark.asyncio
    async def test_text_response(self):
        result = await run_agent(
            user_message="Hello",
            provider=MockTextProvider(),
        )
        assert result.content == "Hello from mock"
        assert result.state is not None
        assert len(result.state.messages) == 3
        assert result.state.messages[0]["role"] == "system"
        assert result.state.messages[1]["role"] == "user"
        assert result.state.messages[2]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_tool_execution(self):
        tool = MockTool()
        result = await run_agent(
            user_message="Use the tool",
            provider=MockToolProvider(),
            tools=[tool],
        )
        assert result.content == "Done after tool"
        assert tool.executed
        assert tool.last_args == {"msg": "hi"}

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        provider = MockToolProvider()
        result = await run_agent(
            user_message="Use tool",
            provider=provider,
            tools=[],
        )
        assert result.content == "Done after tool"

    @pytest.mark.asyncio
    async def test_provider_fallback(self):
        fallback = MockTextProvider()
        result = await run_agent(
            user_message="Hello",
            provider=MockFailingProvider(),
            fallback_provider=fallback,
        )
        assert result.content == "Hello from mock"

    @pytest.mark.asyncio
    async def test_both_providers_fail(self):
        result = await run_agent(
            user_message="Hello",
            provider=MockFailingProvider(),
            fallback_provider=MockFailingProvider(),
        )
        assert "Lo siento" in result.content

    @pytest.mark.asyncio
    async def test_retry_success(self):
        provider = MockRetryProvider()
        result = await run_agent(
            user_message="Hello",
            provider=provider,
        )
        assert result.content == "Success after retry"
        assert provider.call_count == 3

    @pytest.mark.asyncio
    async def test_max_iterations(self):
        class InfiniteToolProvider(LLMProvider):
            async def generate(self, messages, tools=None, **kwargs):
                return Response(
                    content=None,
                    tool_calls=[
                        ToolCall(id="call_1", name="mock_tool", arguments={}),
                    ],
                    finish_reason="tool_use",
                )

            async def generate_stream(self, messages, tools=None, **kwargs):
                yield {"type": "tool_use", "name": "mock_tool", "arguments": {}}

            def count_tokens(self, text):
                return 0

        tool = MockTool()
        with pytest.raises(MaxIterationsError):
            await run_agent(
                user_message="Loop",
                provider=InfiniteToolProvider(),
                tools=[tool],
                max_iterations=3,
            )

    @pytest.mark.asyncio
    async def test_tool_failure_does_not_crash(self):
        class ToolFailProvider(LLMProvider):
            def __init__(self):
                self.call_count = 0

            async def generate(self, messages, tools=None, **kwargs):
                self.call_count += 1
                if self.call_count == 1:
                    return Response(
                        content=None,
                        tool_calls=[
                            ToolCall(id="call_1", name="failing_tool", arguments={}),
                        ],
                        finish_reason="tool_use",
                    )
                return Response(content="Recovered")

            async def generate_stream(self, messages, tools=None, **kwargs):
                yield {"type": "text", "delta": "ok"}

            def count_tokens(self, text):
                return 0

        result = await run_agent(
            user_message="Use tool",
            provider=ToolFailProvider(),
            tools=[MockFailingTool()],
        )
        assert result.content == "Recovered"

    @pytest.mark.asyncio
    async def test_preserves_state_across_calls(self):
        state = AgentState()
        result1 = await run_agent(
            user_message="First",
            provider=MockTextProvider(),
            state=state,
        )
        result2 = await run_agent(
            user_message="Second",
            provider=MockTextProvider(),
            state=result1.state,
        )
        assert len(result2.state.messages) == 5
        assert result2.state.messages[1]["content"] == "First"
        assert result2.state.messages[3]["content"] == "Second"

    @pytest.mark.asyncio
    async def test_usage_tracked_in_response(self):
        class UsageProvider(MockTextProvider):
            async def generate(self, messages, tools=None, **kwargs):
                return Response(
                    content="Hi",
                    usage={"input_tokens": 10, "output_tokens": 5},
                )

        result = await run_agent(user_message="Hi", provider=UsageProvider())
        assert result.usage == {"input_tokens": 10, "output_tokens": 5}


class TestRunAgentStream:
    @pytest.mark.asyncio
    async def test_stream_text(self):
        events = []
        async for event in run_agent_stream(
            user_message="Hello",
            provider=MockTextProvider(),
        ):
            events.append(event)
        assert len(events) > 0
