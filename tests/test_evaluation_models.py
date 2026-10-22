"""Unit tests for evaluation data models, manifest validation, and report schemas."""

import pytest

from aegis.evaluation.models import (
    CaseExecutionResult,
    EvaluationCase,
    EvaluationCompatibilityError,
    EvaluationManifest,
    EvaluationMetrics,
    EvaluationReport,
    EvaluationValidationError,
    validate_evaluation_manifest_dict,
    validate_evaluation_report_dict,
)


def test_manifest_validation_success():
    manifest = EvaluationManifest(
        schema_version="0.1.0",
        corpus_version="0.1.0",
        title="Test Manifest",
        cases=[
            EvaluationCase(
                case_id="TEST-01",
                title="Test Case 1",
                category="normalization",
                description="Sample case",
                provenance="synthetic_fixture",
            )
        ],
    )
    d = manifest.to_dict()
    validate_evaluation_manifest_dict(d)

    roundtrip = EvaluationManifest.from_dict(d)
    assert roundtrip.schema_version == "0.1.0"
    assert len(roundtrip.cases) == 1
    assert roundtrip.cases[0].case_id == "TEST-01"


def test_manifest_duplicate_case_id_rejected():
    data = {
        "schema_version": "0.1.0",
        "corpus_version": "0.1.0",
        "cases": [
            {"case_id": "DUP-01", "category": "normalization"},
            {"case_id": "DUP-01", "category": "graph_integrity"},
        ],
    }
    with pytest.raises(EvaluationValidationError, match="Duplicate case_id"):
        validate_evaluation_manifest_dict(data)


def test_manifest_invalid_category_rejected():
    data = {
        "schema_version": "0.1.0",
        "corpus_version": "0.1.0",
        "cases": [{"case_id": "INV-01", "category": "invalid_category_name"}],
    }
    with pytest.raises(EvaluationValidationError, match="invalid category"):
        validate_evaluation_manifest_dict(data)


def test_manifest_unsupported_schema_version():
    data = {
        "schema_version": "99.0.0",
        "corpus_version": "0.1.0",
        "cases": [],
    }
    with pytest.raises(EvaluationCompatibilityError, match="Unsupported evaluation schema version"):
        validate_evaluation_manifest_dict(data)


def test_evaluation_report_validation_and_reconciliation():
    results = [
        CaseExecutionResult(
            case_id="C-01",
            category="normalization",
            status="passed",
            execution_time_ms=10.0,
        ),
        CaseExecutionResult(
            case_id="C-02",
            category="rule_evaluation",
            status="failed",
            execution_time_ms=12.5,
            message="Rule mismatch",
        ),
    ]

    metrics = EvaluationMetrics(
        total_cases=2,
        passed=1,
        failed=1,
        overall_pass_rate=0.5,
    )

    report = EvaluationReport(
        schema_version="0.1.0",
        corpus_version="0.1.0",
        aegis_version="0.1.0",
        evaluated_at_utc="2026-10-22T00:00:00Z",
        results=results,
        metrics=metrics,
    )

    d = report.to_dict()
    validate_evaluation_report_dict(d)

    roundtrip = EvaluationReport.from_dict(d)
    assert roundtrip.metrics.total_cases == 2
    assert roundtrip.metrics.passed == 1
    assert roundtrip.metrics.failed == 1


def test_evaluation_report_mismatched_counts_rejected():
    results = [
        CaseExecutionResult(
            case_id="C-01",
            category="normalization",
            status="passed",
            execution_time_ms=10.0,
        )
    ]

    # Deliberately mismatched total count
    metrics = EvaluationMetrics(
        total_cases=5,
        passed=1,
        failed=0,
    )

    report = EvaluationReport(
        schema_version="0.1.0",
        corpus_version="0.1.0",
        aegis_version="0.1.0",
        evaluated_at_utc="2026-10-22T00:00:00Z",
        results=results,
        metrics=metrics,
    )

    with pytest.raises(EvaluationValidationError, match="does not match actual results count"):
        validate_evaluation_report_dict(report.to_dict())
