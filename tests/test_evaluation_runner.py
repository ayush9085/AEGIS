"""Unit tests for EvaluationRunner execution and ground-truth verification."""

from aegis.evaluation.corpus import load_default_manifest
from aegis.evaluation.models import (
    CaseExpectation,
    EvaluationCase,
    RuleOutcomeExpectation,
)
from aegis.evaluation.runner import EvaluationRunner


def test_runner_executes_single_valid_case():
    manifest = load_default_manifest()
    case = next(c for c in manifest.cases if c.case_id == "NORM-01-VALID-PHASE1")

    runner = EvaluationRunner()
    result = runner.run_case(case)

    assert result.status == "passed"
    assert result.case_id == "NORM-01-VALID-PHASE1"
    assert result.actual_rule_outcomes.get("RULE-BOOT-CHAIN-COMPLETE") == "supported"
    assert result.execution_time_ms > 0


def test_runner_handles_expected_exception():
    case = EvaluationCase(
        case_id="ERR-01-EXPECTED",
        title="Expected Syntax Error",
        category="normalization",
        description="",
        provenance="synthetic_fixture",
        inputs=[{"type": "malformed_json", "name": "bad.json", "raw": "not valid json"}],
        expectation=CaseExpectation(
            expected_status="passed",
            expected_exception_type="ResearchValidationError",
            expected_exception_message_substring="Failed to read/parse JSON",
        ),
    )

    runner = EvaluationRunner()
    result = runner.run_case(case)

    assert result.status == "passed"
    assert not result.differences


def test_runner_detects_mismatched_rule_expectation():
    case = EvaluationCase(
        case_id="MISMATCH-01",
        title="Deliberate Mismatch",
        category="rule_evaluation",
        description="",
        provenance="synthetic_fixture",
        inputs=[{"type": "inline_json", "name": "dev.json", "data": {
            "schema_version": "0.1.0",
            "device": {"model": "Pixel 8"},
            "observations": [],
        }}],
        expectation=CaseExpectation(
            expected_status="passed",
            rule_expectations=[
                # Deliberately expect 'supported' when no bootloader observations exist
                RuleOutcomeExpectation(rule_id="RULE-BOOT-CHAIN-COMPLETE", expected_outcome="supported")
            ],
        ),
    )

    runner = EvaluationRunner()
    result = runner.run_case(case)

    # Must fail because actual outcome was 'insufficient_evidence', not 'supported'
    assert result.status == "failed"
    assert any("expected outcome 'supported'" in d for d in result.differences)


def test_runner_default_manifest_full_execution():
    manifest = load_default_manifest()
    runner = EvaluationRunner()
    report = runner.run_manifest(manifest)

    assert report.metrics.total_cases == len(manifest.cases)
    assert report.metrics.failed == 0
    assert report.metrics.passed + report.metrics.skipped == report.metrics.total_cases
    assert report.metrics.overall_pass_rate >= 0.97
    assert report.reproducibility_hash != ""


def test_runner_skips_when_fixture_file_missing():
    case = EvaluationCase(
        case_id="SKIP-01",
        title="Missing Fixture File",
        category="reproducibility",
        description="",
        provenance="physical_handset",
        inputs=[{"type": "file_path", "path": "nonexistent/fixture/path/evidence.json"}],
        expectation=CaseExpectation(expected_status="passed"),
    )
    runner = EvaluationRunner()
    result = runner.run_case(case)
    assert result.status == "skipped"
    assert "safely skipped" in result.message

