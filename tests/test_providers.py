
import pytest

from enterpriseagent.config import settings
from enterpriseagent.providers.base import LLMProvider, Response, ToolCall


class TestToolCall:
    def test_toolcall_creation(self):
        tc = ToolCall(id="call_1", name="search_docs", arguments={"query": "hello"})
        assert tc.id == "call_1"
        assert tc.name == "search_docs"
        assert tc.arguments == {"query": "hello"}


class TestResponse:
    def test_response_defaults(self):
        r = Response(content="Hello")
        assert r.content == "Hello"
        assert r.tool_calls == []
        assert r.finish_reason == "stop"
        assert r.usage is None

    def test_response_with_tool_calls(self):
        tc = ToolCall(id="call_1", name="search_docs", arguments={"query": "test"})
        r = Response(content=None, tool_calls=[tc], finish_reason="tool_use")
        assert r.content is None
        assert len(r.tool_calls) == 1
        assert r.finish_reason == "tool_use"


class TestLLMProvider:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            LLMProvider()

    def test_concrete_subclass_must_implement_all_methods(self):
        class Incomplete(LLMProvider):
            pass

        with pytest.raises(TypeError):
            Incomplete()


class TestAnthropicProvider:
    def test_init(self):
        from enterpriseagent.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider(api_key="test-key")
        assert provider.model == "claude-sonnet-4-20250514"

    @pytest.mark.skipif(
        not settings.anthropic_api_key,
        reason="ANTHROPIC_API_KEY not set",
    )
    @pytest.mark.asyncio
    async def test_generate_text(self):
        from enterpriseagent.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider()
        response = await provider.generate(
            [{"role": "user", "content": "Say 'hello world' and nothing else"}],
            max_tokens=50,
        )
        assert response.content is not None
        assert "hello" in response.content.lower()
        assert response.usage is not None

    @pytest.mark.skipif(
        not settings.anthropic_api_key,
        reason="ANTHROPIC_API_KEY not set",
    )
    @pytest.mark.asyncio
    async def test_generate_with_tools(self):
        from enterpriseagent.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider()
        tools = [
            {
                "name": "get_weather",
                "description": "Get the weather for a city",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                    },
                    "required": ["city"],
                },
            }
        ]
        response = await provider.generate(
            [{"role": "user", "content": "What is the weather in Madrid?"}],
            tools=tools,
            max_tokens=100,
        )
        assert len(response.tool_calls) > 0
        assert response.tool_calls[0].name == "get_weather"

    @pytest.mark.skipif(
        not settings.anthropic_api_key,
        reason="ANTHROPIC_API_KEY not set",
    )
    @pytest.mark.asyncio
    async def test_generate_stream(self):
        from enterpriseagent.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider()
        chunks = []
        async for chunk in provider.generate_stream(
            [{"role": "user", "content": "Say 'hello'"}],
            max_tokens=50,
        ):
            chunks.append(chunk)
        assert len(chunks) > 0


class TestOpenAIProvider:
    def test_init(self):
        from enterpriseagent.providers.openai import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key")
        assert provider.model == "gpt-4o"

    @pytest.mark.skipif(
        not settings.openai_api_key,
        reason="OPENAI_API_KEY not set",
    )
    @pytest.mark.asyncio
    async def test_generate_text(self):
        from enterpriseagent.providers.openai import OpenAIProvider

        provider = OpenAIProvider()
        response = await provider.generate(
            [{"role": "user", "content": "Say 'hello world' and nothing else"}],
            max_tokens=50,
        )
        assert response.content is not None
        assert "hello" in response.content.lower()
        assert response.usage is not None

    @pytest.mark.skipif(
        not settings.openai_api_key,
        reason="OPENAI_API_KEY not set",
    )
    @pytest.mark.asyncio
    async def test_generate_with_tools(self):
        from enterpriseagent.providers.openai import OpenAIProvider

        provider = OpenAIProvider()
        tools = [
            {
                "name": "get_weather",
                "description": "Get the weather for a city",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                    },
                    "required": ["city"],
                },
            }
        ]
        response = await provider.generate(
            [{"role": "user", "content": "What is the weather in Madrid?"}],
            tools=tools,
            max_tokens=100,
        )
        assert len(response.tool_calls) > 0
        call_args = response.tool_calls[0].arguments
        assert call_args.get("city", "").lower() == "madrid"

    @pytest.mark.skipif(
        not settings.openai_api_key,
        reason="OPENAI_API_KEY not set",
    )
    @pytest.mark.asyncio
    async def test_generate_stream(self):
        from enterpriseagent.providers.openai import OpenAIProvider

        provider = OpenAIProvider()
        chunks = []
        async for chunk in provider.generate_stream(
            [{"role": "user", "content": "Say 'hello'"}],
            max_tokens=50,
        ):
            chunks.append(chunk)
        assert len(chunks) > 0
