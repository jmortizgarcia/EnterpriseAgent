import pytest

from enterpriseagent.observability.cost import calculate_cost, resolve_model


class TestResolveModel:
    def test_claude_alias(self):
        assert resolve_model("claude") == "claude-sonnet-4-6"

    def test_provider_class_name(self):
        assert resolve_model("AnthropicProvider") == "claude-sonnet-4-6"

    def test_ollama_passthrough(self):
        assert resolve_model("llama3.2") == "ollama"

    def test_unknown_passthrough(self):
        assert resolve_model("custom-model") == "custom-model"


class TestCalculateCost:
    def test_ollama_free(self):
        assert calculate_cost("ollama", 100, 50) == 0.0

    def test_claude_pricing(self):
        cost = calculate_cost("claude", 1_000_000, 500_000)
        expected_input = 1_000_000 * (3.0 / 1_000_000)
        expected_output = 500_000 * (15.0 / 1_000_000)
        assert cost == pytest.approx(expected_input + expected_output)

    def test_gpt4o_pricing(self):
        cost = calculate_cost("gpt-4o", 1_000_000, 500_000)
        expected_input = 1_000_000 * (2.5 / 1_000_000)
        expected_output = 500_000 * (10.0 / 1_000_000)
        assert cost == pytest.approx(expected_input + expected_output)

    def test_zero_tokens(self):
        assert calculate_cost("claude", 0, 0) == 0.0

    @pytest.mark.parametrize("provider", ["OllamaProvider", "llama3.2"])
    def test_ollama_aliases_free(self, provider):
        assert calculate_cost(provider, 1000, 500) == 0.0

    def test_unknown_model_free(self):
        assert calculate_cost("nonexistent", 1000, 500) == 0.0
