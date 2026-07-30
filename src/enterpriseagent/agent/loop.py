from collections.abc import AsyncIterator
from dataclasses import dataclass

from enterpriseagent.agent.graph import (
    MaxIterationsError,  # noqa: F401 — re-exported via agent.__init__
    run_agent_graph,
)
from enterpriseagent.agent.state import AgentState
from enterpriseagent.agent.tools.base import Tool
from enterpriseagent.providers.base import LLMProvider

RAG_SYSTEM_PROMPT = (
    "Eres un asistente de soporte técnico para Nimbus Cloud Platform. Tus respuestas deben:\n"
    "1. Basarse SOLO en las fuentes proporcionadas por la herramienta search_docs\n"
    "2. Citar las fuentes como [1], [2], etc.\n"
    "3. Si no hay información en las fuentes, decirlo explícitamente — NO inventes\n"
    "4. Si el usuario pregunta algo fuera del alcance de la documentación, redirigir amablemente"
)


def find_tool(name: str, tools: list[Tool]) -> Tool | None:
    for t in tools:
        if t.name == name:
            return t
    return None


async def run_agent(
    user_message: str,
    provider: LLMProvider,
    tools: list[Tool] | None = None,
    state: AgentState | None = None,
    fallback_provider: LLMProvider | None = None,
    max_iterations: int = 10,
) -> AgentState:
    final_state = await run_agent_graph(
        user_message=user_message,
        provider=provider,
        tools=tools or [],
        state=state,
        fallback_provider=fallback_provider,
        max_iterations=max_iterations,
    )
    return AgentResponse(
        content=final_state.messages[-1]["content"] if final_state.messages else None,
        state=final_state,
        usage=final_state.context.get("last_response", None) and getattr(final_state.context["last_response"], "usage", None),
    )


async def run_agent_stream(
    user_message: str,
    provider: LLMProvider,
    tools: list[Tool] | None = None,
    state: AgentState | None = None,
) -> AsyncIterator[dict]:
    tools_list = tools or []
    state = state or AgentState()
    if not any(m.get("role") == "system" for m in state.messages):
        state.messages.insert(0, {"role": "system", "content": RAG_SYSTEM_PROMPT})
    state.messages.append({"role": "user", "content": user_message})

    tools_schema = [
        {"name": t.name, "description": t.description, "input_schema": t.input_schema}
        for t in tools_list
    ]

    async for event in provider.generate_stream(state.messages, tools_schema):
        yield event
        if event.get("type") == "tool_use":
            tool = find_tool(event["name"], tools_list)
            if tool:
                try:
                    result = await tool.execute(**event.get("arguments", {}))
                except Exception as e:
                    result = f"Error: {e}"
                state.messages.append({
                    "role": "assistant",
                    "content": f"Tool {event['name']} result: {result}",
                })
                yield {"type": "tool_result", "name": event["name"], "content": result}


@dataclass
class AgentResponse:
    content: str | None
    state: AgentState
    usage: dict | None = None