"""Coordination engine for multi-source research analysis and evidence correlation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aegis import __version__
from aegis.research.graph import build_evidence_graph
from aegis.research.models import (
    DEFAULT_RESEARCH_LIMITATIONS,
    NormalizedEvidence,
    ResearchClaim,
    ResearchReport,
    RuleEvaluationRecord,
)
from aegis.research.normalize import load_and_normalize_path
from aegis.research.rules import DEFAULT_RULE_REGISTRY, BaseRule


def analyze_research_inputs(
    paths: list[Path],
    rule_registry: list[BaseRule] | None = None,
) -> ResearchReport:
    """Load, normalize, correlate, and evaluate multiple AEGIS evidence reports offline."""
    if not paths:
        raise ValueError("At least one input file or directory must be provided for research analysis")

    if rule_registry is None:
        rule_registry = DEFAULT_RULE_REGISTRY

    resolved_files: list[Path] = []
    for p in paths:
        res_p = p.resolve()
        if not res_p.exists():
            raise FileNotFoundError(f"Input path does not exist: {p}")
        if res_p.is_file():
            resolved_files.append(res_p)
        elif res_p.is_dir():
            for child in sorted(res_p.rglob("*.json")):
                if child.is_file():
                    # Symlink guard
                    try:
                        resolved_child = child.resolve()
                        if resolved_child.is_relative_to(res_p):
                            resolved_files.append(resolved_child)
                    except (OSError, ValueError):
                        continue

    if not resolved_files:
        raise ValueError("No JSON evidence reports found in specified input path(s)")

    # Deduplicate files while preserving order
    unique_files: list[Path] = []
    seen_files: set[Path] = set()
    for f in resolved_files:
        if f not in seen_files:
            seen_files.add(f)
            unique_files.append(f)

    # 1. Load and Normalize
    source_inputs: list[dict[str, Any]] = []
    all_evidence: list[NormalizedEvidence] = []

    for file_path in unique_files:
        meta, items = load_and_normalize_path(file_path)
        source_inputs.append(meta)
        all_evidence.extend(items)

    # 2. Detect Cross-Source Direct Conflicts
    conflicts = _detect_cross_source_conflicts(all_evidence)

    # 3. Missing Evidence Inventory
    missing_inventory = _build_missing_evidence_inventory(all_evidence)

    # 4. Evaluate Rules
    evaluations: list[RuleEvaluationRecord] = []
    claims: list[ResearchClaim] = []

    for rule in rule_registry:
        eval_record, claim = rule.evaluate(all_evidence)
        evaluations.append(eval_record)
        if claim:
            claims.append(claim)

    # 5. Build Interconnected Evidence Graph
    graph = build_evidence_graph(all_evidence, evaluations, claims, source_inputs)

    # 6. Reconcile Summary Counts
    outcomes: dict[str, int] = {
        "supported": 0,
        "contradicted": 0,
        "insufficient_evidence": 0,
        "not_applicable": 0,
        "incomparable": 0,
        "error": 0,
    }
    certainties: dict[str, int] = {
        "directly_observed": 0,
        "strongly_supported": 0,
        "tentatively_supported": 0,
        "insufficient_evidence": 0,
        "conflicting_evidence": 0,
    }
    for ev in evaluations:
        if ev.outcome in outcomes:
            outcomes[ev.outcome] += 1
        if ev.certainty in certainties:
            certainties[ev.certainty] += 1

    summary = {
        "total_sources": len(source_inputs),
        "total_evidence_items": len(all_evidence),
        "total_evaluations": len(evaluations),
        "total_claims": len(claims),
        "total_conflicts": len(conflicts),
        "outcomes": outcomes,
        "certainties": certainties,
        "graph_nodes_count": len(graph.nodes),
        "graph_edges_count": len(graph.edges),
    }

    timestamp = datetime.now(UTC).isoformat()

    return ResearchReport(
        schema_version="0.1.0",
        aegis_version=__version__,
        evaluated_at_utc=timestamp,
        source_inputs=source_inputs,
        graph=graph,
        evaluations=evaluations,
        claims=claims,
        conflicts=conflicts,
        missing_evidence_inventory=missing_inventory,
        summary=summary,
        limitations=list(DEFAULT_RESEARCH_LIMITATIONS),
    )


def _detect_cross_source_conflicts(evidence: list[NormalizedEvidence]) -> list[dict[str, Any]]:
    """Identify direct contradictions across sources for identical observed keys."""
    conflicts: list[dict[str, Any]] = []

    # Group by key for comparable observed properties
    by_key: dict[str, list[NormalizedEvidence]] = {}
    for e in evidence:
        if e.status == "observed" and e.value is not None:
            by_key.setdefault(e.key, []).append(e)

    for key, items in by_key.items():
        if len(items) < 2:
            continue
        # Check if values diverge across distinct sources
        first_val = str(items[0].value).strip()
        divergent = [it for it in items[1:] if str(it.value).strip() != first_val]
        if divergent:
            conflicts.append({
                "key": key,
                "label": items[0].label,
                "conflict_type": "divergent_values",
                "evidence_sources": [
                    {
                        "evidence_id": it.evidence_id,
                        "source_ref": it.source_ref,
                        "value": it.value,
                        "provenance": it.provenance,
                    }
                    for it in items
                ],
            })

    return conflicts


def _build_missing_evidence_inventory(evidence: list[NormalizedEvidence]) -> list[str]:
    """Catalog standard security observation keys that were absent or non-observed."""
    standard_keys = [
        "ro.bootloader",
        "ro.boot.verifiedbootstate",
        "ro.boot.vbmeta.device_state",
        "ro.boot.flash.locked",
        "ro.boot.veritymode",
        "ro.build.version.security_patch",
        "ro.build.fingerprint",
    ]
    observed_keys = {e.key for e in evidence if e.status == "observed"}
    return [k for k in standard_keys if k not in observed_keys]
