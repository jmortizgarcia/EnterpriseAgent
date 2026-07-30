PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
    "gpt-4o": {"input": 2.5 / 1_000_000, "output": 10.0 / 1_000_000},
    "ollama": {"input": 0.0, "output": 0.0},
}

MODEL_ALIASES: dict[str, str] = {
    "claude": "claude-sonnet-4-6",
    "AnthropicProvider": "claude-sonnet-4-6",
    "openai": "gpt-4o",
    "OpenAIProvider": "gpt-4o",
    "ollama": "ollama",
    "OllamaProvider": "ollama",
    "llama3.2": "ollama",
}


def resolve_model(model_or_provider: str) -> str:
    return MODEL_ALIASES.get(model_or_provider, model_or_provider)


def calculate_cost(model_or_provider: str, input_tokens: int, output_tokens: int) -> float:
    model = resolve_model(model_or_provider)
    p = PRICING.get(model)
    if p is None:
        return 0.0
    return input_tokens * p["input"] + output_tokens * p["output"]
