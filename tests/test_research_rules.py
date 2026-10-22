"""Unit tests for explainable research rules and prerequisite accounting."""

from aegis.research.models import NormalizedEvidence
from aegis.research.rules import (
    BootChainCompletenessRule,
    CrossSourceConsistencyRule,
    DiffBootDriftRule,
    FirmwareBootValidationRule,
    InaccessibleEvidenceLimitRule,
    ProvenanceBoundaryRule,
)


def _make_ev(key: str, value: object, status: str = "observed", src_type: str = "device_evidence", prov: str = "physical_handset") -> NormalizedEvidence:
    return NormalizedEvidence(
        evidence_id=f"ev:{key}",
        source_type=src_type,
        source_ref="test_ref",
        source_schema_version="0.1.0",
        category="test_cat",
        key=key,
        label=key,
        status=status,
        value=value,
        provenance=prov,
    )


def test_boot_chain_completeness_rule_complete():
    rule = BootChainCompletenessRule()
    evidence = [
        _make_ev("ro.bootloader", "c2-1.0"),
        _make_ev("ro.boot.verifiedbootstate", "green"),
        _make_ev("ro.boot.vbmeta.device_state", "locked"),
        _make_ev("ro.boot.flash.locked", "1"),
        _make_ev("ro.boot.veritymode", "enforcing"),
    ]

    record, claim = rule.evaluate(evidence)
    assert record.outcome == "supported"
    assert record.certainty == "directly_observed"
    assert len(record.prerequisites_missing) == 0
    assert claim is not None
    assert claim.certainty == "directly_observed"


def test_boot_chain_completeness_rule_incomplete():
    rule = BootChainCompletenessRule()
    evidence = [
        _make_ev("ro.bootloader", "c2-1.0"),
        _make_ev("ro.boot.verifiedbootstate", "green"),
        # Missing flash.locked and veritymode
    ]

    record, claim = rule.evaluate(evidence)
    assert record.outcome == "insufficient_evidence"
    assert record.certainty == "insufficient_evidence"
    assert "flash_locked" in record.prerequisites_missing
    assert claim is not None
    assert claim.category == "evidence_gap"


def test_diff_boot_drift_rule_detects_changes():
    rule = DiffBootDriftRule()
    evidence = [
        _make_ev("ro.boot.verifiedbootstate", {"baseline": "green", "current": "orange"}, status="value_changed", src_type="semantic_diff", prov="same_device_updated")
    ]

    record, claim = rule.evaluate(evidence)
    assert record.outcome == "supported"
    assert record.certainty == "strongly_supported"
    assert "detected" in record.conclusion.lower()
    assert claim is not None


def test_diff_boot_drift_rule_incomparable():
    rule = DiffBootDriftRule()
    evidence = [
        _make_ev("ro.bootloader", {"baseline": "a", "current": "b"}, status="value_changed", src_type="semantic_diff", prov="different_device")
    ]

    record, _claim = rule.evaluate(evidence)
    assert record.outcome == "incomparable"
    assert record.certainty == "conflicting_evidence"


def test_firmware_boot_validation_rule():
    rule = FirmwareBootValidationRule()
    valid_ev = [
        _make_ev("boot.header_version", 4, status="observed", src_type="firmware_report", prov="firmware_artifact"),
        _make_ev("boot.kernel_size_bytes", 8192, status="observed", src_type="firmware_report", prov="firmware_artifact"),
    ]

    record, claim = rule.evaluate(valid_ev)
    assert record.outcome == "supported"
    assert record.certainty == "strongly_supported"
    assert claim is not None

    invalid_ev = [
        _make_ev("boot.header_version", 99, status="unsupported", src_type="firmware_report", prov="firmware_artifact"),
    ]
    rec_inv, claim_inv = rule.evaluate(invalid_ev)
    assert rec_inv.outcome == "contradicted"
    assert claim_inv is not None


def test_cross_source_consistency_rule_match_and_mismatch():
    rule = CrossSourceConsistencyRule()

    # Matching
    match_ev = [
        _make_ev("ro.build.version.release", "14", status="observed", src_type="device_evidence"),
        _make_ev("boot.declared_os_version", "14", status="observed", src_type="firmware_report"),
    ]
    rec_m, claim_m = rule.evaluate(match_ev)
    assert rec_m.outcome == "supported"
    assert rec_m.certainty == "strongly_supported"
    assert claim_m is not None

    # Mismatching
    mismatch_ev = [
        _make_ev("ro.build.version.release", "14", status="observed", src_type="device_evidence"),
        _make_ev("boot.declared_os_version", "12", status="observed", src_type="firmware_report"),
    ]
    rec_mis, claim_mis = rule.evaluate(mismatch_ev)
    assert rec_mis.outcome == "contradicted"
    assert rec_mis.certainty == "conflicting_evidence"
    assert len(rec_mis.conflicting_evidence_ids) > 0
    assert claim_mis is not None


def test_provenance_boundary_rule_flags_synthetic_mixing():
    rule = ProvenanceBoundaryRule()

    mixed_ev = [
        _make_ev("ro.product.model", "Mock Phone", prov="synthetic"),
        _make_ev("ro.build.id", "REAL_BUILD_1", prov="physical_handset"),
    ]
    record, claim = rule.evaluate(mixed_ev)
    assert record.outcome == "contradicted"
    assert record.certainty == "conflicting_evidence"
    assert claim is not None

    pure_ev = [
        _make_ev("ro.product.model", "Real Phone", prov="physical_handset"),
        _make_ev("ro.build.id", "REAL_BUILD_1", prov="physical_handset"),
    ]
    record_p, claim_p = rule.evaluate(pure_ev)
    assert record_p.outcome == "supported"
    assert claim_p is None


def test_inaccessible_evidence_limit_rule():
    rule = InaccessibleEvidenceLimitRule()

    inacc_ev = [
        _make_ev("ro.boot.flash.locked", None, status="inaccessible"),
        _make_ev("ro.boot.veritymode", None, status="unsupported"),
    ]
    record, claim = rule.evaluate(inacc_ev)
    assert record.outcome == "supported"
    assert claim is not None
    assert claim.category == "evidence_gap"
    assert len(claim.missing_evidence) == 2
