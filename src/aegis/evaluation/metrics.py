"""Metrics computation, category aggregations, and rule confusion matrices for AEGIS evaluation."""

from __future__ import annotations

from aegis.evaluation.models import (
    CaseExecutionResult,
    CategoryMetrics,
    ConfusionMatrix,
    EvaluationCase,
    EvaluationMetrics,
    RuleCoverageMetrics,
)
from aegis.research.rules import DEFAULT_RULE_REGISTRY


def compute_evaluation_metrics(
    cases: list[EvaluationCase],
    results: list[CaseExecutionResult],
) -> EvaluationMetrics:
    """Compute comprehensive evaluation metrics from execution results."""
    case_map = {c.case_id: c for c in cases}
    total_cases = len(results)
    passed_cases = sum(1 for r in results if r.status == "passed")
    failed_cases = sum(1 for r in results if r.status == "failed")
    skipped_cases = sum(1 for r in results if r.status == "skipped")
    indeterminate_cases = sum(1 for r in results if r.status == "indeterminate")

    overall_pass_rate = round(passed_cases / total_cases, 4) if total_cases > 0 else 0.0

    # 1. Category Breakdown
    cat_results: dict[str, list[CaseExecutionResult]] = {}
    for r in results:
        cat_results.setdefault(r.category, []).append(r)

    category_breakdown: dict[str, CategoryMetrics] = {}
    for cat, c_res in sorted(cat_results.items()):
        c_tot = len(c_res)
        c_pass = sum(1 for r in c_res if r.status == "passed")
        c_fail = sum(1 for r in c_res if r.status == "failed")
        c_skip = sum(1 for r in c_res if r.status == "skipped")
        c_indet = sum(1 for r in c_res if r.status == "indeterminate")
        c_rate = round(c_pass / c_tot, 4) if c_tot > 0 else 0.0
        category_breakdown[cat] = CategoryMetrics(
            category=cat,
            total_cases=c_tot,
            passed=c_pass,
            failed=c_fail,
            skipped=c_skip,
            indeterminate=c_indet,
            pass_rate=c_rate,
        )

    # 2. Rule Coverage and Confusion Matrices
    rule_metrics: dict[str, RuleCoverageMetrics] = {}
    for rule in DEFAULT_RULE_REGISTRY:
        r_id = rule.rule_id
        r_ver = rule.version
        r_cases = [r for r in results if r_id in r.actual_rule_outcomes]

        cases_eval = len(r_cases)
        supported_cnt = sum(1 for r in r_cases if r.actual_rule_outcomes.get(r_id) == "supported")
        contradicted_cnt = sum(1 for r in r_cases if r.actual_rule_outcomes.get(r_id) == "contradicted")
        insufficient_cnt = sum(1 for r in r_cases if r.actual_rule_outcomes.get(r_id) == "insufficient_evidence")
        na_cnt = sum(1 for r in r_cases if r.actual_rule_outcomes.get(r_id) == "not_applicable")
        incomp_cnt = sum(1 for r in r_cases if r.actual_rule_outcomes.get(r_id) == "incomparable")
        err_cnt = sum(1 for r in r_cases if r.actual_rule_outcomes.get(r_id) == "error")

        agree_cnt = 0
        disagree_cnt = 0
        tp = 0
        fp = 0
        tn = 0
        fn = 0
        has_binary_cases = False

        for r in r_cases:
            c = case_map.get(r.case_id)
            if not c:
                continue

            # Check rule expectation match
            exp_rule = next((exp for exp in c.expectation.rule_expectations if exp.rule_id == r_id), None)
            if exp_rule:
                actual_out = r.actual_rule_outcomes.get(r_id)
                if actual_out == exp_rule.expected_outcome:
                    agree_cnt += 1
                else:
                    disagree_cnt += 1

            # Check binary ground truth if defined for this specific rule
            if c.expectation.binary_ground_truth_label and exp_rule:
                has_binary_cases = True
                actual_out = r.actual_rule_outcomes.get(r_id)
                is_predicted_positive = actual_out == "supported"
                is_gt_positive = c.expectation.binary_ground_truth_label == "positive"

                if is_gt_positive and is_predicted_positive:
                    tp += 1
                elif not is_gt_positive and is_predicted_positive:
                    fp += 1
                elif not is_gt_positive and not is_predicted_positive:
                    tn += 1
                elif is_gt_positive and not is_predicted_positive:
                    fn += 1

        agr_tot = agree_cnt + disagree_cnt
        agr_rate = round(agree_cnt / agr_tot, 4) if agr_tot > 0 else 1.0

        cm: ConfusionMatrix | None = None
        if has_binary_cases and (tp + fp + tn + fn) > 0:
            cm = ConfusionMatrix(
                true_positives=tp,
                false_positives=fp,
                true_negatives=tn,
                false_negatives=fn,
                notes="Binary metrics where ground-truth positive label indicates verified condition satisfaction.",
            )
            cm.compute_rates()

        rule_metrics[r_id] = RuleCoverageMetrics(
            rule_id=r_id,
            rule_version=r_ver,
            cases_evaluated=cases_eval,
            supported_count=supported_cnt,
            contradicted_count=contradicted_cnt,
            insufficient_evidence_count=insufficient_cnt,
            not_applicable_count=na_cnt,
            incomparable_count=incomp_cnt,
            error_count=err_cnt,
            agreement_count=agree_cnt,
            disagreement_count=disagree_cnt,
            agreement_rate=agr_rate,
            known_limitations=list(rule.limitations),
            confusion_matrix=cm,
        )

    # 3. Security and Robustness Rate
    sec_cases = [r for r in results if r.category == "security_robustness"]
    sec_rate = (
        round(sum(1 for r in sec_cases if r.status == "passed") / len(sec_cases), 4)
        if sec_cases
        else 1.0
    )

    # 4. Reproducibility Rate
    repro_cases = [r for r in results if r.reproducibility_verified is not None]
    repro_rate = (
        round(sum(1 for r in repro_cases if r.reproducibility_verified) / len(repro_cases), 4)
        if repro_cases
        else 1.0
    )

    return EvaluationMetrics(
        total_cases=total_cases,
        passed=passed_cases,
        failed=failed_cases,
        skipped=skipped_cases,
        indeterminate=indeterminate_cases,
        overall_pass_rate=overall_pass_rate,
        category_breakdown=category_breakdown,
        rule_metrics=rule_metrics,
        reproducibility_rate=repro_rate,
        security_robustness_rejection_rate=sec_rate,
    )
