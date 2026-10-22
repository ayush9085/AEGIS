"""Unit tests for research engine coordinator and multi-source correlation."""

from pathlib import Path

import pytest

from aegis.research.engine import analyze_research_inputs

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_research_engine_single_device_report():
    report_file = FIXTURES_DIR / "sample_evidence.json"
    report = analyze_research_inputs([report_file])

    assert report.schema_version == "0.1.0"
    assert len(report.source_inputs) == 1
    assert report.source_inputs[0]["source_type"] == "device_evidence"
    assert len(report.graph.nodes) > 0
    assert len(report.graph.edges) > 0
    assert len(report.evaluations) > 0
    assert report.summary["total_sources"] == 1


def test_research_engine_multiple_reports():
    f1 = FIXTURES_DIR / "sample_evidence.json"
    f2 = FIXTURES_DIR / "sample_evidence_updated.json"
    report = analyze_research_inputs([f1, f2])

    assert len(report.source_inputs) == 2
    assert report.summary["total_sources"] == 2
    assert report.summary["total_evidence_items"] > 0
    assert len(report.claims) > 0


def test_research_engine_directory_input(tmp_path):
    d = tmp_path / "research_bundle"
    d.mkdir()

    f1 = d / "ev1.json"
    f1.write_text((FIXTURES_DIR / "sample_evidence.json").read_text(encoding="utf-8"), encoding="utf-8")

    f2 = d / "ev2.json"
    f2.write_text((FIXTURES_DIR / "sample_evidence_updated.json").read_text(encoding="utf-8"), encoding="utf-8")

    report = analyze_research_inputs([d])
    assert report.summary["total_sources"] == 2


def test_research_engine_symlink_escape_prevented(tmp_path):
    root_dir = tmp_path / "safe_dir"
    root_dir.mkdir()

    outside_dir = tmp_path / "outside_dir"
    outside_dir.mkdir()
    secret_file = outside_dir / "secret.json"
    secret_file.write_text((FIXTURES_DIR / "sample_evidence.json").read_text(encoding="utf-8"), encoding="utf-8")

    symlink = root_dir / "escaped.json"
    try:
        symlink.symlink_to(secret_file)
    except OSError:
        pytest.skip("Symlinks not supported on host")

    # Symlinked files pointing outside must not be collected
    with pytest.raises(ValueError, match="No JSON evidence reports found"):
        analyze_research_inputs([root_dir])


def test_research_engine_missing_path_raises_not_found():
    with pytest.raises(FileNotFoundError, match="Input path does not exist"):
        analyze_research_inputs([Path("nonexistent_path_xyz.json")])


def test_research_engine_empty_input_list():
    with pytest.raises(ValueError, match="At least one input file or directory"):
        analyze_research_inputs([])


def test_research_engine_determinism():
    f1 = FIXTURES_DIR / "sample_evidence.json"
    f2 = FIXTURES_DIR / "sample_evidence_updated.json"

    r1 = analyze_research_inputs([f1, f2])
    r2 = analyze_research_inputs([f1, f2])

    # Graph nodes and edges must match identically
    assert [n.node_id for n in r1.graph.nodes] == [n.node_id for n in r2.graph.nodes]
    assert [(e.source_id, e.target_id, e.relationship) for e in r1.graph.edges] == [
        (e.source_id, e.target_id, e.relationship) for e in r2.graph.edges
    ]
    assert [c.claim_id for c in r1.claims] == [c.claim_id for c in r2.claims]
    assert [e.evaluation_id for e in r1.evaluations] == [e.evaluation_id for e in r2.evaluations]
