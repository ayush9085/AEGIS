"""Data models, manifest schemas, and validation for Phase 5 Research Evaluation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

EVALUATION_SCHEMA_VERSION = "0.1.0"
SUPPORTED_EVALUATION_SCHEMA_VERSIONS = {EVALUATION_SCHEMA_VERSION}

EVALUATION_CORPUS_VERSION = "0.1.0"
SUPPORTED_CORPUS_VERSIONS = {EVALUATION_CORPUS_VERSION}

VALID_CASE_CATEGORIES = {
    "normalization",
    "graph_integrity",
    "rule_evaluation",
    "cross_source_correlation",
    "security_robustness",
    "reproducibility",
}

VALID_EXECUTION_STATUSES = {
    "passed",
    "failed",
    "skipped",
    "indeterminate",
}


class EvaluationError(Exception):
    """Base exception for AEGIS evaluation subsystem."""


class EvaluationValidationError(EvaluationError):
    """Raised when an evaluation manifest or report fails validation."""


class EvaluationCompatibilityError(EvaluationError):
    """Raised when an unsupported evaluation schema or corpus version is encountered."""


@dataclass
class RuleOutcomeExpectation:
    """Expected outcome for a specific research rule."""

    rule_id: str
    expected_outcome: str  # supported, contradicted, insufficient_evidence, not_applicable, incomparable, error
    expected_certainty: str | None = None
    expected_prerequisites_missing: list[str] = field(default_factory=list)
    expected_conflicts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleOutcomeExpectation:
        return cls(
            rule_id=str(data["rule_id"]),
            expected_outcome=str(data["expected_outcome"]),
            expected_certainty=data.get("expected_certainty"),
            expected_prerequisites_missing=list(data.get("expected_prerequisites_missing", [])),
            expected_conflicts=list(data.get("expected_conflicts", [])),
        )


@dataclass
class CaseExpectation:
    """Explicit ground-truth expectations for an evaluation case."""

    expected_status: str = "passed"  # passed, failed, skipped, indeterminate
    expected_exception_type: str | None = None
    expected_exception_message_substring: str | None = None
    rule_expectations: list[RuleOutcomeExpectation] = field(default_factory=list)
    expected_conflict_count: int | None = None
    expected_missing_inventory_keys: list[str] = field(default_factory=list)
    expected_graph_node_count: int | None = None
    expected_graph_edge_count: int | None = None
    binary_ground_truth_label: str | None = None  # e.g., "positive" or "negative" for binary confusion matrices
    reproducibility_check: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["rule_expectations"] = [r.to_dict() for r in self.rule_expectations]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CaseExpectation:
        return cls(
            expected_status=str(data.get("expected_status", "passed")),
            expected_exception_type=data.get("expected_exception_type"),
            expected_exception_message_substring=data.get("expected_exception_message_substring"),
            rule_expectations=[
                RuleOutcomeExpectation.from_dict(r) for r in data.get("rule_expectations", [])
            ],
            expected_conflict_count=data.get("expected_conflict_count"),
            expected_missing_inventory_keys=list(data.get("expected_missing_inventory_keys", [])),
            expected_graph_node_count=data.get("expected_graph_node_count"),
            expected_graph_edge_count=data.get("expected_graph_edge_count"),
            binary_ground_truth_label=data.get("binary_ground_truth_label"),
            reproducibility_check=bool(data.get("reproducibility_check", False)),
        )


@dataclass
class EvaluationCase:
    """A documented, versioned evaluation case with ground-truth expectations."""

    case_id: str
    title: str
    category: str  # from VALID_CASE_CATEGORIES
    description: str
    provenance: str  # synthetic_fixture, physical_handset, mixed
    inputs: list[dict[str, Any]] = field(default_factory=list)
    expectation: CaseExpectation = field(default_factory=CaseExpectation)
    rationale: str = ""
    limitations: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["expectation"] = self.expectation.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationCase:
        category = str(data.get("category", ""))
        if category not in VALID_CASE_CATEGORIES:
            raise EvaluationValidationError(
                f"Invalid case category '{category}'. Expected one of {sorted(VALID_CASE_CATEGORIES)}"
            )
        return cls(
            case_id=str(data["case_id"]),
            title=str(data.get("title", data["case_id"])),
            category=category,
            description=str(data.get("description", "")),
            provenance=str(data.get("provenance", "synthetic_fixture")),
            inputs=list(data.get("inputs", [])),
            expectation=CaseExpectation.from_dict(data.get("expectation", {})),
            rationale=str(data.get("rationale", "")),
            limitations=list(data.get("limitations", [])),
            tags=list(data.get("tags", [])),
        )


@dataclass
class EvaluationManifest:
    """A versioned manifest defining a suite of evaluation cases."""

    schema_version: str = EVALUATION_SCHEMA_VERSION
    corpus_version: str = EVALUATION_CORPUS_VERSION
    title: str = "AEGIS Ground-Truth Research Evaluation Corpus"
    description: str = "Comprehensive evaluation corpus for AEGIS Phases 1-4 capabilities."
    created_at_utc: str = ""
    cases: list[EvaluationCase] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "corpus_version": self.corpus_version,
            "title": self.title,
            "description": self.description,
            "created_at_utc": self.created_at_utc,
            "cases": [c.to_dict() for c in self.cases],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationManifest:
        validate_evaluation_manifest_dict(data)
        return cls(
            schema_version=str(data["schema_version"]),
            corpus_version=str(data.get("corpus_version", EVALUATION_CORPUS_VERSION)),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            created_at_utc=str(data.get("created_at_utc", "")),
            cases=[EvaluationCase.from_dict(c) for c in data.get("cases", [])],
        )

    @classmethod
    def from_json(cls, json_str: str) -> EvaluationManifest:
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise EvaluationValidationError(f"Invalid JSON in evaluation manifest: {exc}") from exc
        return cls.from_dict(data)


@dataclass
class CaseExecutionResult:
    """The outcome of executing a single evaluation case."""

    case_id: str
    category: str
    status: str  # passed, failed, skipped, indeterminate
    execution_time_ms: float
    message: str = ""
    differences: list[str] = field(default_factory=list)
    actual_rule_outcomes: dict[str, str] = field(default_factory=dict)
    actual_rule_certainties: dict[str, str] = field(default_factory=dict)
    actual_conflicts_count: int = 0
    actual_missing_inventory_count: int = 0
    binary_predicted_label: str | None = None
    binary_ground_truth_label: str | None = None
    reproducibility_verified: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CaseExecutionResult:
        return cls(**data)


@dataclass
class ConfusionMatrix:
    """Confusion matrix for binary evaluation tasks where ground-truth labels exist."""

    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None
    notes: str = ""

    def compute_rates(self) -> None:
        denom_p = self.true_positives + self.false_positives
        self.precision = round(self.true_positives / denom_p, 4) if denom_p > 0 else None

        denom_r = self.true_positives + self.false_negatives
        self.recall = round(self.true_positives / denom_r, 4) if denom_r > 0 else None

        if self.precision is not None and self.recall is not None and (self.precision + self.recall) > 0:
            self.f1_score = round(2 * (self.precision * self.recall) / (self.precision + self.recall), 4)
        else:
            self.f1_score = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConfusionMatrix:
        return cls(**data)


@dataclass
class RuleCoverageMetrics:
    """Coverage and agreement statistics for a specific research rule."""

    rule_id: str
    rule_version: str
    cases_evaluated: int = 0
    supported_count: int = 0
    contradicted_count: int = 0
    insufficient_evidence_count: int = 0
    not_applicable_count: int = 0
    incomparable_count: int = 0
    error_count: int = 0
    agreement_count: int = 0
    disagreement_count: int = 0
    agreement_rate: float = 1.0
    known_limitations: list[str] = field(default_factory=list)
    confusion_matrix: ConfusionMatrix | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.confusion_matrix:
            d["confusion_matrix"] = self.confusion_matrix.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleCoverageMetrics:
        cm_data = data.get("confusion_matrix")
        cm = ConfusionMatrix.from_dict(cm_data) if cm_data else None
        data_copy = dict(data)
        data_copy["confusion_matrix"] = cm
        return cls(**data_copy)


@dataclass
class CategoryMetrics:
    """Summary metrics for a specific evaluation category."""

    category: str
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    indeterminate: int = 0
    pass_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CategoryMetrics:
        return cls(**data)


@dataclass
class EvaluationMetrics:
    """Aggregated evaluation metrics across all cases and categories."""

    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    indeterminate: int = 0
    overall_pass_rate: float = 0.0
    category_breakdown: dict[str, CategoryMetrics] = field(default_factory=dict)
    rule_metrics: dict[str, RuleCoverageMetrics] = field(default_factory=dict)
    reproducibility_rate: float = 1.0
    security_robustness_rejection_rate: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "indeterminate": self.indeterminate,
            "overall_pass_rate": self.overall_pass_rate,
            "category_breakdown": {k: v.to_dict() for k, v in self.category_breakdown.items()},
            "rule_metrics": {k: v.to_dict() for k, v in self.rule_metrics.items()},
            "reproducibility_rate": self.reproducibility_rate,
            "security_robustness_rejection_rate": self.security_robustness_rejection_rate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationMetrics:
        cat_breakdown = {
            k: CategoryMetrics.from_dict(v) for k, v in data.get("category_breakdown", {}).items()
        }
        rule_mets = {
            k: RuleCoverageMetrics.from_dict(v) for k, v in data.get("rule_metrics", {}).items()
        }
        return cls(
            total_cases=int(data.get("total_cases", 0)),
            passed=int(data.get("passed", 0)),
            failed=int(data.get("failed", 0)),
            skipped=int(data.get("skipped", 0)),
            indeterminate=int(data.get("indeterminate", 0)),
            overall_pass_rate=float(data.get("overall_pass_rate", 0.0)),
            category_breakdown=cat_breakdown,
            rule_metrics=rule_mets,
            reproducibility_rate=float(data.get("reproducibility_rate", 1.0)),
            security_robustness_rejection_rate=float(
                data.get("security_robustness_rejection_rate", 1.0)
            ),
        )


@dataclass
class EvaluationReport:
    """Comprehensive, versioned evaluation report documenting methodology and results."""

    schema_version: str = EVALUATION_SCHEMA_VERSION
    corpus_version: str = EVALUATION_CORPUS_VERSION
    aegis_version: str = ""
    git_commit: str = ""
    evaluated_at_utc: str = ""
    manifest_title: str = ""
    manifest_description: str = ""
    results: list[CaseExecutionResult] = field(default_factory=list)
    metrics: EvaluationMetrics = field(default_factory=EvaluationMetrics)
    reproducibility_hash: str = ""
    methodology: dict[str, Any] = field(default_factory=dict)
    known_limitations: list[str] = field(default_factory=list)
    threats_to_validity: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "corpus_version": self.corpus_version,
            "aegis_version": self.aegis_version,
            "git_commit": self.git_commit,
            "evaluated_at_utc": self.evaluated_at_utc,
            "manifest_title": self.manifest_title,
            "manifest_description": self.manifest_description,
            "results": [r.to_dict() for r in self.results],
            "metrics": self.metrics.to_dict(),
            "reproducibility_hash": self.reproducibility_hash,
            "methodology": self.methodology,
            "known_limitations": self.known_limitations,
            "threats_to_validity": self.threats_to_validity,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationReport:
        validate_evaluation_report_dict(data)
        return cls(
            schema_version=str(data["schema_version"]),
            corpus_version=str(data.get("corpus_version", EVALUATION_CORPUS_VERSION)),
            aegis_version=str(data.get("aegis_version", "")),
            git_commit=str(data.get("git_commit", "")),
            evaluated_at_utc=str(data.get("evaluated_at_utc", "")),
            manifest_title=str(data.get("manifest_title", "")),
            manifest_description=str(data.get("manifest_description", "")),
            results=[CaseExecutionResult.from_dict(r) for r in data.get("results", [])],
            metrics=EvaluationMetrics.from_dict(data.get("metrics", {})),
            reproducibility_hash=str(data.get("reproducibility_hash", "")),
            methodology=dict(data.get("methodology", {})),
            known_limitations=list(data.get("known_limitations", [])),
            threats_to_validity=list(data.get("threats_to_validity", [])),
        )

    @classmethod
    def from_json(cls, json_str: str) -> EvaluationReport:
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise EvaluationValidationError(f"Invalid JSON in evaluation report: {exc}") from exc
        return cls.from_dict(data)


def validate_evaluation_manifest_dict(data: dict[str, Any]) -> None:
    """Validate structure and referential integrity of an evaluation manifest dictionary."""
    if not isinstance(data, dict):
        raise EvaluationValidationError(f"Manifest must be a JSON object, got {type(data).__name__}")

    schema_version = data.get("schema_version")
    if not schema_version:
        raise EvaluationValidationError("Missing required 'schema_version' field in manifest")
    if schema_version not in SUPPORTED_EVALUATION_SCHEMA_VERSIONS:
        raise EvaluationCompatibilityError(
            f"Unsupported evaluation schema version '{schema_version}'. Supported: {sorted(SUPPORTED_EVALUATION_SCHEMA_VERSIONS)}"
        )

    corpus_version = data.get("corpus_version")
    if not corpus_version:
        raise EvaluationValidationError("Missing required 'corpus_version' field in manifest")
    if corpus_version not in SUPPORTED_CORPUS_VERSIONS:
        raise EvaluationCompatibilityError(
            f"Unsupported evaluation corpus version '{corpus_version}'. Supported: {sorted(SUPPORTED_CORPUS_VERSIONS)}"
        )

    if "cases" not in data or not isinstance(data["cases"], list):
        raise EvaluationValidationError("Manifest must contain a 'cases' list")

    seen_case_ids: set[str] = set()
    for case_data in data["cases"]:
        if not isinstance(case_data, dict):
            raise EvaluationValidationError(f"Case must be a JSON object, got {type(case_data).__name__}")
        case_id = case_data.get("case_id")
        if not case_id:
            raise EvaluationValidationError("Missing required 'case_id' in evaluation case")
        if case_id in seen_case_ids:
            raise EvaluationValidationError(f"Duplicate case_id in manifest: '{case_id}'")
        seen_case_ids.add(case_id)

        category = case_data.get("category")
        if not category or category not in VALID_CASE_CATEGORIES:
            raise EvaluationValidationError(
                f"Case '{case_id}' has invalid category '{category}'. Expected one of {sorted(VALID_CASE_CATEGORIES)}"
            )


def validate_evaluation_report_dict(data: dict[str, Any]) -> None:
    """Validate structure, types, and reconciled metrics of an evaluation report dictionary."""
    if not isinstance(data, dict):
        raise EvaluationValidationError(f"Report must be a JSON object, got {type(data).__name__}")

    schema_version = data.get("schema_version")
    if not schema_version:
        raise EvaluationValidationError("Missing required 'schema_version' field in evaluation report")
    if schema_version not in SUPPORTED_EVALUATION_SCHEMA_VERSIONS:
        raise EvaluationCompatibilityError(
            f"Unsupported evaluation schema version '{schema_version}'. Supported: {sorted(SUPPORTED_EVALUATION_SCHEMA_VERSIONS)}"
        )

    required_fields = (
        "aegis_version",
        "evaluated_at_utc",
        "results",
        "metrics",
        "known_limitations",
        "threats_to_validity",
    )
    for f in required_fields:
        if f not in data:
            raise EvaluationValidationError(f"Missing required field in evaluation report: '{f}'")

    if not isinstance(data["results"], list):
        raise EvaluationValidationError("Field 'results' must be a list")
    if not isinstance(data["metrics"], dict):
        raise EvaluationValidationError("Field 'metrics' must be a dictionary")

    # Validate count reconciliation
    metrics = data["metrics"]
    actual_results_count = len(data["results"])
    reported_total = metrics.get("total_cases")
    if reported_total is not None and reported_total != actual_results_count:
        raise EvaluationValidationError(
            f"Metrics total_cases ({reported_total}) does not match actual results count ({actual_results_count})"
        )

    passed_count = sum(1 for r in data["results"] if r.get("status") == "passed")
    failed_count = sum(1 for r in data["results"] if r.get("status") == "failed")
    skipped_count = sum(1 for r in data["results"] if r.get("status") == "skipped")
    indeterminate_count = sum(1 for r in data["results"] if r.get("status") == "indeterminate")

    if metrics.get("passed") is not None and metrics["passed"] != passed_count:
        raise EvaluationValidationError(
            f"Metrics passed count ({metrics['passed']}) does not match results ({passed_count})"
        )
    if metrics.get("failed") is not None and metrics["failed"] != failed_count:
        raise EvaluationValidationError(
            f"Metrics failed count ({metrics['failed']}) does not match results ({failed_count})"
        )
    if metrics.get("skipped") is not None and metrics["skipped"] != skipped_count:
        raise EvaluationValidationError(
            f"Metrics skipped count ({metrics['skipped']}) does not match results ({skipped_count})"
        )
    if metrics.get("indeterminate") is not None and metrics["indeterminate"] != indeterminate_count:
        raise EvaluationValidationError(
            f"Metrics indeterminate count ({metrics['indeterminate']}) does not match results ({indeterminate_count})"
        )
