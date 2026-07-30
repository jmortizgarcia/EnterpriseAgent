from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from enterpriseagent.agent.loop import run_agent
from enterpriseagent.evaluation.dataset import EVAL_DATASET, EvalItem
from enterpriseagent.evaluation.metrics import (
    calculate_cost,
    faithfulness_score,
    llm_judge,
    precision_at_k,
)
from enterpriseagent.providers.base import LLMProvider


@dataclass
class EvalResult:
    question: str
    category: str
    expected: str
    actual: str | None
    accuracy: float
    faithfulness: float
    precision: float
    input_tokens: int
    output_tokens: int
    cost: float
    duration_ms: float


@dataclass
class EvalReport:
    results: list[EvalResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def avg_accuracy(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.accuracy for r in self.results) / len(self.results)

    @property
    def avg_faithfulness(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.faithfulness for r in self.results) / len(self.results)

    @property
    def avg_precision(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.precision for r in self.results) / len(self.results)

    @property
    def total_cost(self) -> float:
        return sum(r.cost for r in self.results)

    @property
    def total_tokens(self) -> int:
        return sum(r.input_tokens + r.output_tokens for r in self.results)

    @property
    def hallucination_rate(self) -> float:
        if not self.results:
            return 0.0
        low_faith = [r for r in self.results if r.faithfulness < 0.7]
        return len(low_faith) / len(self.results)

    def by_category(self, category: str) -> list[EvalResult]:
        return [r for r in self.results if r.category == category]

    def to_markdown(self) -> str:
        lines = [
            "# Reporte de evaluacion",
            "",
            f"**Total preguntas:** {self.total}",
            f"**Accuracy promedio:** {self.avg_accuracy:.2%}",
            f"**Faithfulness promedio:** {self.avg_faithfulness:.2%}",
            f"**Precision promedio:** {self.avg_precision:.2%}",
            f"**Tasa de alucinacion:** {self.hallucination_rate:.2%}",
            f"**Coste total:** ${self.total_cost:.4f}",
            f"**Tokens totales:** {self.total_tokens}",
            "",
            "## Resultados por categoria",
            "",
        ]
        for cat in ("factual", "synthetic", "no_answer", "edge"):
            items = self.by_category(cat)
            if items:
                avg_acc = sum(i.accuracy for i in items) / len(items)
                avg_faith = sum(i.faithfulness for i in items) / len(items)
                cat_name = {
                    "factual": "Factual directa",
                    "synthetic": "Sintetica",
                    "no_answer": "Sin respuesta en docs",
                    "edge": "Borde/ambiguas",
                }.get(cat, cat)
                lines.append(f"### {cat_name} ({len(items)})")
                lines.append(f"- Accuracy: {avg_acc:.2%}")
                lines.append(f"- Faithfulness: {avg_faith:.2%}")
                lines.append("")

        lines.extend([
            "## Detalle por pregunta",
            "",
            "| # | Categoria | Pregunta | Accuracy | Faithfulness | Precision | Coste |",
            "|---|-----------|----------|----------|--------------|-----------|-------|",
        ])
        for i, r in enumerate(self.results, 1):
            short_q = r.question[:50] + "..." if len(r.question) > 50 else r.question
            lines.append(
                f"| {i} | {r.category} | {short_q} | {r.accuracy:.2%} | "
                f"{r.faithfulness:.2%} | {r.precision:.2%} | ${r.cost:.4f} |"
            )
        lines.append("")
        return "\n".join(lines)


async def run_evaluation(
    dataset: list[EvalItem],
    provider: LLMProvider,
    tools: list,
    judge_provider: LLMProvider | None = None,
) -> EvalReport:
    report = EvalReport()

    for item in dataset:
        t0 = time.monotonic()
        try:
            result = await run_agent(
                user_message=item.question,
                provider=provider,
                tools=tools,
            )
            actual = result.content
            usage = result.usage or {}
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
        except Exception:  # noqa: BLE001
            actual = None
            input_tokens = 0
            output_tokens = 0

        duration_ms = (time.monotonic() - t0) * 1000
        cost = calculate_cost(provider.__class__.__name__, input_tokens, output_tokens)
        accuracy = await llm_judge(item.question, item.expected_answer, actual, judge_provider)
        faithfulness = await faithfulness_score(
            item.question, actual, ", ".join(item.expected_sources), judge_provider,
        )
        precision = precision_at_k(
            item.expected_sources if item.category != "no_answer" else [],
            item.expected_sources,
        )

        report.results.append(EvalResult(
            question=item.question,
            category=item.category,
            expected=item.expected_answer,
            actual=actual,
            accuracy=accuracy,
            faithfulness=faithfulness,
            precision=precision,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            duration_ms=duration_ms,
        ))

        print(f"  [{item.category:>12}] {item.question[:60]:60s} acc={accuracy:.2f}")

    return report


async def main(output: str = "eval-report.md") -> None:
    from enterpriseagent.agent.tools import CreateTicket, QueryMetric, SearchDocs
    from enterpriseagent.config import settings
    from enterpriseagent.providers import (
        AnthropicProvider,
        OllamaProvider,
        OpenAIProvider,
    )
    from enterpriseagent.rag.vector_store import ChromaStore

    provider_name = settings.provider
    if provider_name == "openai":
        provider = OpenAIProvider()
    elif provider_name == "ollama":
        provider = OllamaProvider()
    else:
        provider = AnthropicProvider()

    judge = provider if provider_name != "ollama" else None

    tools = [SearchDocs(store=ChromaStore()), CreateTicket(), QueryMetric()]

    print(f"Evaluando con proveedor: {provider_name}")
    print(f"Dataset: {len(EVAL_DATASET)} preguntas")
    print()

    report = await run_evaluation(EVAL_DATASET, provider, tools, judge)

    md = report.to_markdown()
    def _write():
        with open(output, "w", encoding="utf-8") as f:
            f.write(md)
    await asyncio.to_thread(_write)

    print(f"\nReporte guardado en {output}")
    print(f"Accuracy: {report.avg_accuracy:.2%}")
    print(f"Faithfulness: {report.avg_faithfulness:.2%}")
    print(f"Hallucination rate: {report.hallucination_rate:.2%}")
    print(f"Coste: ${report.total_cost:.4f}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="eval-report.md")
    args = parser.parse_args()
    asyncio.run(main(output=args.output))
