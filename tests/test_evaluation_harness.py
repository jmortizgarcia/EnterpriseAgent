
from enterpriseagent.evaluation.harness import EvalReport


class TestEvalReport:
    def test_empty_report(self):
        report = EvalReport()
        assert report.total == 0
        assert report.avg_accuracy == 0.0
        assert report.avg_faithfulness == 0.0
        assert report.total_cost == 0.0

    def test_single_result(self):
        report = EvalReport()
        from enterpriseagent.evaluation.harness import EvalResult
        report.results.append(EvalResult(
            question="test",
            category="factual",
            expected="yes",
            actual="yes",
            accuracy=1.0,
            faithfulness=1.0,
            precision=1.0,
            input_tokens=10,
            output_tokens=5,
            cost=0.001,
            duration_ms=100.0,
        ))
        assert report.total == 1
        assert report.avg_accuracy == 1.0
        assert report.total_cost == 0.001
        assert report.hallucination_rate == 0.0

    def test_hallucination_rate(self):
        report = EvalReport()
        from enterpriseagent.evaluation.harness import EvalResult
        report.results.append(EvalResult(
            question="q1", category="factual", expected="a", actual="a",
            accuracy=1.0, faithfulness=1.0, precision=1.0,
            input_tokens=0, output_tokens=0, cost=0.0, duration_ms=0.0,
        ))
        report.results.append(EvalResult(
            question="q2", category="factual", expected="b", actual="b",
            accuracy=0.5, faithfulness=0.5, precision=0.5,
            input_tokens=0, output_tokens=0, cost=0.0, duration_ms=0.0,
        ))
        assert report.hallucination_rate == 0.5

    def test_by_category(self):
        report = EvalReport()
        from enterpriseagent.evaluation.harness import EvalResult
        report.results.append(EvalResult(
            question="q1", category="factual", expected="a", actual="a",
            accuracy=1.0, faithfulness=1.0, precision=1.0,
            input_tokens=0, output_tokens=0, cost=0.0, duration_ms=0.0,
        ))
        report.results.append(EvalResult(
            question="q2", category="synthetic", expected="b", actual="b",
            accuracy=0.5, faithfulness=0.8, precision=0.5,
            input_tokens=0, output_tokens=0, cost=0.0, duration_ms=0.0,
        ))
        assert len(report.by_category("factual")) == 1
        assert len(report.by_category("synthetic")) == 1
        assert len(report.by_category("no_answer")) == 0

    def test_to_markdown_contains_expected_sections(self):
        report = EvalReport()
        md = report.to_markdown()
        assert "# Reporte de evaluacion" in md
        assert "Total preguntas" in md
