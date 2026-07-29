from collections.abc import AsyncIterator

import anthropic
from anthropic.types import MessageParam, ToolParam

from enterpriseagent.config import settings
from enterpriseagent.providers.base import LLMProvider, Response, ToolCall


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key or settings.anthropic_api_key,
        )
        self.model = "claude-sonnet-4-20250514"

    async def generate(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> Response:
        system = self._extract_system(messages)
        provider_messages = self._convert_messages(messages)
        provider_tools = self._convert_tools(tools) if tools else None

        response = await self.client.messages.create(
            model=kwargs.get("model", self.model),
            system=system,
            messages=provider_messages,
            tools=provider_tools,
            max_tokens=kwargs.get("max_tokens", 4096),
        )

        content = None
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )

        return Response(
            content=content,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason or "stop",
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

    async def generate_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> AsyncIterator[dict]:
        system = self._extract_system(messages)
        provider_messages = self._convert_messages(messages)
        provider_tools = self._convert_tools(tools) if tools else None

        async with self.client.messages.stream(
            model=kwargs.get("model", self.model),
            system=system,
            messages=provider_messages,
            tools=provider_tools,
            max_tokens=kwargs.get("max_tokens", 4096),
        ) as stream:
            async for text in stream.text_stream:
                yield {"type": "text", "delta": text}
            final = await stream.get_final_message()
            for block in final.content:
                if block.type == "tool_use":
                    yield {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input,
                    }

    def count_tokens(self, text: str) -> int:
        return self.client.count_tokens(text)

    def _extract_system(self, messages: list[dict]) -> str | None:
        for m in messages:
            if m.get("role") == "system":
                return m["content"]
        return None

    def _convert_messages(self, messages: list[dict]) -> list[MessageParam]:
        return [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m["role"] != "system"
        ]

    def _convert_tools(self, tools: list[dict]) -> list[ToolParam] | None:
        if not tools:
            return None
        return [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t["input_schema"],
            }
            for t in tools
        ]
