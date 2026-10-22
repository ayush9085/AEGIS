"""Offline evidence-linked boot-chain research engine for AEGIS."""

from aegis.research.engine import analyze_research_inputs
from aegis.research.graph import build_evidence_graph
from aegis.research.models import (
    DEFAULT_RESEARCH_LIMITATIONS,
    RESEARCH_SCHEMA_VERSION,
    EvidenceGraph,
    GraphEdge,
    GraphNode,
    NormalizedEvidence,
    ResearchClaim,
    ResearchCompatibilityError,
    ResearchError,
    ResearchReport,
    ResearchValidationError,
    RuleEvaluationRecord,
    validate_research_report_dict,
)
from aegis.research.normalize import load_and_normalize_path, normalize_source_data
from aegis.research.rules import DEFAULT_RULE_REGISTRY, BaseRule

__all__ = [
    "DEFAULT_RESEARCH_LIMITATIONS",
    "DEFAULT_RULE_REGISTRY",
    "RESEARCH_SCHEMA_VERSION",
    "BaseRule",
    "EvidenceGraph",
    "GraphEdge",
    "GraphNode",
    "NormalizedEvidence",
    "ResearchClaim",
    "ResearchCompatibilityError",
    "ResearchError",
    "ResearchReport",
    "ResearchValidationError",
    "RuleEvaluationRecord",
    "analyze_research_inputs",
    "build_evidence_graph",
    "load_and_normalize_path",
    "normalize_source_data",
    "validate_research_report_dict",
]
