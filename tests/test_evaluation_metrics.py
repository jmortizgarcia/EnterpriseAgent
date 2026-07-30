import pytest

from enterpriseagent.evaluation.metrics import (
    calculate_cost,
    llm_judge,
    parse_judge_score,
    precision_at_k,
)


class TestCalculateCost:
    def test_ollama_is_free(self):
        assert calculate_cost("ollama", 100, 50) == 0.0

    def test_claude_cost(self):
        cost = calculate_cost("claude", 1000, 500)
        assert cost > 0.0
        assert cost < 0.1

    def test_gpt4o_cost(self):
        cost = calculate_cost("openai", 2000, 1000)
        assert cost > 0.0

    def test_unknown_provider_defaults_free(self):
        assert calculate_cost("unknown", 100, 50) == 0.0

    @pytest.mark.parametrize("alias", ["AnthropicProvider", "claude-sonnet-4-6", "claude"])
    def test_claude_aliases(self, alias):
        cost = calculate_cost(alias, 1000, 500)
        assert cost > 0.0

    @pytest.mark.parametrize("alias", ["OpenAIProvider", "gpt-4o", "openai"])
    def test_gpt_aliases(self, alias):
        cost = calculate_cost(alias, 1000, 500)
        assert cost > 0.0


class TestPrecisionAtK:
    def test_perfect_match(self):
        assert precision_at_k(["pricing.md", "slas.md"], ["pricing.md", "slas.md"]) == 1.0

    def test_partial_match(self):
        # 2 retrieved, 1 expected = 0.5 precision
        assert precision_at_k(["pricing.md", "faq.md"], ["pricing.md"]) == 0.5

    def test_no_match(self):
        assert precision_at_k(["faq.md"], ["pricing.md"]) == 0.0

    def test_empty_expected(self):
        assert precision_at_k(["anything.md"], []) == 1.0

    def test_empty_retrieved(self):
        assert precision_at_k([], ["pricing.md"]) == 0.0

    def test_with_k(self):
        result = precision_at_k(
            ["pricing.md", "slas.md", "faq.md"],
            ["pricing.md", "faq.md"],
            k=2,
        )
        assert result == 0.5

    def test_source_with_path(self):
        assert precision_at_k(
            ["data/docs/pricing.md"],
            ["pricing.md"],
        ) == 1.0

    def test_substring_match(self):
        assert precision_at_k(
            ["authentication.md"],
            ["auth"],
        ) == 1.0


class TestParseJudgeScore:
    def test_simple_number(self):
        assert parse_judge_score("8") == 0.8

    def test_number_in_text(self):
        assert parse_judge_score("La respuesta tiene un 7 sobre 10") == 0.7

    def test_clamp_min(self):
        assert parse_judge_score("0") == 0.1

    def test_clamp_max(self):
        assert parse_judge_score("15") == 1.0

    def test_no_number(self):
        assert parse_judge_score("no se") == 0.0


class TestLlmJudge:
    @pytest.mark.asyncio
    async def test_without_provider_uses_simple(self):
        score = await llm_judge("question", "expected answer", "actual answer here")
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_no_answer_detected(self):
        # actual says "no tengo informacion", expected doesn't say "no tengo" -> 0.3
        score = await llm_judge("who founded X?", "No info", "No tengo informacion sobre eso")
        assert score == 0.3

    @pytest.mark.asyncio
    async def test_none_actual(self):
        score = await llm_judge("q", "a", None)
        assert score == 0.0
