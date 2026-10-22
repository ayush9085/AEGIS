"""Unit tests for offline HTML evaluation report generation and strict XSS escaping."""

from aegis.evaluation.html_report import render_evaluation_html_report
from aegis.evaluation.models import CaseExecutionResult, EvaluationMetrics, EvaluationReport


def test_html_evaluation_report_basic_structure():
    report = EvaluationReport(
        schema_version="0.1.0",
        corpus_version="0.1.0",
        aegis_version="0.1.0",
        git_commit="abcdef0",
        evaluated_at_utc="2026-10-22T00:00:00Z",
        results=[
            CaseExecutionResult(
                case_id="TEST-01",
                category="normalization",
                status="passed",
                execution_time_ms=12.3,
                message="Case executed successfully",
            )
        ],
        metrics=EvaluationMetrics(
            total_cases=1,
            passed=1,
            failed=0,
            overall_pass_rate=1.0,
        ),
        reproducibility_hash="1234567890abcdef",
    )

    html_out = render_evaluation_html_report(report)

    assert "<!DOCTYPE html>" in html_out
    assert "AEGIS Evaluation &amp; Reproducibility Report" in html_out
    assert "TEST-01" in html_out
    assert "12.3 ms" in html_out
    # Zero external CDN checks
    assert "http://" not in html_out
    assert "https://" not in html_out
    assert "<script" not in html_out


def test_html_evaluation_report_strict_xss_escaping():
    report = EvaluationReport(
        schema_version="0.1.0",
        corpus_version="0.1.0",
        aegis_version="0.1.0",
        git_commit="<script>alert('commit')</script>",
        evaluated_at_utc="2026-10-22T00:00:00Z",
        results=[
            CaseExecutionResult(
                case_id="<img src=x onerror=alert('xss')>",
                category="<svg onload=alert(1)>",
                status="passed",
                execution_time_ms=5.0,
                message="<b>Dangerous message</b>",
            )
        ],
        metrics=EvaluationMetrics(
            total_cases=1,
            passed=1,
            failed=0,
            overall_pass_rate=1.0,
        ),
    )

    html_out = render_evaluation_html_report(report)

    assert "<script>alert('commit')</script>" not in html_out
    assert "&lt;script&gt;alert(&#x27;commit&#x27;)&lt;/script&gt;" in html_out
    assert "<img src=x onerror=alert('xss')>" not in html_out
    assert "&lt;img src=x onerror=alert(&#x27;xss&#x27;)&gt;" in html_out
    assert "<svg onload=alert(1)>" not in html_out
    assert "&lt;svg onload=alert(1)&gt;" in html_out
    assert "<b>Dangerous message</b>" not in html_out
    assert "&lt;b&gt;Dangerous message&lt;/b&gt;" in html_out
