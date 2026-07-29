from unittest.mock import AsyncMock

import pytest
from httpx import Response

from enterpriseagent.config import settings
from enterpriseagent.providers.ollama import OllamaProvider


class TestOllamaProvider:
    def test_init_defaults(self):
        provider = OllamaProvider()
        assert provider.model == settings.ollama_model
        assert provider.base_url == settings.ollama_base_url.rstrip("/")

    def test_init_custom(self):
        provider = OllamaProvider(model="llama3.2:1b", base_url="http://localhost:11434")
        assert provider.model == "llama3.2:1b"

    def test_count_tokens(self):
        provider = OllamaProvider()
        assert provider.count_tokens("hello world") == 2
        assert provider.count_tokens("a" * 40) == 10

    @pytest.mark.asyncio
    async def test_generate_text(self):
        mock_response = {
            "model": "llama3.2",
            "message": {"role": "assistant", "content": "Hello from Ollama"},
            "done": True,
            "prompt_eval_count": 10,
            "eval_count": 5,
        }

        provider = OllamaProvider()
        provider._client = AsyncMock()
        provider._client.post.return_value = Response(
            status_code=200,
            json=mock_response,
        )

        result = await provider.generate(
            [{"role": "user", "content": "Say hello"}],
        )
        assert result.content == "Hello from Ollama"
        assert result.tool_calls == []
        assert result.usage == {"input_tokens": 10, "output_tokens": 5}

    @pytest.mark.asyncio
    async def test_generate_with_tools(self):
        mock_response = {
            "model": "llama3.2",
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_weather",
                            "arguments": {"city": "Madrid"},
                        },
                    },
                ],
            },
            "done": True,
            "prompt_eval_count": 15,
            "eval_count": 8,
        }

        provider = OllamaProvider()
        provider._client = AsyncMock()
        provider._client.post.return_value = Response(
            status_code=200,
            json=mock_response,
        )

        tools = [
            {
                "name": "get_weather",
                "description": "Get weather",
                "input_schema": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        ]
        result = await provider.generate(
            [{"role": "user", "content": "Weather in Madrid?"}],
            tools=tools,
        )
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "get_weather"
        assert result.tool_calls[0].arguments == {"city": "Madrid"}
        assert result.finish_reason == "tool_use"

    @pytest.mark.asyncio
    async def test_generate_with_tools_string_args(self):
        mock_response = {
            "model": "llama3.2",
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"city": "Barcelona"}',
                        },
                    },
                ],
            },
            "done": True,
            "prompt_eval_count": 15,
            "eval_count": 8,
        }

        provider = OllamaProvider()
        provider._client = AsyncMock()
        provider._client.post.return_value = Response(
            status_code=200,
            json=mock_response,
        )

        result = await provider.generate(
            [{"role": "user", "content": "Weather in Barcelona?"}],
        )
        assert result.tool_calls[0].arguments == {"city": "Barcelona"}

    @pytest.mark.asyncio
    async def test_generate_stream(self):
        from unittest.mock import MagicMock

        lines = [
            b'{"message":{"content":"Hello"}}\n',
            b'{"message":{"content":" world"}}\n',
            b'{"message":{"content":"","tool_calls":[{"function":{"name":"test","arguments":{}}}]}}\n',
        ]

        class MockStream:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def aiter_lines(self):
                for line in lines:
                    yield line.decode()

        provider = OllamaProvider()
        provider._client = MagicMock()
        provider._client.stream.return_value = MockStream()

        events = []
        async for event in provider.generate_stream(
            [{"role": "user", "content": "Hi"}],
        ):
            events.append(event)

        assert len(events) == 3
        assert events[0] == {"type": "text", "delta": "Hello"}
        assert events[1] == {"type": "text", "delta": " world"}
        assert events[2]["type"] == "tool_use"

    @pytest.mark.asyncio
    async def test_api_error(self):
        provider = OllamaProvider()
        provider._client = AsyncMock()
        provider._client.post.return_value = Response(
            status_code=500,
            text="Internal Server Error",
        )

        with pytest.raises(RuntimeError):
            await provider.generate(
                [{"role": "user", "content": "Hi"}],
            )
