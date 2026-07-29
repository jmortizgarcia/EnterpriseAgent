import asyncio
import random
from collections.abc import AsyncIterator
from dataclasses import dataclass

from enterpriseagent.agent.state import AgentState
from enterpriseagent.agent.tools.base import Tool
from enterpriseagent.providers.base import LLMProvider, Response


class MaxIterationsError(Exception):
    ...


@dataclass
class AgentResponse:
    content: str | None
    state: AgentState
    usage: dict | None = None


def find_tool(name: str, tools: list[Tool]) -> Tool | None:
    for t in tools:
        if t.name == name:
            return t
    return None


async def _execute_with_retry(
    provider: LLMProvider,
    messages: list[dict],
    tools_schema: list[dict] | None,
    max_retries: int = 3,
) -> Response:
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await provider.generate(messages, tools_schema)
        except Exception as e:  # noqa: BLE001
            last_exception = e
            if attempt < max_retries - 1:
                delay = (2 ** attempt) + random.uniform(0, 0.5)
                await asyncio.sleep(delay)
    raise last_exception  # type: ignore


async def _execute_tool(tool: Tool, arguments: dict, timeout: float = 10.0) -> str:
    try:
        return await asyncio.wait_for(tool.execute(**arguments), timeout=timeout)
    except TimeoutError:
        return f"Error: tool {tool.name} timed out after {timeout}s"
    except Exception as e:  # noqa: BLE001
        return f"Error: tool {tool.name} failed: {e}"


async def run_agent(
    user_message: str,
    provider: LLMProvider,
    tools: list[Tool] | None = None,
    state: AgentState | None = None,
    fallback_provider: LLMProvider | None = None,
    max_iterations: int = 10,
) -> AgentResponse:
    state = state or AgentState()
    state.messages.append({"role": "user", "content": user_message})

    active_provider = provider
    tools_list = tools or []
    tools_schema = [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in tools_list]

    for _ in range(max_iterations):
        try:
            response = await _execute_with_retry(active_provider, state.messages, tools_schema)
        except Exception:  # noqa: BLE001
            if fallback_provider and active_provider is not fallback_provider:
                active_provider = fallback_provider
                try:
                    response = await _execute_with_retry(active_provider, state.messages, tools_schema)
                except Exception as e:  # noqa: BLE001
                    return AgentResponse(
                        content=f"Lo siento, no pude procesar tu solicitud. Error: {e}",
                        state=state,
                    )
            else:
                return AgentResponse(
                    content="Lo siento, no pude procesar tu solicitud. El servicio no está disponible.",
                    state=state,
                )

        if not response.tool_calls:
            state.messages.append({"role": "assistant", "content": response.content})
            return AgentResponse(
                content=response.content,
                state=state,
                usage=response.usage,
            )

        for tc in response.tool_calls:
            tool = find_tool(tc.name, tools_list)
            if tool is None:
                result = f"Error: tool '{tc.name}' not found"
            else:
                result = await _execute_tool(tool, tc.arguments)

            state.messages.append({
                "role": "user" if active_provider.__class__.__name__ == "OpenAIProvider" else "assistant",
                "content": f"Tool {tc.name} result: {result}",
            })

    raise MaxIterationsError(f"Agent exceeded max iterations ({max_iterations})")


async def run_agent_stream(
    user_message: str,
    provider: LLMProvider,
    tools: list[Tool] | None = None,
    state: AgentState | None = None,
) -> AsyncIterator[dict]:
    state = state or AgentState()
    state.messages.append({"role": "user", "content": user_message})

    tools_list = tools or []
    tools_schema = [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in tools_list]

    async for event in provider.generate_stream(state.messages, tools_schema):
        yield event
        if event.get("type") == "tool_use":
            tool = find_tool(event["name"], tools_list)
            if tool:
                result = await _execute_tool(tool, event.get("arguments", {}))
                state.messages.append({
                    "role": "assistant",
                    "content": f"Tool {event['name']} result: {result}",
                })
                yield {"type": "tool_result", "name": event["name"], "content": result}
