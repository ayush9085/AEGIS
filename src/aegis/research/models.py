"""Data models, graph representation, and validation for evidence-linked research."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

RESEARCH_SCHEMA_VERSION = "0.1.0"
SUPPORTED_RESEARCH_SCHEMA_VERSIONS = {RESEARCH_SCHEMA_VERSION}

VALID_CERTAINTIES = {
    "directly_observed",
    "strongly_supported",
    "tentatively_supported",
    "insufficient_evidence",
    "conflicting_evidence",
}

VALID_OUTCOMES = {
    "supported",
    "contradicted",
    "insufficient_evidence",
    "not_applicable",
    "incomparable",
    "error",
}

VALID_NODE_TYPES = {
    "device",
    "observation",
    "firmware_artifact",
    "firmware_component",
    "snapshot",
    "diff",
    "claim",
    "rule_evaluation",
}

VALID_RELATIONSHIPS = {
    "observed_on",
    "contained_in",
    "derived_from",
    "compared_with",
    "supports",
    "contradicts",
    "requires",
    "related_to",
}

DEFAULT_RESEARCH_LIMITATIONS = [
    "AEGIS Research Engine correlates and reasons over supplied evidence; it is NOT a hardware-backed attestation engine.",
    "Absence of an observation or property is NOT proof that a security control or component is disabled.",
    "Correlating static firmware metadata with live device state establishes consistency or drift, NOT cryptographic proof of runtime authenticity.",
    "Rules evaluate structural completeness, consistency, and observable indicators without making binary 'secure' or 'compromised' verdicts.",
    "Certainty classifications reflect evidence presence and convergence, not mathematical probabilities or absolute truth.",
]


class ResearchError(Exception):
    """Base exception for AEGIS research engine."""


class ResearchValidationError(ResearchError):
    """Raised when a research report fails schema or integrity validation."""


class ResearchCompatibilityError(ResearchError):
    """Raised when an unsupported input report or schema version is encountered."""


@dataclass
class NormalizedEvidence:
    """A standardized, traceable evidence item extracted from any AEGIS report."""

    evidence_id: str
    source_type: str  # device_evidence, snapshot, semantic_diff, firmware_report
    source_ref: str
    source_schema_version: str
    category: str
    key: str
    label: str
    status: str
    value: Any
    source_content_hash: str | None = None
    raw_value: str | None = None
    provenance: str = "unverified"  # synthetic, physical_handset, firmware_artifact, unverified
    device_fingerprint: dict[str, Any] | None = None
    collector_or_parser: str | None = None
    collected_at_utc: str | None = None
    redacted: bool = False
    caveats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NormalizedEvidence:
        return cls(**data)


@dataclass
class GraphNode:
    """A node in the evidence graph."""

    node_id: str
    node_type: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphNode:
        return cls(
            node_id=str(data["node_id"]),
            node_type=str(data["node_type"]),
            label=str(data.get("label", data["node_id"])),
            properties=dict(data.get("properties", {})),
        )


@dataclass
class GraphEdge:
    """A directed, typed relationship between two nodes in the evidence graph."""

    source_id: str
    target_id: str
    relationship: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphEdge:
        return cls(
            source_id=str(data["source_id"]),
            target_id=str(data["target_id"]),
            relationship=str(data["relationship"]),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class EvidenceGraph:
    """Deterministic, serializable evidence graph with referential integrity."""

    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def add_node(self, node: GraphNode) -> None:
        if not any(n.node_id == node.node_id for n in self.nodes):
            self.nodes.append(node)

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)

    def validate_referential_integrity(self) -> None:
        """Verify that every edge connects two valid, existing nodes."""
        node_ids = {n.node_id for n in self.nodes}

        # Check duplicate node IDs
        if len(node_ids) != len(self.nodes):
            seen: set[str] = set()
            dups: set[str] = set()
            for n in self.nodes:
                if n.node_id in seen:
                    dups.add(n.node_id)
                seen.add(n.node_id)
            raise ResearchValidationError(f"Duplicate node IDs in evidence graph: {sorted(dups)}")

        # Check edge endpoints
        for edge in self.edges:
            if edge.source_id not in node_ids:
                raise ResearchValidationError(
                    f"Dangling edge: source node '{edge.source_id}' does not exist in graph"
                )
            if edge.target_id not in node_ids:
                raise ResearchValidationError(
                    f"Dangling edge: target node '{edge.target_id}' does not exist in graph"
                )
            if edge.relationship not in VALID_RELATIONSHIPS:
                raise ResearchValidationError(
                    f"Invalid edge relationship '{edge.relationship}'. Expected one of {sorted(VALID_RELATIONSHIPS)}"
                )

    def sort_deterministic(self) -> None:
        """Sort nodes and edges deterministically."""
        self.nodes.sort(key=lambda n: (n.node_type, n.node_id))
        self.edges.sort(key=lambda e: (e.source_id, e.target_id, e.relationship))

    def to_dict(self) -> dict[str, Any]:
        self.sort_deterministic()
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceGraph:
        graph = cls(
            nodes=[GraphNode.from_dict(n) for n in data.get("nodes", [])],
            edges=[GraphEdge.from_dict(e) for e in data.get("edges", [])],
        )
        graph.validate_referential_integrity()
        return graph


@dataclass
class RuleEvaluationRecord:
    """Deterministic record of an evaluation performed by a research rule."""

    evaluation_id: str
    rule_id: str
    rule_version: str
    outcome: str  # from VALID_OUTCOMES
    certainty: str  # from VALID_CERTAINTIES
    input_evidence_ids: list[str] = field(default_factory=list)
    prerequisites_checked: list[str] = field(default_factory=list)
    prerequisites_satisfied: list[str] = field(default_factory=list)
    prerequisites_missing: list[str] = field(default_factory=list)
    conflicting_evidence_ids: list[str] = field(default_factory=list)
    conclusion: str = ""
    explanation: str = ""
    caveats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleEvaluationRecord:
        return cls(**data)


@dataclass
class ResearchClaim:
    """An explainable derived claim backed by explicit evidence traces."""

    claim_id: str
    title: str
    category: str
    certainty: str  # from VALID_CERTAINTIES
    summary: str
    supporting_evidence_ids: list[str] = field(default_factory=list)
    contradicting_evidence_ids: list[str] = field(default_factory=list)
    evaluating_rule_id: str = ""
    assumptions: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResearchClaim:
        return cls(**data)


@dataclass
class ResearchReport:
    """Versioned, self-contained report of evidence correlation, graph, and derived research findings."""

    schema_version: str = RESEARCH_SCHEMA_VERSION
    aegis_version: str = ""
    evaluated_at_utc: str = ""
    source_inputs: list[dict[str, Any]] = field(default_factory=list)
    graph: EvidenceGraph = field(default_factory=EvidenceGraph)
    evaluations: list[RuleEvaluationRecord] = field(default_factory=list)
    claims: list[ResearchClaim] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    missing_evidence_inventory: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=lambda: list(DEFAULT_RESEARCH_LIMITATIONS))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "aegis_version": self.aegis_version,
            "evaluated_at_utc": self.evaluated_at_utc,
            "source_inputs": self.source_inputs,
            "graph": self.graph.to_dict(),
            "evaluations": [e.to_dict() for e in self.evaluations],
            "claims": [c.to_dict() for c in self.claims],
            "conflicts": self.conflicts,
            "missing_evidence_inventory": self.missing_evidence_inventory,
            "summary": self.summary,
            "limitations": self.limitations,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResearchReport:
        validate_research_report_dict(data)
        return cls(
            schema_version=str(data["schema_version"]),
            aegis_version=str(data.get("aegis_version", "")),
            evaluated_at_utc=str(data.get("evaluated_at_utc", "")),
            source_inputs=list(data.get("source_inputs", [])),
            graph=EvidenceGraph.from_dict(data.get("graph", {})),
            evaluations=[RuleEvaluationRecord.from_dict(e) for e in data.get("evaluations", [])],
            claims=[ResearchClaim.from_dict(c) for c in data.get("claims", [])],
            conflicts=list(data.get("conflicts", [])),
            missing_evidence_inventory=list(data.get("missing_evidence_inventory", [])),
            summary=dict(data.get("summary", {})),
            limitations=list(data.get("limitations", DEFAULT_RESEARCH_LIMITATIONS)),
        )

    @classmethod
    def from_json(cls, json_str: str) -> ResearchReport:
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ResearchValidationError(f"Invalid JSON: {exc}") from exc
        return cls.from_dict(data)


def validate_research_report_dict(data: dict[str, Any]) -> None:
    """Validate structure, types, and referential integrity of a research report dictionary."""
    if not isinstance(data, dict):
        raise ResearchValidationError(f"Report must be a JSON object, got {type(data).__name__}")

    schema_version = data.get("schema_version")
    if not schema_version:
        raise ResearchValidationError("Missing required 'schema_version' field")
    if schema_version not in SUPPORTED_RESEARCH_SCHEMA_VERSIONS:
        raise ResearchCompatibilityError(
            f"Unsupported research schema version '{schema_version}'. Supported: {sorted(SUPPORTED_RESEARCH_SCHEMA_VERSIONS)}"
        )

    required_fields = (
        "aegis_version",
        "evaluated_at_utc",
        "source_inputs",
        "graph",
        "evaluations",
        "claims",
        "conflicts",
        "missing_evidence_inventory",
        "summary",
    )
    for f in required_fields:
        if f not in data:
            raise ResearchValidationError(f"Missing required field in research report: '{f}'")

    if not isinstance(data["source_inputs"], list):
        raise ResearchValidationError("Field 'source_inputs' must be a list")
    if not isinstance(data["evaluations"], list):
        raise ResearchValidationError("Field 'evaluations' must be a list")
    if not isinstance(data["claims"], list):
        raise ResearchValidationError("Field 'claims' must be a list")
    if not isinstance(data["conflicts"], list):
        raise ResearchValidationError("Field 'conflicts' must be a list")
    if not isinstance(data["missing_evidence_inventory"], list):
        raise ResearchValidationError("Field 'missing_evidence_inventory' must be a list")
    if not isinstance(data["summary"], dict):
        raise ResearchValidationError("Field 'summary' must be a dictionary")

    # Validate graph
    graph_dict = data.get("graph")
    if not isinstance(graph_dict, dict) or "nodes" not in graph_dict or "edges" not in graph_dict:
        raise ResearchValidationError("Field 'graph' must be an object with 'nodes' and 'edges'")

    # Validate referential integrity on graph
    graph = EvidenceGraph.from_dict(graph_dict)
    graph.validate_referential_integrity()

    # Validate summary counts reconciliation
    summary = data["summary"]
    total_claims = len(data["claims"])
    total_evaluations = len(data["evaluations"])
    total_conflicts = len(data["conflicts"])

    if "total_claims" in summary and summary["total_claims"] != total_claims:
        raise ResearchValidationError(
            f"Summary total_claims ({summary['total_claims']}) does not match actual claims count ({total_claims})"
        )
    if "total_evaluations" in summary and summary["total_evaluations"] != total_evaluations:
        raise ResearchValidationError(
            f"Summary total_evaluations ({summary['total_evaluations']}) does not match evaluations count ({total_evaluations})"
        )
    if "total_conflicts" in summary and summary["total_conflicts"] != total_conflicts:
        raise ResearchValidationError(
            f"Summary total_conflicts ({summary['total_conflicts']}) does not match conflicts count ({total_conflicts})"
        )
