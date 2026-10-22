"""Evidence graph builder and topology coordinator."""

from __future__ import annotations

from typing import Any

from aegis.research.models import (
    EvidenceGraph,
    GraphEdge,
    GraphNode,
    NormalizedEvidence,
    ResearchClaim,
    RuleEvaluationRecord,
)


def build_evidence_graph(
    evidence_items: list[NormalizedEvidence],
    evaluations: list[RuleEvaluationRecord],
    claims: list[ResearchClaim],
    source_inputs: list[dict[str, Any]],
) -> EvidenceGraph:
    """Construct an interconnected, validated evidence graph connecting raw evidence to derived claims."""
    graph = EvidenceGraph()

    # Track devices to avoid duplicate nodes
    device_nodes: dict[str, str] = {}  # key -> node_id

    # 1. Add Source Inputs / Devices / Artifacts / Snapshots
    for src in source_inputs:
        src_type = src.get("source_type", "unknown")
        src_ref = str(src.get("source_ref", "src"))
        c_hash = src.get("content_hash") or "unhashed"
        safe_ref = "".join(c if c.isalnum() or c in "._-" else "_" for c in src_ref)

        if src_type in ("device_evidence", "snapshot"):
            dev_fp = src.get("device_fingerprint") or {}
            mfr = dev_fp.get("manufacturer") or "Generic"
            model = dev_fp.get("model") or "Android Device"
            dev_key = f"{mfr}:{model}:{dev_fp.get('build_id', 'unknown')}"

            if dev_key not in device_nodes:
                dev_node_id = f"node:dev:{safe_ref}"
                device_nodes[dev_key] = dev_node_id
                graph.add_node(
                    GraphNode(
                        node_id=dev_node_id,
                        node_type="device",
                        label=f"{mfr} {model}",
                        properties={
                            "fingerprint": dev_fp,
                            "provenance": src.get("provenance", "unverified"),
                        },
                    )
                )
            else:
                dev_node_id = device_nodes[dev_key]

            if src_type == "snapshot":
                snap_node_id = f"node:snap:{c_hash[:12]}"
                graph.add_node(
                    GraphNode(
                        node_id=snap_node_id,
                        node_type="snapshot",
                        label=f"Snapshot {c_hash[:8]}",
                        properties={
                            "content_hash": c_hash,
                            "source_ref": src_ref,
                            "schema_version": src.get("schema_version"),
                        },
                    )
                )
                graph.add_edge(
                    GraphEdge(
                        source_id=snap_node_id,
                        target_id=dev_node_id,
                        relationship="observed_on",
                    )
                )

        elif src_type == "semantic_diff":
            diff_node_id = f"node:diff:{safe_ref}"
            graph.add_node(
                GraphNode(
                    node_id=diff_node_id,
                    node_type="diff",
                    label=f"Diff {safe_ref}",
                    properties={
                        "device_comparability": src.get("device_comparability"),
                        "baseline_hash": src.get("baseline_snapshot_hash"),
                        "current_hash": src.get("current_snapshot_hash"),
                    },
                )
            )

        elif src_type == "firmware_report":
            fw_node_id = f"node:fw:{safe_ref}"
            graph.add_node(
                GraphNode(
                    node_id=fw_node_id,
                    node_type="firmware_artifact",
                    label=f"Firmware: {src.get('target_name', safe_ref)}",
                    properties={
                        "target_name": src.get("target_name"),
                        "target_type": src.get("target_type"),
                        "source_ref": src_ref,
                    },
                )
            )

    # 2. Add Normalized Evidence Nodes
    evidence_nodes: set[str] = set()
    for ev in evidence_items:
        node_id = f"node:ev:{ev.evidence_id}"
        evidence_nodes.add(node_id)

        node_type = "observation"
        if ev.source_type == "firmware_report":
            node_type = "firmware_component" if ev.category != "firmware_artifact" else "firmware_artifact"

        graph.add_node(
            GraphNode(
                node_id=node_id,
                node_type=node_type,
                label=ev.label,
                properties={
                    "evidence_id": ev.evidence_id,
                    "key": ev.key,
                    "status": ev.status,
                    "value": ev.value,
                    "provenance": ev.provenance,
                    "category": ev.category,
                },
            )
        )

        # Connect evidence to its parent device, snapshot, or firmware artifact if present
        if ev.source_type == "device_evidence":
            dev_fp = ev.device_fingerprint or {}
            dev_key = f"{dev_fp.get('manufacturer', 'Generic')}:{dev_fp.get('model', 'Android Device')}:{dev_fp.get('build_id', 'unknown')}"
            if dev_key in device_nodes:
                graph.add_edge(
                    GraphEdge(
                        source_id=node_id,
                        target_id=device_nodes[dev_key],
                        relationship="observed_on",
                    )
                )

        elif ev.source_type == "snapshot":
            c_hash = ev.source_content_hash or "unhashed"
            snap_node_id = f"node:snap:{c_hash[:12]}"
            if any(n.node_id == snap_node_id for n in graph.nodes):
                graph.add_edge(
                    GraphEdge(
                        source_id=node_id,
                        target_id=snap_node_id,
                        relationship="contained_in",
                    )
                )

        elif ev.source_type == "firmware_report":
            # Connect to firmware container
            fw_node = next((n for n in graph.nodes if n.node_type == "firmware_artifact"), None)
            if fw_node and fw_node.node_id != node_id:
                graph.add_edge(
                    GraphEdge(
                        source_id=node_id,
                        target_id=fw_node.node_id,
                        relationship="contained_in",
                    )
                )

    # 3. Add Rule Evaluation Nodes and Edges
    for ev_record in evaluations:
        eval_node_id = f"node:eval:{ev_record.evaluation_id}"
        graph.add_node(
            GraphNode(
                node_id=eval_node_id,
                node_type="rule_evaluation",
                label=f"Rule: {ev_record.rule_id}",
                properties={
                    "outcome": ev_record.outcome,
                    "certainty": ev_record.certainty,
                    "conclusion": ev_record.conclusion,
                },
            )
        )

        # Connect rule to input evidence (requires)
        for in_ev_id in ev_record.input_evidence_ids:
            target_ev_node = f"node:ev:{in_ev_id}"
            if target_ev_node in evidence_nodes:
                graph.add_edge(
                    GraphEdge(
                        source_id=eval_node_id,
                        target_id=target_ev_node,
                        relationship="requires",
                    )
                )

    # 4. Add Claim Nodes and Edges
    for claim in claims:
        claim_node_id = f"node:claim:{claim.claim_id}"
        graph.add_node(
            GraphNode(
                node_id=claim_node_id,
                node_type="claim",
                label=claim.title,
                properties={
                    "category": claim.category,
                    "certainty": claim.certainty,
                    "summary": claim.summary,
                    "evaluating_rule_id": claim.evaluating_rule_id,
                },
            )
        )

        # Connect claim to evaluating rule
        rule_node = next(
            (n for n in graph.nodes if n.node_type == "rule_evaluation" and claim.evaluating_rule_id in n.label),
            None,
        )
        if rule_node:
            graph.add_edge(
                GraphEdge(
                    source_id=claim_node_id,
                    target_id=rule_node.node_id,
                    relationship="derived_from",
                )
            )

        # Connect claim to supporting evidence
        for supp_id in claim.supporting_evidence_ids:
            target_ev_node = f"node:ev:{supp_id}"
            if target_ev_node in evidence_nodes:
                graph.add_edge(
                    GraphEdge(
                        source_id=claim_node_id,
                        target_id=target_ev_node,
                        relationship="supports",
                    )
                )

        # Connect claim to contradicting evidence
        for contra_id in claim.contradicting_evidence_ids:
            target_ev_node = f"node:ev:{contra_id}"
            if target_ev_node in evidence_nodes:
                graph.add_edge(
                    GraphEdge(
                        source_id=claim_node_id,
                        target_id=target_ev_node,
                        relationship="contradicts",
                    )
                )

    # Ensure referential integrity and deterministic ordering
    graph.validate_referential_integrity()
    graph.sort_deterministic()
    return graph
