"""Terminal formatting, serialization, and report rendering for AEGIS evaluations."""

from __future__ import annotations

from pathlib import Path

from aegis.evaluation.models import EvaluationReport


def save_evaluation_report(
    report: EvaluationReport,
    out_path: Path,
    overwrite: bool = False,
) -> Path:
    """Save evaluation report to JSON file with overwrite protection."""
    dest = out_path.resolve()
    if dest.exists() and not overwrite:
        raise FileExistsError(f"Destination evaluation report file already exists: {dest} (use --overwrite)")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(report.to_json(), encoding="utf-8")
    return dest


def load_evaluation_report(path: Path) -> EvaluationReport:
    """Load and validate an evaluation report from a JSON file."""
    p = path.resolve()
    if not p.is_file():
        raise FileNotFoundError(f"Evaluation report file not found: {p}")
    raw_text = p.read_text(encoding="utf-8")
    return EvaluationReport.from_json(raw_text)


def format_terminal_evaluation_report(report: EvaluationReport) -> str:
    """Generate rich, human-readable terminal output for an evaluation report."""
    lines: list[str] = []
    m = report.metrics

    lines.append("\n" + "=" * 78)
    lines.append("  🧪 AEGIS PHASE 5 — RESEARCH EVALUATION & REPRODUCIBILITY REPORT")
    lines.append("=" * 78)
    lines.append(f"  Schema Version   : {report.schema_version}")
    lines.append(f"  Corpus Version   : {report.corpus_version}")
    lines.append(f"  AEGIS Version    : {report.aegis_version}")
    lines.append(f"  Git Commit       : {report.git_commit}")
    lines.append(f"  Evaluated At     : {report.evaluated_at_utc}")
    lines.append(f"  Reproducibility  : {report.reproducibility_hash[:16]}... (stable)")
    lines.append("-" * 78)

    # Executive Summary Card
    status_icon = "✅" if m.failed == 0 else "⚠️"
    lines.append(f"\n  {status_icon} EXECUTIVE SUMMARY")
    lines.append(f"     Total Cases   : {m.total_cases}")
    lines.append(f"     Passed        : {m.passed}")
    lines.append(f"     Failed        : {m.failed}")
    lines.append(f"     Skipped       : {m.skipped}")
    lines.append(f"     Indeterminate : {m.indeterminate}")
    lines.append(f"     Pass Rate     : {m.overall_pass_rate * 100:.1f}%")
    lines.append(f"     Reproducibility: {m.reproducibility_rate * 100:.1f}%")
    lines.append(f"     Robustness    : {m.security_robustness_rejection_rate * 100:.1f}%")

    # Category Breakdown
    lines.append("\n  📂 RESULTS BY EVALUATION CATEGORY")
    lines.append(f"     {'Category':<26} {'Total':<7} {'Passed':<8} {'Failed':<8} {'Pass Rate':<10}")
    lines.append(f"     {'-'*25} {'-'*6} {'-'*7} {'-'*7} {'-'*9}")
    for cat, cm in sorted(m.category_breakdown.items()):
        rate_str = f"{cm.pass_rate * 100:.1f}%"
        lines.append(f"     {cat:<26} {cm.total_cases:<7} {cm.passed:<8} {cm.failed:<8} {rate_str:<10}")

    # Rule Coverage Matrix
    lines.append("\n  🔬 RULE COVERAGE & EVALUATION AGREEMENT MATRIX")
    lines.append(
        f"     {'Rule ID':<30} {'Version':<9} {'Cases':<7} {'Agreement':<11} {'Outcome Distribution'}"
    )
    lines.append(f"     {'-'*29} {'-'*8} {'-'*6} {'-'*10} {'-'*22}")
    for r_id, rm in sorted(m.rule_metrics.items()):
        dist = f"sup:{rm.supported_count} | in-ev:{rm.insufficient_evidence_count} | cont:{rm.contradicted_count} | na:{rm.not_applicable_count}"
        agr_str = f"{rm.agreement_rate * 100:.1f}%"
        lines.append(f"     {r_id:<30} {rm.rule_version:<9} {rm.cases_evaluated:<7} {agr_str:<11} {dist}")

    # Binary Confusion Matrices
    cm_rules = [(r_id, rm.confusion_matrix) for r_id, rm in m.rule_metrics.items() if rm.confusion_matrix]
    if cm_rules:
        lines.append("\n  📊 BINARY CONFUSION MATRICES (Ground-Truth Validated)")
        for r_id, cm in cm_rules:
            assert cm is not None
            lines.append(f"     Rule: {r_id}")
            lines.append(f"       TP: {cm.true_positives:<4} FP: {cm.false_positives:<4} | Precision: {cm.precision if cm.precision is not None else 'N/A'}")
            lines.append(f"       FN: {cm.false_negatives:<4} TN: {cm.true_negatives:<4} | Recall   : {cm.recall if cm.recall is not None else 'N/A'}")
            lines.append(f"       F1 Score: {cm.f1_score if cm.f1_score is not None else 'N/A'}")
            lines.append(f"       Notes   : {cm.notes}")

    # Failure Analysis if any
    failed_results = [r for r in report.results if r.status == "failed"]
    if failed_results:
        lines.append("\n  ❌ FAILED CASES ANALYSIS")
        for fr in failed_results:
            lines.append(f"     • [{fr.case_id}] {fr.category}: {fr.message}")
            for d in fr.differences:
                lines.append(f"         - {d}")
    else:
        lines.append("\n  ✅ Zero case failures encountered across the evaluation corpus.")

    # Scientific Restraint Notice
    lines.append("\n" + "-" * 78)
    lines.append("  ⚠️  SCIENTIFIC & METHODOLOGICAL DISCLAIMER")
    lines.append("  • Results are derived from synthetic evaluation fixtures and consenting test devices.")
    lines.append("  • Evaluation verifies software determinism and rule logic consistency.")
    lines.append("  • Passing evaluation does NOT prove an Android device is cryptographically authentic,")
    lines.append("    hardware-attested, uncompromised, or free of kernel/firmware rootkits.")
    lines.append("=" * 78 + "\n")

    return "\n".join(lines)
