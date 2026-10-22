"""Automated tests for AEGIS semantic diff engine and device comparability safeguards."""

from pathlib import Path

import pytest

from aegis.diff import (
    IncomparableDeviceError,
    compare_snapshots,
)
from aegis.schema import EvidenceReport
from aegis.snapshots import create_snapshot

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def baseline_snapshot():
    sample_file = FIXTURES_DIR / "sample_evidence.json"
    rep = EvidenceReport.from_json(sample_file.read_text(encoding="utf-8"))
    return create_snapshot(rep, notes="Baseline synthetic")


@pytest.fixture
def updated_snapshot():
    sample_file = FIXTURES_DIR / "sample_evidence_updated.json"
    rep = EvidenceReport.from_json(sample_file.read_text(encoding="utf-8"))
    return create_snapshot(rep, notes="Updated synthetic")


def test_identical_snapshots_produce_zero_changes(baseline_snapshot):
    """Comparing a snapshot against itself yields all unchanged records and zero changes."""
    diff = compare_snapshots(baseline_snapshot, baseline_snapshot)

    assert diff.comparability_state == "match"
    assert diff.is_cross_device_override is False
    assert diff.summary.unchanged == len(baseline_snapshot.observations)
    assert diff.summary.value_changed == 0
    assert diff.summary.status_changed == 0
    assert diff.summary.added == 0
    assert diff.summary.removed == 0
    assert diff.baseline_hash == diff.current_hash


def test_semantic_diff_detects_value_changes(baseline_snapshot, updated_snapshot):
    """Diff between baseline and updated synthetic fixture detects OEM system update."""
    diff = compare_snapshots(baseline_snapshot, updated_snapshot)

    assert diff.comparability_state == "match"
    assert diff.summary.value_changed == 1
    assert diff.summary.unchanged == 3
    assert diff.summary.status_changed == 2
    assert diff.summary.added == 1
    assert diff.summary.removed == 0

    val_changes = {c.key: c for c in diff.changes if c.classification == "value_changed"}
    assert "build.version.release" in val_changes
    rel_change = val_changes["build.version.release"]
    assert rel_change.old_value == "12"
    assert rel_change.new_value == "13"
    assert "Value changed from '12' to '13'" in rel_change.explanation

    status_changes = {c.key: c for c in diff.changes if c.classification == "status_changed"}
    assert "boot.vbmeta_state" in status_changes
    assert "kernel.version" in status_changes
    vb_change = status_changes["boot.vbmeta_state"]
    assert vb_change.old_status == "unsupported"
    assert vb_change.new_status == "observed"

    added_obs = {c.key: c for c in diff.changes if c.classification == "added"}
    assert "build.version.security_patch" in added_obs


def test_status_transition_classification(baseline_snapshot):
    """Observation status transition (e.g., observed -> inaccessible) is classified as status_changed."""
    modified_dict = baseline_snapshot.to_dict()
    for obs in modified_dict["observations"]:
        if obs["key"] == "boot.flash_locked":
            obs["status"] = "inaccessible"
            obs["value"] = None
            obs["error"] = "SELinux denied read access"

    from aegis.snapshots import EvidenceSnapshot
    snap2 = EvidenceSnapshot.from_dict(modified_dict)

    diff = compare_snapshots(baseline_snapshot, snap2)
    assert diff.summary.status_changed == 1

    changed = next(c for c in diff.changes if c.classification == "status_changed")
    assert changed.key == "boot.flash_locked"
    assert changed.old_status == "observed"
    assert changed.new_status == "inaccessible"


