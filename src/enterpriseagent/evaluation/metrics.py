from __future__ import annotations

import re

from enterpriseagent.observability.cost import calculate_cost as _observability_cost


def calculate_cost(provider_name: str, input_tokens: int, output_tokens: int) -> float:
    return _observability_cost(provider_name, input_tokens, output_tokens)


def precision_at_k(
    retrieved_sources: list[str],
    expected_sources: list[str],
    k: int | None = None,
) -> float:
    if not expected_sources:
        return 1.0
    if not retrieved_sources:
        return 0.0
    top = retrieved_sources[:k] if k else retrieved_sources
    expected_set = set(expected_sources)
    matches = sum(1 for s in top if _source_match(s, expected_set))
    return matches / len(top)


def _source_match(source: str, expected_set: set[str]) -> bool:
    filename = _extract_filename(source)
    for exp in expected_set:
        if exp in filename or filename in exp:
            return True
    return False


def _extract_filename(source: str) -> str:
    if "/" in source:
        return source.rsplit("/", 1)[-1]
    return source


ANSWER_PROMPT = """Eres un juez de respuestas. Dada una pregunta, la respuesta esperada y la respuesta generada, evalua del 1 al 10 que tan correcta es la respuesta generada.

Pregunta: {question}
Respuesta esperada: {expected}
Respuesta generada: {actual}

Devuelve SOLO un numero entero del 1 al 10, sin explicacion."""


def parse_judge_score(raw: str) -> float:
    numbers = re.findall(r"\b(\d+)\b", raw)
    if not numbers:
        return 0.0
    score = int(numbers[0])
    return max(1.0, min(10.0, float(score))) / 10.0


HALLUCINATION_PROMPT = """Eres un asistente que detecta alucinaciones. Dada una pregunta, una respuesta y las fuentes disponibles, indica cuantas afirmaciones en la respuesta NO estan respaldadas por las fuentes.

Pregunta: {question}
Respuesta: {actual}
Fuentes: {sources}

Si la respuesta dice que no tiene informacion, la respuesta es correcta (0 alucinaciones).

Devuelve SOLO un numero entero con la cantidad de afirmaciones no respaldadas, sin explicacion."""


async def llm_judge(question: str, expected: str, actual: str | None, provider=None) -> float:
    from enterpriseagent.providers.base import LLMProvider, Response

    if not actual:
        return 0.0

    if provider is not None and isinstance(provider, LLMProvider):
        prompt = ANSWER_PROMPT.format(question=question, expected=expected, actual=actual)
        resp: Response = await provider.generate([
            {"role": "user", "content": prompt},
        ])
        raw = resp.content or ""
        return parse_judge_score(raw)

    return _simple_judge(question, expected, actual)


def _simple_judge(question: str, expected: str, actual: str) -> float:
    a_lower = actual.lower()
    e_lower = expected.lower()

    if "no tengo informacion" in a_lower or "no tengo datos" in a_lower:
        return 1.0 if "no tengo" in e_lower else 0.3

    expected_words = set(e_lower.split())
    actual_words = set(a_lower.split())
    if not expected_words:
        return 0.5
    intersection = expected_words & actual_words
    return len(intersection) / len(expected_words)


async def faithfulness_score(
    question: str,
    actual: str | None,
    sources: str,
    provider=None,
) -> float:
    from enterpriseagent.providers.base import LLMProvider, Response

    if not actual:
        return 0.0

    if provider is not None and isinstance(provider, LLMProvider):
        prompt = HALLUCINATION_PROMPT.format(question=question, actual=actual, sources=sources)
        resp: Response = await provider.generate([
            {"role": "user", "content": prompt},
        ])
        raw = resp.content or ""
        hallucinations = _parse_hallucination_count(raw)
        return max(0.0, 1.0 - hallucinations * 0.33)

    return _simple_faithfulness(actual)


def _parse_hallucination_count(raw: str) -> int:
    numbers = re.findall(r"\b(\d+)\b", raw)
    if not numbers:
        return 0
    return int(numbers[0])


def _simple_faithfulness(actual: str) -> float:
    a_lower = actual.lower()
    if "no tengo informacion" in a_lower or "no tengo datos" in a_lower:
        return 1.0
    return 0.8 if len(actual) > 20 else 0.5
