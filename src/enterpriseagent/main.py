import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from enterpriseagent.agent.loop import run_agent, run_agent_stream
from enterpriseagent.agent.tools import CreateTicket, QueryMetric, SearchDocs
from enterpriseagent.config import settings
from enterpriseagent.providers import (
    AnthropicProvider,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
)

app = FastAPI(title="Enterprise Agent", version="0.1.0")


class ChatRequest(BaseModel):
    message: str
    provider: str | None = None


class ChatResponse(BaseModel):
    content: str | None
    usage: dict | None = None


def get_provider(name: str | None = None) -> LLMProvider:
    provider_name = name or settings.provider
    if provider_name == "openai":
        return OpenAIProvider()
    if provider_name == "ollama":
        return OllamaProvider()
    return AnthropicProvider()


def get_tools() -> list:
    return [SearchDocs(), CreateTicket(), QueryMetric()]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/agent/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    provider = get_provider(request.provider)
    tools = get_tools()
    result = await run_agent(
        user_message=request.message,
        provider=provider,
        tools=tools,
    )
    return ChatResponse(content=result.content, usage=result.usage)


@app.post("/agent/chat/stream")
async def chat_stream(request: ChatRequest):
    provider = get_provider(request.provider)
    tools = get_tools()

    async def event_stream():
        async for event in run_agent_stream(
            user_message=request.message,
            provider=provider,
            tools=tools,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
    )
