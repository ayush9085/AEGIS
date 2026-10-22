"""Unit tests for Research models, graph referential integrity, and report validation."""

import pytest

from aegis.research.models import (
    EvidenceGraph,
    GraphEdge,
    GraphNode,
    ResearchClaim,
    ResearchReport,
    ResearchValidationError,
    RuleEvaluationRecord,
)


def test_evidence_graph_nodes_and_edges():
    graph = EvidenceGraph()

    n1 = GraphNode(node_id="dev:1", node_type="device", label="Pixel 7")
    n2 = GraphNode(node_id="ev:1", node_type="observation", label="Verified Boot State")
    graph.add_node(n1)
    graph.add_node(n2)

    e1 = GraphEdge(source_id="ev:1", target_id="dev:1", relationship="observed_on")
    graph.add_edge(e1)

    graph.validate_referential_integrity()
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1


def test_evidence_graph_dangling_edge_rejected():
    graph = EvidenceGraph()
    n1 = GraphNode(node_id="dev:1", node_type="device", label="Pixel 7")
    graph.add_node(n1)

    # Edge target does not exist
    graph.add_edge(GraphEdge(source_id="dev:1", target_id="dev:missing", relationship="related_to"))
    with pytest.raises(ResearchValidationError, match="Dangling edge: target node 'dev:missing'"):
        graph.validate_referential_integrity()


def test_evidence_graph_duplicate_nodes_rejected():
    graph = EvidenceGraph()
    n1 = GraphNode(node_id="dup:1", node_type="device", label="First")
    n2 = GraphNode(node_id="dup:1", node_type="device", label="Second")
    graph.nodes.extend([n1, n2])

    with pytest.raises(ResearchValidationError, match="Duplicate node IDs"):
        graph.validate_referential_integrity()


def test_evidence_graph_invalid_relationship_rejected():
    graph = EvidenceGraph()
    n1 = GraphNode(node_id="a", node_type="device", label="A")
    n2 = GraphNode(node_id="b", node_type="device", label="B")
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_edge(GraphEdge(source_id="a", target_id="b", relationship="invented_relation"))

    with pytest.raises(ResearchValidationError, match="Invalid edge relationship"):
        graph.validate_referential_integrity()


def test_evidence_graph_deterministic_sorting():
    graph = EvidenceGraph()
    graph.add_node(GraphNode(node_id="z_node", node_type="observation", label="Z"))
    graph.add_node(GraphNode(node_id="a_node", node_type="device", label="A"))
    graph.add_edge(GraphEdge(source_id="z_node", target_id="a_node", relationship="observed_on"))

    graph.sort_deterministic()
    assert graph.nodes[0].node_type == "device"
    assert graph.nodes[1].node_type == "observation"


def test_research_report_serialization_and_validation():
    graph = EvidenceGraph()
    n1 = GraphNode(node_id="dev:1", node_type="device", label="Device 1")
    n2 = GraphNode(node_id="ev:1", node_type="observation", label="Obs 1")
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_edge(GraphEdge(source_id="ev:1", target_id="dev:1", relationship="observed_on"))

    report = ResearchReport(
        schema_version="0.1.0",
        aegis_version="0.1.0",
        evaluated_at_utc="2026-10-22T00:00:00Z",
        source_inputs=[{"source_ref": "test.json", "source_type": "device_evidence"}],
        graph=graph,
        evaluations=[
            RuleEvaluationRecord(
                evaluation_id="eval:1",
                rule_id="RULE-1",
                rule_version="0.1.0",
                outcome="supported",
                certainty="directly_observed",
                conclusion="Test conclusion",
            )
        ],
        claims=[
            ResearchClaim(
                claim_id="claim:1",
                title="Test Claim",
                category="boot_chain_integrity",
                certainty="directly_observed",
                summary="Test summary",
            )
        ],
        conflicts=[],
        missing_evidence_inventory=["ro.bootloader"],
        summary={
            "total_sources": 1,
            "total_evaluations": 1,
            "total_claims": 1,
            "total_conflicts": 0,
        },
    )

    json_str = report.to_json()
    loaded = ResearchReport.from_json(json_str)

    assert loaded.schema_version == "0.1.0"
    assert len(loaded.claims) == 1
    assert loaded.claims[0].title == "Test Claim"
    assert len(loaded.evaluations) == 1
    assert len(loaded.graph.nodes) == 2


def test_research_report_mismatched_summary_rejected():
    graph = EvidenceGraph()
    report_dict = {
        "schema_version": "0.1.0",
        "aegis_version": "0.1.0",
        "evaluated_at_utc": "2026-10-22T00:00:00Z",
        "source_inputs": [],
        "graph": graph.to_dict(),
        "evaluations": [],
        "claims": [],
        "conflicts": [],
        "missing_evidence_inventory": [],
        "summary": {
            "total_claims": 99,  # Mismatch!
            "total_evaluations": 0,
            "total_conflicts": 0,
        },
    }

    with pytest.raises(ResearchValidationError, match="Summary total_claims"):
        ResearchReport.from_dict(report_dict)
