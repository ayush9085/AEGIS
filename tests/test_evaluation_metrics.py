"""Unit tests for evaluation metrics calculations and confusion matrices."""

from aegis.evaluation.metrics import compute_evaluation_metrics
from aegis.evaluation.models import (
    CaseExecutionResult,
    CaseExpectation,
    ConfusionMatrix,
    EvaluationCase,
    RuleOutcomeExpectation,
)


def test_confusion_matrix_rates_computation():
    cm = ConfusionMatrix(
        true_positives=8,
        false_positives=2,
        true_negatives=9,
        false_negatives=1,
    )
    cm.compute_rates()

    # Precision = TP / (TP + FP) = 8 / 10 = 0.8
    assert cm.precision == 0.8
    # Recall = TP / (TP + FN) = 8 / 9 = 0.8889
    assert cm.recall == 0.8889
    # F1 Score = 2 * (0.8 * 0.8889) / (0.8 + 0.8889) = 0.8421
    assert cm.f1_score == 0.8421


def test_confusion_matrix_zero_division_safety():
    cm = ConfusionMatrix(
        true_positives=0,
        false_positives=0,
        true_negatives=0,
        false_negatives=0,
    )
    cm.compute_rates()

    assert cm.precision is None
    assert cm.recall is None
    assert cm.f1_score is None


def test_compute_evaluation_metrics_aggregation():
    cases = [
        EvaluationCase(
            case_id="C-01",
            title="Case 1",
            category="normalization",
            description="",
            provenance="synthetic_fixture",
            expectation=CaseExpectation(
                expected_status="passed",
                binary_ground_truth_label="positive",
                rule_expectations=[
                    RuleOutcomeExpectation(rule_id="RULE-BOOT-CHAIN-COMPLETE", expected_outcome="supported")
                ],
            ),
        ),
        EvaluationCase(
            case_id="C-02",
            title="Case 2",
            category="normalization",
            description="",
            provenance="synthetic_fixture",
            expectation=CaseExpectation(
                expected_status="passed",
                binary_ground_truth_label="negative",
                rule_expectations=[
                    RuleOutcomeExpectation(rule_id="RULE-BOOT-CHAIN-COMPLETE", expected_outcome="insufficient_evidence")
                ],
            ),
        ),
    ]

    results = [
        CaseExecutionResult(
            case_id="C-01",
            category="normalization",
            status="passed",
            execution_time_ms=5.0,
            actual_rule_outcomes={"RULE-BOOT-CHAIN-COMPLETE": "supported"},
        ),
        CaseExecutionResult(
            case_id="C-02",
            category="normalization",
            status="passed",
            execution_time_ms=5.0,
            actual_rule_outcomes={"RULE-BOOT-CHAIN-COMPLETE": "insufficient_evidence"},
        ),
    ]

    metrics = compute_evaluation_metrics(cases, results)

    assert metrics.total_cases == 2
    assert metrics.passed == 2
    assert metrics.failed == 0
    assert metrics.overall_pass_rate == 1.0

    # Category breakdown
    norm_cat = metrics.category_breakdown["normalization"]
    assert norm_cat.total_cases == 2
    assert norm_cat.passed == 2
    assert norm_cat.pass_rate == 1.0

    # Rule metrics
    rule_m = metrics.rule_metrics["RULE-BOOT-CHAIN-COMPLETE"]
    assert rule_m.cases_evaluated == 2
    assert rule_m.agreement_count == 2
    assert rule_m.agreement_rate == 1.0

    # Confusion matrix for binary rule
    cm = rule_m.confusion_matrix
    assert cm is not None
    assert cm.true_positives == 1
    assert cm.true_negatives == 1
    assert cm.false_positives == 0
    assert cm.false_negatives == 0
    assert cm.precision == 1.0
    assert cm.recall == 1.0
    assert cm.f1_score == 1.0
