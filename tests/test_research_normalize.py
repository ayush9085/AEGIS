"""Unit tests for evidence normalization across Phase 1, 2, and 3 reports."""

import json
from pathlib import Path

import pytest

from aegis.diff import compare_snapshots
from aegis.firmware.models import ArtifactInventory, FirmwareFinding, FirmwareReport
from aegis.research.models import ResearchCompatibilityError, ResearchValidationError
from aegis.research.normalize import detect_source_type, normalize_source_data
from aegis.schema import EvidenceReport
from aegis.snapshots import create_snapshot

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_normalize_device_evidence():
    ev_path = FIXTURES_DIR / "sample_evidence.json"
    data = json.loads(ev_path.read_text(encoding="utf-8"))

    assert detect_source_type(data) == "device_evidence"
    meta, items = normalize_source_data(data, "sample_evidence.json")

    assert meta["source_type"] == "device_evidence"
    assert meta["provenance"] == "synthetic"
    assert len(items) == len(data["observations"])

    keys = {item.key for item in items}
    assert "build.version.release" in keys
    assert "boot.flash_locked" in keys


def test_normalize_snapshot():
    ev_path = FIXTURES_DIR / "sample_evidence.json"
    ev = EvidenceReport.from_json(ev_path.read_text(encoding="utf-8"))
    snap = create_snapshot(ev, notes="Unit test snapshot")
    snap_dict = snap.to_dict()

    assert detect_source_type(snap_dict) == "snapshot"
    meta, items = normalize_source_data(snap_dict, "snapshot.json")

    assert meta["source_type"] == "snapshot"
    assert meta["content_hash"] == snap.content_hash
    assert len(items) == len(snap.observations)
    assert items[0].source_content_hash == snap.content_hash


def test_normalize_semantic_diff():
    ev1 = EvidenceReport.from_json((FIXTURES_DIR / "sample_evidence.json").read_text(encoding="utf-8"))
    ev2 = EvidenceReport.from_json((FIXTURES_DIR / "sample_evidence_updated.json").read_text(encoding="utf-8"))
    snap1 = create_snapshot(ev1)
    snap2 = create_snapshot(ev2)
    diff = compare_snapshots(snap1, snap2)
    diff_dict = diff.to_dict()

    assert detect_source_type(diff_dict) == "semantic_diff"
    meta, items = normalize_source_data(diff_dict, "diff.json")

    assert meta["source_type"] == "semantic_diff"
    assert meta["device_comparability"] == diff.comparability_state
    assert len(items) == len(diff.changes)
    assert any(item.status == "value_changed" for item in items)


def test_normalize_firmware_report():
    fw_report = FirmwareReport(
        schema_version="0.1.0",
        aegis_version="0.1.0",
        analyzed_at_utc="2026-10-22T00:00:00Z",
        target_name="boot.img",
        target_type="file",
        artifacts=[
            ArtifactInventory(
                path="boot.img",
                detected_format="android_boot_image",
                size_bytes=4096,
                sha256="abc123sha",
                parser_used="aegis_boot_img_parser",
                parse_status="observed",
            )
        ],
        findings=[
            FirmwareFinding(
                finding_id="boot.img:header:version",
                category="header",
                key="boot.header_version",
                label="Boot Header Version",
                status="observed",
                value=4,
                evidence_source="boot.img",
                parser="aegis_boot_img_parser",
                parser_version="0.1.0",
            )
        ],
        summary={"total_artifacts": 1, "total_findings": 1},
    )
    fw_dict = fw_report.to_dict()

    assert detect_source_type(fw_dict) == "firmware_report"
    meta, items = normalize_source_data(fw_dict, "firmware.json")

    assert meta["source_type"] == "firmware_report"
    assert meta["provenance"] == "firmware_artifact"
    # 1 finding + 1 artifact overview item = 2 items
    assert len(items) == 2

    finding_items = [it for it in items if it.key == "boot.header_version"]
    assert len(finding_items) == 1
    assert finding_items[0].value == 4


def test_unsupported_data_raises_compatibility_error():
    with pytest.raises(ResearchCompatibilityError, match="Unrecognized AEGIS evidence format"):
        normalize_source_data({"random_field": "unknown"}, "corrupt.json")


def test_non_dict_data_raises_validation_error():
    with pytest.raises(ResearchValidationError, match="Expected JSON object"):
        normalize_source_data(["not", "a", "dict"], "list.json")  # type: ignore
