"""Automated tests for AEGIS evidence snapshots, canonical hashing, and integrity verification."""

import copy
import json
from pathlib import Path

import pytest

from aegis.schema import EvidenceReport
from aegis.snapshots import (
    SNAPSHOT_FORMAT_VERSION,
    SnapshotFormatError,
    SnapshotIntegrityError,
    canonical_json_bytes,
    compute_content_hash,
    create_snapshot,
    load_snapshot,
    save_snapshot,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_evidence_dict() -> dict:
    sample_path = FIXTURES_DIR / "sample_evidence.json"
    return json.loads(sample_path.read_text(encoding="utf-8"))


@pytest.fixture
def sample_report(sample_evidence_dict) -> EvidenceReport:
    return EvidenceReport.from_dict(sample_evidence_dict)


def test_snapshot_creation_and_canonical_hash_stability(sample_report):
    """Same canonical evidence content produces identical content hash across independent runs."""
    snap1 = create_snapshot(sample_report)
    snap2 = create_snapshot(sample_report)

    assert snap1.snapshot_format_version == SNAPSHOT_FORMAT_VERSION
    assert snap1.content_hash == snap2.content_hash
    assert snap1.snapshot_id == snap2.snapshot_id
    assert len(snap1.content_hash) == 64
    assert len(snap1.snapshot_id) == 16


def test_dict_key_insertion_order_does_not_change_hash(sample_evidence_dict):
    """Varying dictionary key order does not alter canonical content hash."""
    rev_evidence = {k: sample_evidence_dict[k] for k in reversed(list(sample_evidence_dict.keys()))}

    snap_normal = create_snapshot(sample_evidence_dict)
    snap_rev = create_snapshot(rev_evidence)

    assert snap_normal.content_hash == snap_rev.content_hash


def test_envelope_timestamp_changes_do_not_change_content_hash(sample_evidence_dict):
    """Execution and creation timestamps do not alter content hash of the evidence."""
    ev1 = copy.deepcopy(sample_evidence_dict)
    ev2 = copy.deepcopy(sample_evidence_dict)

    ev1["collection"]["timestamp_utc"] = "2026-01-01T00:00:00Z"
    ev2["collection"]["timestamp_utc"] = "2026-12-31T23:59:59Z"

    snap1 = create_snapshot(ev1)
    snap2 = create_snapshot(ev2)

    assert snap1.content_hash == snap2.content_hash


def test_meaningful_observation_change_changes_hash(sample_evidence_dict):
    """Modifying an observation value changes the content hash."""
    ev_modified = copy.deepcopy(sample_evidence_dict)
    ev_modified["observations"][0]["value"] = "ModifiedVendor"

    snap_orig = create_snapshot(sample_evidence_dict)
    snap_mod = create_snapshot(ev_modified)

    assert snap_orig.content_hash != snap_mod.content_hash


def test_observation_status_change_changes_hash(sample_evidence_dict):
    """Changing an observation status alters the content hash."""
    ev_status_changed = copy.deepcopy(sample_evidence_dict)
    ev_status_changed["observations"][0]["status"] = "inaccessible"

    snap_orig = create_snapshot(sample_evidence_dict)
    snap_status = create_snapshot(ev_status_changed)

    assert snap_orig.content_hash != snap_status.content_hash


def test_unicode_and_escaped_strings_serialize_consistently():
    """Unicode characters serialize predictably without platform-specific variations."""
    payload1 = {"key": "test", "val": "안녕 🛡️ Android — äöü"}
    payload2 = {"val": "안녕 🛡️ Android — äöü", "key": "test"}

    bytes1 = canonical_json_bytes(payload1)
    bytes2 = canonical_json_bytes(payload2)

    assert bytes1 == bytes2
    assert compute_content_hash(payload1) == compute_content_hash(payload2)


def test_type_preservation():
    """Null, boolean, integer, float, and string retain exact types in canonical serialization."""
    payload = {
        "null_val": None,
        "bool_val": False,
        "int_val": 42,
        "float_val": 3.14,
        "str_val": "true",
    }
    raw = canonical_json_bytes(payload).decode("utf-8")

    assert '"null_val":null' in raw
    assert '"bool_val":false' in raw
    assert '"int_val":42' in raw
    assert '"str_val":"true"' in raw


def test_snapshot_creation_does_not_mutate_source(sample_evidence_dict):
    """Source evidence dictionary is not mutated during snapshot creation."""
    snapshot_copy = copy.deepcopy(sample_evidence_dict)
    create_snapshot(sample_evidence_dict)

    assert sample_evidence_dict == snapshot_copy


def test_save_and_load_roundtrip_with_integrity(tmp_path, sample_report):
    """Snapshot saves to disk and reloads with verified cryptographic integrity."""
    snap = create_snapshot(sample_report, notes="Test baseline snapshot")
    target_path = tmp_path / "baseline_snapshot.json"

    saved = save_snapshot(snap, target_path)
    assert saved.is_file()

    loaded = load_snapshot(saved, verify_integrity=True)
    assert loaded.snapshot_id == snap.snapshot_id
    assert loaded.content_hash == snap.content_hash
    assert loaded.metadata.get("notes") == "Test baseline snapshot"
    assert len(loaded.observations) == len(snap.observations)


def test_save_snapshot_overwrite_protection(tmp_path, sample_report):
    """Attempting to overwrite without flag raises FileExistsError."""
    snap = create_snapshot(sample_report)
    target = tmp_path / "protected.json"

    save_snapshot(snap, target)
    assert target.is_file()

    with pytest.raises(FileExistsError):
        save_snapshot(snap, target, overwrite=False)

    # With overwrite=True, succeeds
    saved2 = save_snapshot(snap, target, overwrite=True)
    assert saved2 == target.resolve()


def test_load_snapshot_tampered_integrity_fails(tmp_path, sample_report):
    """Altered content in snapshot file triggers SnapshotIntegrityError."""
    snap = create_snapshot(sample_report)
    target = tmp_path / "tampered.json"
    save_snapshot(snap, target)

    # Tamper with file on disk
    data = json.loads(target.read_text(encoding="utf-8"))
    data["observations"][0]["value"] = "FORGED_VAL"
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")

    with pytest.raises(SnapshotIntegrityError) as exc_info:
        load_snapshot(target, verify_integrity=True)

    assert "Snapshot integrity verification failed" in str(exc_info.value)


def test_load_snapshot_unsupported_version_fails(tmp_path, sample_report):
    """Unsupported snapshot format version triggers SnapshotFormatError."""
    snap = create_snapshot(sample_report)
    target = tmp_path / "bad_version.json"
    save_snapshot(snap, target)

    data = json.loads(target.read_text(encoding="utf-8"))
    data["snapshot_format_version"] = "9.9.9"
    target.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(SnapshotFormatError) as exc_info:
        load_snapshot(target, verify_integrity=False)

    assert "Unsupported snapshot_format_version '9.9.9'" in str(exc_info.value)


def test_load_snapshot_missing_file_raises_not_found():
    """Loading nonexistent snapshot path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_snapshot("nonexistent_snapshot_path.json")
