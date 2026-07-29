import json
from collections.abc import AsyncIterator

import httpx

from enterpriseagent.config import settings
from enterpriseagent.providers.base import LLMProvider, Response, ToolCall


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
    ):
        self.model = model or settings.ollama_model
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=120)

    async def generate(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> Response:
        body = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "stream": False,
        }
        if tools:
            body["tools"] = self._convert_tools(tools)

        response = await self._client.post("/api/chat", json=body)
        if response.status_code >= 400:
            raise RuntimeError(f"Ollama API error: {response.status_code} {response.text}")
        data = response.json()

        msg = data.get("message", {})
        content = msg.get("content") or None
        tool_calls = []

        for tc in msg.get("tool_calls", []):
            func = tc.get("function", {})
            args = func.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", ""),
                    name=func.get("name", ""),
                    arguments=args,
                )
            )

        return Response(
            content=content,
            tool_calls=tool_calls,
            finish_reason="tool_use" if tool_calls else "stop",
            usage={
                "input_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0),
            },
        )

    async def generate_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> AsyncIterator[dict]:
        body = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "stream": True,
        }
        if tools:
            body["tools"] = self._convert_tools(tools)

        async with self._client.stream("POST", "/api/chat", json=body) as stream:
            async for line in stream.aiter_lines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = data.get("message", {})
                if msg.get("content"):
                    yield {"type": "text", "delta": msg["content"]}
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        func = tc.get("function", {})
                        yield {
                            "type": "tool_use",
                            "id": tc.get("id", ""),
                            "name": func.get("name", ""),
                            "arguments": func.get("arguments", ""),
                        }

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
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
