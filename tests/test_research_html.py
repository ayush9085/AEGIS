"""Unit tests for self-contained HTML research report generator and XSS escaping."""

import re

from aegis.reports.research_html import render_html_research_report
from aegis.research.models import (
    EvidenceGraph,
    GraphEdge,
    GraphNode,
    ResearchClaim,
    ResearchReport,
    RuleEvaluationRecord,
)


def test_research_html_basic_structure():
    graph = EvidenceGraph()
    graph.add_node(GraphNode(node_id="dev:1", node_type="device", label="Pixel 7"))
    graph.add_node(GraphNode(node_id="ev:1", node_type="observation", label="Verified Boot State"))
    graph.add_edge(GraphEdge(source_id="ev:1", target_id="dev:1", relationship="observed_on"))

    report = ResearchReport(
        schema_version="0.1.0",
        aegis_version="0.1.0",
        source_inputs=[{
            "source_ref": "test.json",
            "source_type": "device_evidence",
            "provenance": "physical_handset",
            "device_fingerprint": {"manufacturer": "Google", "model": "Pixel 7", "android_version": "14"},
        }],
        graph=graph,
        evaluations=[
            RuleEvaluationRecord(
                evaluation_id="eval:1",
                rule_id="RULE-BOOT-CHAIN-COMPLETE",
                rule_version="0.1.0",
                outcome="supported",
                certainty="directly_observed",
                conclusion="Core parameters observed",
            )
        ],
        claims=[
            ResearchClaim(
                claim_id="claim:1",
                title="Boot-Chain Telemetry Available",
                category="boot_chain_integrity",
                certainty="directly_observed",
                summary="Verified boot parameters observed.",
                supporting_evidence_ids=["ev:1"],
                evaluating_rule_id="RULE-BOOT-CHAIN-COMPLETE",
            )
        ],
        conflicts=[],
        missing_evidence_inventory=["ro.boot.flash.locked"],
        summary={
            "total_sources": 1,
            "total_evaluations": 1,
            "total_claims": 1,
            "total_conflicts": 0,
            "graph_nodes_count": 2,
            "graph_edges_count": 1,
        },
    )

    html_out = render_html_research_report(report)
    assert "<!DOCTYPE html>" in html_out
    assert "AEGIS Research Intelligence Report" in html_out
    assert "Pixel 7" in html_out
    assert "Boot-Chain Telemetry Available" in html_out
    assert "RULE-BOOT-CHAIN-COMPLETE" in html_out
    assert "ro.boot.flash.locked" in html_out

    # Verify zero external CDN scripts/fonts/stylesheets
    assert not re.search(r'<script[^>]+src=["\']http', html_out, re.IGNORECASE)
    assert not re.search(r'<link[^>]+href=["\']http', html_out, re.IGNORECASE)


def test_research_html_strict_xss_escaping():
    graph = EvidenceGraph()
    malicious_title = "<script>alert('xss_claim')</script>"
    malicious_summary = "<img src=x onerror=alert('xss_sum')>"
    malicious_ref = "<svg onload=alert('xss_src')>"

    graph.add_node(GraphNode(node_id="dev:1", node_type="device", label="<script>xss_dev</script>"))

    report = ResearchReport(
        schema_version="0.1.0",
        aegis_version="0.1.0",
        evaluated_at_utc="2026-10-22T00:00:00Z",
        source_inputs=[{"source_ref": malicious_ref, "source_type": "device_evidence"}],
        graph=graph,
        evaluations=[
            RuleEvaluationRecord(
                evaluation_id="eval:1",
                rule_id="RULE-1",
                rule_version="0.1.0",
                outcome="supported",
                certainty="directly_observed",
                conclusion="<marquee>xss_conclusion</marquee>",
            )
        ],
        claims=[
            ResearchClaim(
                claim_id="claim:1",
                title=malicious_title,
                category="test",
                certainty="directly_observed",
                summary=malicious_summary,
            )
        ],
        conflicts=[
            {
                "key": "<script>xss_key</script>",
                "label": "Conflict",
                "evidence_sources": [{"source_ref": "ref1", "value": "<script>val</script>", "provenance": "phys"}],
            }
        ],
        missing_evidence_inventory=["<script>xss_missing</script>"],
        summary={"total_claims": 1, "total_evaluations": 1, "total_conflicts": 1},
    )

    html_out = render_html_research_report(report)

    # All injected scripts must be escaped
    assert "<script>alert('xss_claim')</script>" not in html_out
    assert "&lt;script&gt;alert(&#x27;xss_claim&#x27;)&lt;/script&gt;" in html_out
    assert "<img src=x onerror=" not in html_out
    assert "&lt;img src=x onerror=" in html_out
    assert "<svg onload=" not in html_out
    assert "<marquee>" not in html_out