def test_added_and_removed_observations(baseline_snapshot):
    """Observations existing only in one snapshot are classified as added or removed."""
    curr_dict = baseline_snapshot.to_dict()

    # Remove an observation from current
    curr_dict["observations"] = [o for o in curr_dict["observations"] if o["key"] != "product.model"]

    # Add a new observation to current
    curr_dict["observations"].append(
        {
            "key": "custom.security_flag",
            "label": "Custom Flag",
            "status": "observed",
            "value": "enabled",
            "raw_value": "enabled",
            "error": None,
            "redacted": False,
        }
    )

    from aegis.snapshots import EvidenceSnapshot
    diff = compare_snapshots(baseline_snapshot, EvidenceSnapshot.from_dict(curr_dict))

    assert diff.summary.removed == 1
    assert diff.summary.added == 1

    removed_item = next(c for c in diff.changes if c.classification == "removed")
    assert removed_item.key == "product.model"

    added_item = next(c for c in diff.changes if c.classification == "added")
    assert added_item.key == "custom.security_flag"


def test_cross_device_mismatch_blocked_by_default(baseline_snapshot):
    """Comparing snapshots from different devices raises IncomparableDeviceError."""
    other_dict = baseline_snapshot.to_dict()
    other_dict["device"]["model"] = "Pixel-8"
    other_dict["device"]["manufacturer"] = "Google"
    other_dict["device"]["serial_redacted"] = "P8***99"

    from aegis.snapshots import EvidenceSnapshot
    diff_target = EvidenceSnapshot.from_dict(other_dict)

    with pytest.raises(IncomparableDeviceError) as exc_info:
        compare_snapshots(baseline_snapshot, diff_target, allow_different_devices=False)

    assert "Cannot compare snapshots from different devices" in str(exc_info.value)
    assert "--allow-different-devices" in str(exc_info.value)


def test_cross_device_override_permitted_when_flag_set(baseline_snapshot):
    """Passing allow_different_devices=True succeeds and marks comparability_state accordingly."""
    other_dict = baseline_snapshot.to_dict()
    other_dict["device"]["model"] = "SM-A525F"

    from aegis.snapshots import EvidenceSnapshot
    diff_target = EvidenceSnapshot.from_dict(other_dict)

    diff = compare_snapshots(baseline_snapshot, diff_target, allow_different_devices=True)
    assert diff.comparability_state == "mismatch_override"
    assert diff.is_cross_device_override is True


def test_synthetic_vs_physical_provenance_conflict_blocked(baseline_snapshot):
    """Comparing physical device evidence against synthetic fixture evidence is blocked by default."""
    physical_dict = baseline_snapshot.to_dict()
    physical_dict["provenance"]["is_synthetic"] = False

    from aegis.snapshots import EvidenceSnapshot
    diff_target = EvidenceSnapshot.from_dict(physical_dict)

    with pytest.raises(IncomparableDeviceError) as exc_info:
        compare_snapshots(baseline_snapshot, diff_target, allow_different_devices=False)

    assert "provenance mismatch" in str(exc_info.value)


def test_missing_identity_produces_unverified_comparability(baseline_snapshot):
    """When device identities lack distinguishing fields, comparability is marked unverified."""
    unverified_dict = baseline_snapshot.to_dict()
    unverified_dict["device"] = {"serial_redacted": "", "state": "device"}

    from aegis.snapshots import EvidenceSnapshot
    diff_target = EvidenceSnapshot.from_dict(unverified_dict)

    diff = compare_snapshots(baseline_snapshot, diff_target)
    assert diff.comparability_state == "identity_unverified"
    assert diff.is_cross_device_override is False


def test_diff_output_ordering_is_deterministic(baseline_snapshot, updated_snapshot):
    """Output observation differences are deterministically sorted by key alphabetically."""
    diff = compare_snapshots(baseline_snapshot, updated_snapshot)
    keys = [c.key for c in diff.changes]

    assert keys == sorted(keys)


def test_summary_counts_reconciled(baseline_snapshot, updated_snapshot):
    """Summary counts match total detailed records exactly."""
    diff = compare_snapshots(baseline_snapshot, updated_snapshot)
    s = diff.summary

    total_records = s.unchanged + s.value_changed + s.status_changed + s.added + s.removed + s.incomparable
    assert len(diff.changes) == total_records
