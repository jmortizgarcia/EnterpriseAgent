import asyncio
import random

from langgraph.errors import GraphRecursionError
from langgraph.graph import END, StateGraph

from enterpriseagent.agent.orchestrator import (
    classify_intent,
    filter_tools_for_intent,
    supervisor_prompt,
)
from enterpriseagent.agent.state import AgentState
from enterpriseagent.agent.tools.base import Tool
from enterpriseagent.providers.base import LLMProvider, Response


class MaxIterationsError(Exception):
    ...


def _tools_schema(tools: list[Tool]) -> list[dict]:
    return [
        {"name": t.name, "description": t.description, "input_schema": t.input_schema}
        for t in tools
    ]


def _find_tool(name: str, tools: list[Tool]) -> Tool | None:
    for t in tools:
        if t.name == name:
            return t
    return None


def build_agent_graph(
    provider: LLMProvider,
    tools: list[Tool],
    fallback_provider: LLMProvider | None = None,
    use_supervisor: bool = True,
):
    all_tools = tools

    async def supervisor(state: AgentState) -> dict:
        last_msg = state.messages[-1]["content"] if state.messages else ""
        intent = classify_intent(last_msg)
        state.context["intent"] = intent
        state.context["tools"] = filter_tools_for_intent(all_tools, intent)
        # replace system prompt with specialized one
        for i, m in enumerate(state.messages):
            if m.get("role") == "system":
                state.messages[i] = {"role": "system", "content": supervisor_prompt(intent)}
                break
        return {"messages": state.messages, "context": state.context}

    def _get_active_tools(ctx: dict) -> list[Tool]:
        if use_supervisor and "tools" in ctx:
            return ctx["tools"]
        return all_tools

    def _get_active_schema(ctx: dict) -> list[dict]:
        return _tools_schema(_get_active_tools(ctx))

    async def call_llm(state: AgentState) -> dict:
        active = provider
        last_error: Exception | None = None
        schema = _get_active_schema(state.context)

        for attempt in range(3):
            try:
                response = await active.generate(state.messages, schema)
                state.context["last_response"] = response
                return {"context": state.context}
            except Exception as e:
                last_error = e
                if attempt < 2:
                    delay = (2**attempt) + random.uniform(0, 0.5)
                    await asyncio.sleep(delay)

        if fallback_provider and active is not fallback_provider:
            try:
                response = await fallback_provider.generate(state.messages, schema)
                state.context["last_response"] = response
                return {"context": state.context}
            except Exception as e:
                state.context["error"] = str(e)
                return {"context": state.context}

        state.context["error"] = str(last_error) if last_error else "Unknown error"
        return {"context": state.context}

    async def execute_tool(state: AgentState) -> dict:
        response: Response | None = state.context.get("last_response")
        if not response or not response.tool_calls:
            return {}

        active_tools = _get_active_tools(state.context)

        for tc in response.tool_calls:
            tool = _find_tool(tc.name, active_tools)
            if tool is None:
                result = f"Error: tool '{tc.name}' not found"
            else:
                try:
                    result = await asyncio.wait_for(tool.execute(**tc.arguments), timeout=10.0)
                except TimeoutError:
                    result = f"Error: tool {tc.name} timed out"
                except Exception as e:
                    result = f"Error: tool {tc.name} failed: {e}"

            role = "user" if provider.__class__.__name__ == "OpenAIProvider" else "assistant"
            state.messages.append({"role": role, "content": f"Tool {tc.name} result: {result}"})

        state.context.pop("last_response", None)
        return {"messages": state.messages, "context": state.context}

    def decide_next(state: AgentState) -> str:
        if state.context.get("error"):
            return "error"
        response: Response | None = state.context.get("last_response")
        if response and response.tool_calls:
            return "execute_tool"
        return "respond"

    def decide_routing(state: AgentState) -> str:
        intent = state.context.get("intent", "documentation")
        if intent == "action":
            return "actions_agent"
        return "docs_agent"

    workflow = StateGraph(AgentState)

    if use_supervisor:
        workflow.add_node("supervisor", supervisor)
        workflow.add_node("call_llm", call_llm)
        workflow.add_node("execute_tool", execute_tool)

        workflow.set_entry_point("supervisor")

        workflow.add_conditional_edges(
            "supervisor",
            decide_routing,
            {"docs_agent": "call_llm", "actions_agent": "call_llm"},
        )

        workflow.add_conditional_edges(
            "call_llm",
            decide_next,
            {"execute_tool": "execute_tool", "respond": END, "error": END},
        )
        workflow.add_edge("execute_tool", "call_llm")
    else:
        workflow.add_node("call_llm", call_llm)
        workflow.add_node("execute_tool", execute_tool)

        workflow.set_entry_point("call_llm")

        workflow.add_conditional_edges(
            "call_llm",
            decide_next,
            {"execute_tool": "execute_tool", "respond": END, "error": END},
        )
        workflow.add_edge("execute_tool", "call_llm")

    return workflow.compile()


async def run_agent_graph(
    user_message: str,
    provider: LLMProvider,
    tools: list[Tool] | None = None,
    state: AgentState | None = None,
    fallback_provider: LLMProvider | None = None,
    max_iterations: int = 10,
    use_supervisor: bool = True,
) -> AgentState:
    tools_list = tools or []
    state = state or AgentState()
    # inject default system prompt (may be replaced by supervisor)
    if not any(m.get("role") == "system" for m in state.messages):
        from enterpriseagent.agent.loop import RAG_SYSTEM_PROMPT
        state.messages.insert(0, {"role": "system", "content": RAG_SYSTEM_PROMPT})
    state.messages.append({"role": "user", "content": user_message})

    graph = build_agent_graph(provider, tools_list, fallback_provider, use_supervisor)

    try:
        for _ in range(max_iterations):
            result = await graph.ainvoke(state)
            if isinstance(result, dict):
                state = AgentState(
                    messages=result.get("messages", state.messages),
                    context=result.get("context", state.context),
                    current_provider=result.get("current_provider", state.current_provider),
                )
            else:
                state = result
            if state.context.get("error"):
                final = state.context.pop("error", "")
                state.messages.append({"role": "assistant", "content": f"Lo siento, no pude procesar tu solicitud. Error: {final}"})
                return state
            last: Response | None = state.context.get("last_response")
            if last and not last.tool_calls:
                state.messages.append({"role": "assistant", "content": last.content})
                return state
    except GraphRecursionError:
        raise MaxIterationsError("Agent exceeded max iterations")

    state.messages.append({"role": "assistant", "content": "Lo siento, no pude procesar tu solicitud. Límite de iteraciones alcanzado."})
    return state