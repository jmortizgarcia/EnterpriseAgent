import json
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from enterpriseagent.config import settings
from enterpriseagent.providers.base import LLMProvider, Response, ToolCall


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        self.client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
        )
        self.model = "gpt-4o"

    async def generate(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> Response:
        provider_tools = self._convert_tools(tools) if tools else None

        response = await self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=messages,
            tools=provider_tools,
            max_tokens=kwargs.get("max_tokens", 4096),
        )

        choice = response.choices[0]
        message = choice.message

        content = message.content or None
        tool_calls = []

        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                )

        return Response(
            content=content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }
            if response.usage
            else None,
        )

    async def generate_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> AsyncIterator[dict]:
        provider_tools = self._convert_tools(tools) if tools else None

        stream = await self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=messages,
            tools=provider_tools,
            max_tokens=kwargs.get("max_tokens", 4096),
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue
            if delta.content:
                yield {"type": "text", "delta": delta.content}
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    yield {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments if tc.function else "",
                    }

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

    def _convert_tools(self, tools: list[dict]) -> list[dict] | None:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t["input_schema"],
                },
            }
            for t in tools
        ]
