"""AEGIS Phase 5: Research Validation, Evaluation & Reproducibility Subsystem."""

from aegis.evaluation.corpus import build_evaluation_corpus, load_default_manifest
from aegis.evaluation.html_report import render_evaluation_html_report
from aegis.evaluation.metrics import compute_evaluation_metrics
from aegis.evaluation.models import (
    EVALUATION_CORPUS_VERSION,
    EVALUATION_SCHEMA_VERSION,
    SUPPORTED_CORPUS_VERSIONS,
    SUPPORTED_EVALUATION_SCHEMA_VERSIONS,
    VALID_CASE_CATEGORIES,
    VALID_EXECUTION_STATUSES,
    CaseExecutionResult,
    CaseExpectation,
    CategoryMetrics,
    ConfusionMatrix,
    EvaluationCase,
    EvaluationCompatibilityError,
    EvaluationError,
    EvaluationManifest,
    EvaluationMetrics,
    EvaluationReport,
    EvaluationValidationError,
    RuleCoverageMetrics,
    RuleOutcomeExpectation,
    validate_evaluation_manifest_dict,
    validate_evaluation_report_dict,
)
from aegis.evaluation.report import (
    format_terminal_evaluation_report,
    load_evaluation_report,
    save_evaluation_report,
)
from aegis.evaluation.runner import EvaluationRunner

__all__ = [
    "EVALUATION_CORPUS_VERSION",
    "EVALUATION_SCHEMA_VERSION",
    "SUPPORTED_CORPUS_VERSIONS",
    "SUPPORTED_EVALUATION_SCHEMA_VERSIONS",
    "VALID_CASE_CATEGORIES",
    "VALID_EXECUTION_STATUSES",
    "CaseExecutionResult",
    "CaseExpectation",
    "CategoryMetrics",
    "ConfusionMatrix",
    "EvaluationCase",
    "EvaluationCompatibilityError",
    "EvaluationError",
    "EvaluationManifest",
    "EvaluationMetrics",
    "EvaluationReport",
    "EvaluationRunner",
    "EvaluationValidationError",
    "RuleCoverageMetrics",
    "RuleOutcomeExpectation",
    "build_evaluation_corpus",
    "compute_evaluation_metrics",
    "format_terminal_evaluation_report",
    "load_default_manifest",
    "load_evaluation_report",
    "render_evaluation_html_report",
    "save_evaluation_report",
    "validate_evaluation_manifest_dict",
    "validate_evaluation_report_dict",
]
