import pytest

from enterpriseagent.agent.orchestrator import (
    classify_intent,
    filter_tools_for_intent,
    supervisor_prompt,
)
from enterpriseagent.agent.tools.create_ticket import CreateTicket
from enterpriseagent.agent.tools.query_metric import QueryMetric
from enterpriseagent.agent.tools.search_docs import SearchDocs


class TestClassifyIntent:
    def test_documentation_query(self):
        intent = classify_intent("¿Cuál es el SLA del plan enterprise?")
        assert intent == "documentation"

    def test_action_query(self):
        intent = classify_intent("Crea un ticket de alta prioridad para la CPU")
        assert intent == "action"

    def test_metric_query(self):
        intent = classify_intent("Revisa la memoria del servidor y la cpu")
        assert intent == "action"

    def test_pricing_query(self):
        intent = classify_intent("Cuánto cuesta el plan Pro?")
        assert intent == "documentation"

    def test_mixed_query_docs_wins(self):
        intent = classify_intent("Hola")
        assert intent == "documentation"

    def test_greeting_defaults_to_docs(self):
        intent = classify_intent("Hola, buen día")
        assert intent == "documentation"


class TestFilterTools:
    @pytest.fixture
    def tools(self):
        return [SearchDocs(), CreateTicket(), QueryMetric()]

    def test_docs_agent_only_search(self, tools):
        filtered = filter_tools_for_intent(tools, "documentation")
        names = [t.name for t in filtered]
        assert "search_docs" in names
        assert "create_ticket" not in names
        assert "query_metric" not in names

    def test_actions_agent_no_search(self, tools):
        filtered = filter_tools_for_intent(tools, "action")
        names = [t.name for t in filtered]
        assert "search_docs" not in names
        assert "create_ticket" in names
        assert "query_metric" in names

    def test_unknown_intent_returns_all(self, tools):
        filtered = filter_tools_for_intent(tools, "unknown")
        assert len(filtered) == 3


class TestSupervisorPrompt:
    def test_docs_prompt_mentions_sources(self):
        prompt = supervisor_prompt("documentation")
        assert "search_docs" in prompt
        assert "fuentes" in prompt or "sources" in prompt

    def test_actions_prompt_mentions_metrics(self):
        prompt = supervisor_prompt("action")
        assert "métricas" in prompt or "tickets" in prompt