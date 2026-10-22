"""Curated, documented ground-truth evaluation corpus covering AEGIS Phases 1-4 capabilities."""

from __future__ import annotations

from typing import Any

from aegis.evaluation.models import (
    EVALUATION_CORPUS_VERSION,
    EVALUATION_SCHEMA_VERSION,
    CaseExpectation,
    EvaluationCase,
    EvaluationManifest,
    RuleOutcomeExpectation,
)


def _get_base_phase1_device_data() -> dict[str, Any]:
    """Synthetic baseline Phase 1 device evidence report."""
    return {
        "schema_version": "0.1.0",
        "tool": {"name": "aegis", "version": "0.1.0"},
        "collection": {
            "timestamp_utc": "2026-10-22T00:00:00Z",
            "method": "adb_read_only",
            "scope": "phase_one_allowlist",
            "consent_given": True,
            "host_os": "Darwin 27.0.0",
            "host_python": "3.12.0",
            "host_adb_version": "Android Debug Bridge version 1.0.41",
            "is_synthetic": True,
        },
        "device": {
            "serial_redacted": "syn***01",
            "state": "device",
            "manufacturer": "Google",
            "model": "Pixel 8",
            "product_name": "shiba",
            "android_version": "14",
            "sdk_version": "34",
            "security_patch": "2026-06-05",
            "build_id": "UQ1A.240205.004",
            "fingerprint": "google/shiba/shiba:14/UQ1A.240205.004/11267587:user/release-keys",
        },
        "observations": [
            {
                "key": "ro.product.manufacturer",
                "label": "Manufacturer",
                "status": "observed",
                "value": "Google",
                "raw_value": "Google",
                "source_command": ["adb", "shell", "getprop", "ro.product.manufacturer"],
                "collected_at": "2026-10-22T00:00:00Z",
                "error": None,
                "caveat": "Userspace property; identifies brand, not hardware authenticity.",
                "redacted": False,
            },
            {
                "key": "ro.product.model",
                "label": "Model",
                "status": "observed",
                "value": "Pixel 8",
                "raw_value": "Pixel 8",
                "source_command": ["adb", "shell", "getprop", "ro.product.model"],
                "collected_at": "2026-10-22T00:00:00Z",
                "error": None,
                "caveat": "Userspace property; identifies model name.",
                "redacted": False,
            },
            {
                "key": "ro.build.version.release",
                "label": "Android Version",
                "status": "observed",
                "value": "14",
                "raw_value": "14",
                "source_command": ["adb", "shell", "getprop", "ro.build.version.release"],
                "collected_at": "2026-10-22T00:00:00Z",
                "error": None,
                "caveat": "Userspace property; reports major Android OS version.",
                "redacted": False,
            },
            {
                "key": "ro.build.id",
                "label": "Build ID",
                "status": "observed",
                "value": "UQ1A.240205.004",
                "raw_value": "UQ1A.240205.004",
                "source_command": ["adb", "shell", "getprop", "ro.build.id"],
                "collected_at": "2026-10-22T00:00:00Z",
                "error": None,
                "caveat": "Userspace build identifier.",
                "redacted": False,
            },
            {
                "key": "ro.bootloader",
                "label": "Bootloader Version",
                "status": "observed",
                "value": "ripcurrent-1.0-11000000",
                "raw_value": "ripcurrent-1.0-11000000",
                "source_command": ["adb", "shell", "getprop", "ro.bootloader"],
                "collected_at": "2026-10-22T00:00:00Z",
                "error": None,
                "caveat": "Primary bootloader identifier string.",
                "redacted": False,
            },
            {
                "key": "ro.boot.verifiedbootstate",
                "label": "Verified Boot State",
                "status": "observed",
                "value": "green",
                "raw_value": "green",
                "source_command": ["adb", "shell", "getprop", "ro.boot.verifiedbootstate"],
                "collected_at": "2026-10-22T00:00:00Z",
                "error": None,
                "caveat": "AVB boot state passed via kernel command line.",
                "redacted": False,
            },
            {
                "key": "ro.boot.vbmeta.device_state",
                "label": "VBMeta Device State",
                "status": "observed",
                "value": "locked",
                "raw_value": "locked",
                "source_command": ["adb", "shell", "getprop", "ro.boot.vbmeta.device_state"],
                "collected_at": "2026-10-22T00:00:00Z",
                "error": None,
                "caveat": "VBMeta device lock state.",
                "redacted": False,
            },
            {
                "key": "ro.boot.flash.locked",
                "label": "Flash Lock State",
                "status": "observed",
                "value": "1",
                "raw_value": "1",
                "source_command": ["adb", "shell", "getprop", "ro.boot.flash.locked"],
                "collected_at": "2026-10-22T00:00:00Z",
                "error": None,
                "caveat": "Indicates bootloader flash lock status (1=locked).",
                "redacted": False,
            },
            {
                "key": "ro.boot.veritymode",
                "label": "dm-verity Mode",
                "status": "observed",
                "value": "enforcing",
                "raw_value": "enforcing",
                "source_command": ["adb", "shell", "getprop", "ro.boot.veritymode"],
                "collected_at": "2026-10-22T00:00:00Z",
                "error": None,
                "caveat": "AVB verity enforcement status.",
                "redacted": False,
            },
        ],
    }


def _get_base_phase2_snapshot_data(is_synthetic: bool = True) -> dict[str, Any]:
    """Synthetic baseline Phase 2 evidence snapshot matching EvidenceSnapshot schema."""
    base_evidence = _get_base_phase1_device_data()
    return {
        "snapshot_format_version": "0.1.0",
        "snapshot_id": "snap-syn01",
        "content_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
        "created_at_utc": "2026-10-22T00:00:00Z",
        "source_schema_version": "0.1.0",
        "source_timestamp_utc": "2026-10-22T00:00:00Z",
        "provenance": {"is_synthetic": is_synthetic, "method": "adb_read_only"},
        "device": base_evidence["device"],
        "observations": base_evidence["observations"],
        "summary": {"total_observations": len(base_evidence["observations"])},
        "metadata": {"notes": "Synthetic baseline snapshot"},
    }


def _get_base_phase2_diff_data(has_drift: bool = True, incomparable: bool = False) -> dict[str, Any]:
    """Synthetic baseline Phase 2 semantic diff matching SemanticDiff schema."""
    changes = [
        {
            "key": "ro.boot.flash.locked",
            "label": "Flash Lock State",
            "old_value": "1",
            "new_value": "0" if has_drift else "1",
            "old_status": "observed",
            "new_status": "observed",
            "classification": "value_modified" if has_drift else "identical",
            "semantic_note": "Bootloader unlocked transition detected." if has_drift else "No change",
        }
    ]

    comp_state = "synthetic_vs_physical" if incomparable else "comparable"
    comp_reason = (
        "Baseline is physical device; target is synthetic fixture."
        if incomparable
        else "Matching device identity and synthetic provenance."
    )

    return {
        "diff_version": "0.1.0",
        "generated_at_utc": "2026-10-22T00:00:00Z",
        "comparability_state": comp_state,
        "comparability_reason": comp_reason,
        "cross_device_override": False,
        "baseline_ref": "snap-baseline.json",
        "current_ref": "snap-current.json",
        "baseline_hash": "1111111111111111111111111111111111111111111111111111111111111111",
        "current_hash": "2222222222222222222222222222222222222222222222222222222222222222",
        "changes": changes,
        "summary": {"total_changes": len(changes)},
    }


def _get_base_phase3_firmware_data(is_valid: bool = True, os_version: str = "14", model: str = "Pixel 8") -> dict[str, Any]:
    """Synthetic baseline Phase 3 firmware intelligence report matching FirmwareReport schema."""
    header_val = 4 if is_valid else 99
    header_st = "observed" if is_valid else "unsupported"

    artifacts = [
        {
            "path": "boot.img",
            "size_bytes": 33554432,
            "sha256": "3333333333333333333333333333333333333333333333333333333333333333",
            "detected_format": "android_boot_image",
            "parser_used": "aegis_boot_img_parser",
            "parse_status": "observed",
            "warnings": [],
            "error": None,
        }
    ]

    findings = [
        {
            "finding_id": "boot.img:header:version",
            "category": "header",
            "key": "boot.header_version",
            "label": "Boot Header Version",
            "status": header_st,
            "value": header_val,
            "evidence_source": "boot.img",
            "parser": "aegis_boot_img_parser",
            "parser_version": "0.1.0",
            "confidence": "authoritative",
            "caveat": "Parsed from header magic",
            "warnings": [],
        },
        {
            "finding_id": "system/build.prop:ro.product.model",
            "category": "build_prop",
            "key": "ro.product.model",
            "label": "Model",
            "status": "observed",
            "value": model,
            "evidence_source": "system/build.prop",
            "parser": "aegis_build_prop_parser",
            "parser_version": "0.1.0",
            "confidence": "authoritative",
            "caveat": None,
            "warnings": [],
        },
        {
            "finding_id": "system/build.prop:ro.build.version.release",
            "category": "build_prop",
            "key": "ro.build.version.release",
            "label": "Android Version",
            "status": "observed",
            "value": os_version,
            "evidence_source": "system/build.prop",
            "parser": "aegis_build_prop_parser",
            "parser_version": "0.1.0",
            "confidence": "authoritative",
            "caveat": None,
            "warnings": [],
        },
    ]

    return {
        "schema_version": "0.1.0",
        "aegis_version": "0.1.0",
        "analyzed_at_utc": "2026-10-22T00:00:00Z",
        "target_name": "boot.img",
        "target_type": "file",
        "artifacts": artifacts,
        "findings": findings,
        "summary": {"total_artifacts": len(artifacts), "total_findings": len(findings)},
        "limitations": ["Static analysis only"],
        "warnings": [],
    }


def build_evaluation_corpus() -> list[EvaluationCase]:
    """Build the comprehensive, curated suite of documented evaluation cases."""
    cases: list[EvaluationCase] = []

    # =========================================================================
    # CATEGORY A: Normalization and Schema Compatibility
    # =========================================================================
    cases.append(
        EvaluationCase(
            case_id="NORM-01-VALID-PHASE1",
            title="Normalize Valid Phase 1 Device Evidence",
            category="normalization",
            description="Ingest standard valid Phase 1 device observation report and verify field preservation.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "device_evidence.json", "data": _get_base_phase1_device_data()}],
            expectation=CaseExpectation(
                expected_status="passed",
                rule_expectations=[
                    RuleOutcomeExpectation(rule_id="RULE-BOOT-CHAIN-COMPLETE", expected_outcome="supported")
                ],
            ),
            rationale="Phase 1 schema is the primary live collection contract; all valid fields must normalize without loss.",
            limitations=["Synthetic fixture; no hardware-backed attestation."],
            tags=["normalization", "phase1"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="NORM-02-VALID-PHASE2-SNAPSHOT",
            title="Normalize Valid Phase 2 Snapshot",
            category="normalization",
            description="Ingest Phase 2 evidence snapshot and verify hash and observation extraction.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "snapshot.json", "data": _get_base_phase2_snapshot_data()}],
            expectation=CaseExpectation(
                expected_status="passed",
                rule_expectations=[
                    RuleOutcomeExpectation(rule_id="RULE-BOOT-CHAIN-COMPLETE", expected_outcome="supported")
                ],
            ),
            rationale="Phase 2 snapshots encapsulate Phase 1 evidence with canonical hashes.",
            limitations=["Uses simulated canonical hash."],
            tags=["normalization", "phase2", "snapshot"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="NORM-03-VALID-PHASE2-DIFF",
            title="Normalize Valid Phase 2 Semantic Diff",
            category="normalization",
            description="Ingest Phase 2 semantic diff report and extract differential observations.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "diff.json", "data": _get_base_phase2_diff_data(has_drift=True)}],
            expectation=CaseExpectation(
                expected_status="passed",
                rule_expectations=[
                    RuleOutcomeExpectation(rule_id="RULE-DIFF-BOOT-DRIFT", expected_outcome="supported")
                ],
            ),
            rationale="Semantic diffs represent state transitions between two snapshots.",
            limitations=["Synthetic transition of flash lock state."],
            tags=["normalization", "phase2", "diff"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="NORM-04-VALID-PHASE3-FIRMWARE",
            title="Normalize Valid Phase 3 Firmware Report",
            category="normalization",
            description="Ingest Phase 3 offline firmware intelligence report and map component findings.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "firmware.json", "data": _get_base_phase3_firmware_data()}],
            expectation=CaseExpectation(
                expected_status="passed",
                rule_expectations=[
                    RuleOutcomeExpectation(rule_id="RULE-FW-BOOT-VALID", expected_outcome="supported")
                ],
            ),
            rationale="Firmware reports represent static image header and property findings.",
            limitations=["Static metadata only; no cryptographic vendor signature verification."],
            tags=["normalization", "phase3", "firmware"],
        )
    )

    # Negative schema cases
    malformed_schema_data = _get_base_phase1_device_data()
    malformed_schema_data["schema_version"] = "99.0.0"
    cases.append(
        EvaluationCase(
            case_id="NORM-05-UNSUPPORTED-SCHEMA-VERSION",
            title="Reject Unsupported Schema Version",
            category="normalization",
            description="Ensure loader rejects reports with unknown or unsupported schema version.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "unsupported_schema.json", "data": malformed_schema_data}],
            expectation=CaseExpectation(
                expected_status="passed",
                expected_exception_type="ResearchCompatibilityError",
                expected_exception_message_substring="Unsupported",
            ),
            rationale="The research engine must not guess semantics of unknown schema versions.",
            limitations=[],
            tags=["normalization", "negative", "schema_version"],
        )
    )

    missing_obs_data = _get_base_phase1_device_data()
    del missing_obs_data["observations"]
    cases.append(
        EvaluationCase(
            case_id="NORM-06-MISSING-REQUIRED-FIELD",
            title="Reject Report Missing Mandatory Observations Field",
            category="normalization",
            description="Ensure loader rejects reports missing mandatory collection fields.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "missing_obs.json", "data": missing_obs_data}],
            expectation=CaseExpectation(
                expected_status="passed",
                expected_exception_type="ResearchCompatibilityError",
            ),
            rationale="Integrity validation prevents partial or corrupted reports from proceeding.",
            limitations=[],
            tags=["normalization", "negative", "integrity"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="NORM-07-MALFORMED-JSON",
            title="Reject Corrupted Malformed JSON Syntax",
            category="normalization",
            description="Ensure parser safely rejects syntactically malformed JSON with descriptive error.",
            provenance="synthetic_fixture",
            inputs=[{"type": "malformed_json", "name": "corrupt.json", "raw": '{"schema_version": "0.1.0", "unclosed":'}],
            expectation=CaseExpectation(
                expected_status="passed",
                expected_exception_type="ResearchValidationError",
                expected_exception_message_substring="Failed to read/parse JSON",
            ),
            rationale="Malformed JSON must raise ResearchValidationError without crashing.",
            limitations=[],
            tags=["normalization", "negative", "malformed_json"],
        )
    )

    # =========================================================================
    # CATEGORY B: Evidence Graph Integrity
    # =========================================================================
    cases.append(
        EvaluationCase(
            case_id="GRAPH-01-VALID-TOPOLOGY",
            title="Construct Valid Multi-Source Graph Topology",
            category="graph_integrity",
            description="Construct evidence graph connecting device, observation, rule, and claim nodes.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "device.json", "data": _get_base_phase1_device_data()}],
            expectation=CaseExpectation(
                expected_status="passed",
                expected_graph_node_count=17,  # 1 device + 9 observations + 6 rule evaluations + 1 claim = 17
            ),
            rationale="Graph must correctly represent all entities and verified relationships.",
            limitations=[],
            tags=["graph", "topology"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="GRAPH-02-DANGLING-EDGE-REJECTION",
            title="Reject Graph with Dangling Edge",
            category="graph_integrity",
            description="Ensure EvidenceGraph referential integrity rejects edge referencing non-existent node.",
            provenance="synthetic_fixture",
            inputs=[{
                "type": "graph_integrity_test",
                "test_kind": "dangling_edge",
            }],
            expectation=CaseExpectation(
                expected_status="passed",
                expected_exception_type="ResearchValidationError",
                expected_exception_message_substring="Dangling edge",
            ),
            rationale="Every edge must point to existing nodes to ensure referential integrity.",
            limitations=[],
            tags=["graph", "negative", "referential_integrity"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="GRAPH-03-DUPLICATE-NODE-REJECTION",
            title="Reject Graph with Duplicate Node Identifiers",
            category="graph_integrity",
            description="Ensure graph validation rejects duplicate node IDs in node list.",
            provenance="synthetic_fixture",
            inputs=[{
                "type": "graph_integrity_test",
                "test_kind": "duplicate_node",
            }],
            expectation=CaseExpectation(
                expected_status="passed",
                expected_exception_type="ResearchValidationError",
                expected_exception_message_substring="Duplicate node IDs",
            ),
            rationale="Node IDs must uniquely identify entities in the evidence graph.",
            limitations=[],
            tags=["graph", "negative", "node_uniqueness"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="GRAPH-04-INVALID-RELATIONSHIP-REJECTION",
            title="Reject Graph with Unsupported Edge Relationship",
            category="graph_integrity",
            description="Ensure graph validation rejects relationships outside typed schema.",
            provenance="synthetic_fixture",
            inputs=[{
                "type": "graph_integrity_test",
                "test_kind": "invalid_relationship",
            }],
            expectation=CaseExpectation(
                expected_status="passed",
                expected_exception_type="ResearchValidationError",
                expected_exception_message_substring="Invalid edge relationship",
            ),
            rationale="Only typed, justified relationships are permitted in AEGIS graphs.",
            limitations=[],
            tags=["graph", "negative", "relationship_types"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="GRAPH-05-DETERMINISTIC-SORTING",
            title="Deterministic Canonical Sorting of Graph Nodes and Edges",
            category="graph_integrity",
            description="Verify that nodes and edges sort canonically regardless of insertion order.",
            provenance="synthetic_fixture",
            inputs=[{
                "type": "graph_integrity_test",
                "test_kind": "deterministic_sorting",
            }],
            expectation=CaseExpectation(
                expected_status="passed",
                reproducibility_check=True,
            ),
            rationale="Deterministic serialization prevents spurious diffs in report hashes.",
            limitations=[],
            tags=["graph", "determinism"],
        )
    )

    # =========================================================================
    # CATEGORY C: Research-Rule Evaluation (All 6 Rules)
    # =========================================================================

    # 1. RULE-BOOT-CHAIN-COMPLETE
    cases.append(
        EvaluationCase(
            case_id="RULE-01-BOOT-CHAIN-COMPLETE-POS",
            title="RULE-BOOT-CHAIN-COMPLETE: All Core Targets Observed",
            category="rule_evaluation",
            description="Evaluate rule when all 5 essential boot targets are observed and accessible.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "device_complete.json", "data": _get_base_phase1_device_data()}],
            expectation=CaseExpectation(
                expected_status="passed",
                binary_ground_truth_label="positive",
                rule_expectations=[
                    RuleOutcomeExpectation(
                        rule_id="RULE-BOOT-CHAIN-COMPLETE",
                        expected_outcome="supported",
                        expected_certainty="directly_observed",
                        expected_prerequisites_missing=[],
                    )
                ],
            ),
            rationale="Complete boot parameters satisfy all prerequisites.",
            limitations=["Userspace observation over ADB."],
            tags=["rule", "RULE-BOOT-CHAIN-COMPLETE", "positive"],
        )
    )

    missing_boot_data = _get_base_phase1_device_data()
    missing_boot_data["observations"] = [
        o for o in missing_boot_data["observations"] if o["key"] != "ro.boot.verifiedbootstate"
    ]
    cases.append(
        EvaluationCase(
            case_id="RULE-02-BOOT-CHAIN-COMPLETE-NEG",
            title="RULE-BOOT-CHAIN-COMPLETE: Missing Core Target (Incomplete)",
            category="rule_evaluation",
            description="Evaluate rule when verifiedbootstate is missing from observations.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "device_incomplete.json", "data": missing_boot_data}],
            expectation=CaseExpectation(
                expected_status="passed",
                binary_ground_truth_label="negative",
                rule_expectations=[
                    RuleOutcomeExpectation(
                        rule_id="RULE-BOOT-CHAIN-COMPLETE",
                        expected_outcome="insufficient_evidence",
                        expected_certainty="insufficient_evidence",
                        expected_prerequisites_missing=["verifiedbootstate"],
                    )
                ],
            ),
            rationale="Absence of verifiedbootstate leaves bootloader verification state incomplete.",
            limitations=["Absence is not proof of compromise."],
            tags=["rule", "RULE-BOOT-CHAIN-COMPLETE", "negative"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="RULE-03-BOOT-CHAIN-COMPLETE-NA",
            title="RULE-BOOT-CHAIN-COMPLETE: Not Applicable Without Device Telemetry",
            category="rule_evaluation",
            description="Rule must return not_applicable when provided only static firmware reports.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "firmware_only.json", "data": _get_base_phase3_firmware_data()}],
            expectation=CaseExpectation(
                expected_status="passed",
                rule_expectations=[
                    RuleOutcomeExpectation(
                        rule_id="RULE-BOOT-CHAIN-COMPLETE",
                        expected_outcome="not_applicable",
                        expected_certainty="insufficient_evidence",
                    )
                ],
            ),
            rationale="Boot-chain completeness rule requires device or snapshot observations.",
            limitations=[],
            tags=["rule", "RULE-BOOT-CHAIN-COMPLETE", "not_applicable"],
        )
    )

    # 2. RULE-DIFF-BOOT-DRIFT
    cases.append(
        EvaluationCase(
            case_id="RULE-04-DIFF-BOOT-DRIFT-POS",
            title="RULE-DIFF-BOOT-DRIFT: Detects Bootloader State Transition",
            category="rule_evaluation",
            description="Detect boot parameter change across snapshots (locked to unlocked).",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "diff_drift.json", "data": _get_base_phase2_diff_data(has_drift=True)}],
            expectation=CaseExpectation(
                expected_status="passed",
                binary_ground_truth_label="positive",
                rule_expectations=[
                    RuleOutcomeExpectation(
                        rule_id="RULE-DIFF-BOOT-DRIFT",
                        expected_outcome="supported",
                        expected_certainty="strongly_supported",
                    )
                ],
            ),
            rationale="Flash locked status changed from 1 to 0 across snapshots.",
            limitations=[],
            tags=["rule", "RULE-DIFF-BOOT-DRIFT", "positive"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="RULE-05-DIFF-BOOT-DRIFT-INCOMPARABLE",
            title="RULE-DIFF-BOOT-DRIFT: Incomparable Provenance Boundary",
            category="rule_evaluation",
            description="Diff between incomparable snapshots must produce outcome incomparable.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "diff_incomp.json", "data": _get_base_phase2_diff_data(incomparable=True)}],
            expectation=CaseExpectation(
                expected_status="passed",
                rule_expectations=[
                    RuleOutcomeExpectation(
                        rule_id="RULE-DIFF-BOOT-DRIFT",
                        expected_outcome="incomparable",
                        expected_certainty="conflicting_evidence",
                    )
                ],
            ),
            rationale="Semantic diff marked incomparable due to synthetic/physical boundary crossing.",
            limitations=[],
            tags=["rule", "RULE-DIFF-BOOT-DRIFT", "incomparable"],
        )
    )

    # 3. RULE-FW-BOOT-VALID
    cases.append(
        EvaluationCase(
            case_id="RULE-06-FW-BOOT-VALID-POS",
            title="RULE-FW-BOOT-VALID: Valid Android Boot Header and Non-Zero Sections",
            category="rule_evaluation",
            description="Verify valid boot header version and kernel/ramdisk section sizes.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "fw_valid.json", "data": _get_base_phase3_firmware_data(is_valid=True)}],
            expectation=CaseExpectation(
                expected_status="passed",
                binary_ground_truth_label="positive",
                rule_expectations=[
                    RuleOutcomeExpectation(
                        rule_id="RULE-FW-BOOT-VALID",
                        expected_outcome="supported",
                        expected_certainty="strongly_supported",
                    )
                ],
            ),
            rationale="Boot header version 4 with valid kernel size satisfies structural checks.",
            limitations=["Static metadata parsing only."],
            tags=["rule", "RULE-FW-BOOT-VALID", "positive"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="RULE-07-FW-BOOT-VALID-NEG",
            title="RULE-FW-BOOT-VALID: Corrupt Boot Header or Zero Kernel Size",
            category="rule_evaluation",
            description="Verify corrupted boot image header is contradicted.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "fw_corrupt.json", "data": _get_base_phase3_firmware_data(is_valid=False)}],
            expectation=CaseExpectation(
                expected_status="passed",
                binary_ground_truth_label="negative",
                rule_expectations=[
                    RuleOutcomeExpectation(
                        rule_id="RULE-FW-BOOT-VALID",
                        expected_outcome="contradicted",
                        expected_certainty="strongly_supported",
                    )
                ],
            ),
            rationale="Invalid header version 99 and zero kernel size contradict structural validity.",
            limitations=[],
            tags=["rule", "RULE-FW-BOOT-VALID", "negative"],
        )
    )

    # 4. RULE-CROSS-SOURCE-CONSISTENCY
    cases.append(
        EvaluationCase(
            case_id="RULE-08-CROSS-SOURCE-MATCH",
            title="RULE-CROSS-SOURCE-CONSISTENCY: Matching Live Telemetry and Firmware Metadata",
            category="rule_evaluation",
            description="Correlate device telemetry and firmware metadata with matching OS and model.",
            provenance="synthetic_fixture",
            inputs=[
                {"type": "inline_json", "name": "device.json", "data": _get_base_phase1_device_data()},
                {"type": "inline_json", "name": "fw.json", "data": _get_base_phase3_firmware_data(os_version="14", model="Pixel 8")},
            ],
            expectation=CaseExpectation(
                expected_status="passed",
                expected_conflict_count=0,
                rule_expectations=[
                    RuleOutcomeExpectation(
                        rule_id="RULE-CROSS-SOURCE-CONSISTENCY",
                        expected_outcome="supported",
                        expected_certainty="strongly_supported",
                    )
                ],
            ),
            rationale="Device and firmware assert identical OS version (14) and model (Pixel 8).",
            limitations=["Does not prove runtime cryptographic authenticity."],
            tags=["rule", "RULE-CROSS-SOURCE-CONSISTENCY", "match"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="RULE-09-CROSS-SOURCE-MISMATCH",
            title="RULE-CROSS-SOURCE-CONSISTENCY: Conflicting OS Version Between Sources",
            category="rule_evaluation",
            description="Detect conflict when device reports Android 14 but firmware reports Android 13.",
            provenance="synthetic_fixture",
            inputs=[
                {"type": "inline_json", "name": "device.json", "data": _get_base_phase1_device_data()},
                {"type": "inline_json", "name": "fw_old.json", "data": _get_base_phase3_firmware_data(os_version="13", model="Pixel 8")},
            ],
            expectation=CaseExpectation(
                expected_status="passed",
                expected_conflict_count=1,
                rule_expectations=[
                    RuleOutcomeExpectation(
                        rule_id="RULE-CROSS-SOURCE-CONSISTENCY",
                        expected_outcome="contradicted",
                        expected_certainty="conflicting_evidence",
                    )
                ],
            ),
            rationale="Conflicting OS version values (14 vs 13) flagged and preserved.",
            limitations=[],
            tags=["rule", "RULE-CROSS-SOURCE-CONSISTENCY", "conflict"],
        )
    )

    # 5. RULE-PROVENANCE-BOUNDARY
    mixed_phase1 = _get_base_phase1_device_data()
    mixed_phase1["collection"]["is_synthetic"] = False
    cases.append(
        EvaluationCase(
            case_id="RULE-10-PROVENANCE-BOUNDARY-FLAGGED",
            title="RULE-PROVENANCE-BOUNDARY: Flags Mixed Synthetic and Physical Evidence",
            category="rule_evaluation",
            description="Ensure boundary rule contradicts correlation combining physical device with synthetic fixture.",
            provenance="mixed",
            inputs=[
                {"type": "inline_json", "name": "phys_device.json", "data": mixed_phase1},
                {"type": "inline_json", "name": "synth_snapshot.json", "data": _get_base_phase2_snapshot_data(is_synthetic=True)},
            ],
            expectation=CaseExpectation(
                expected_status="passed",
                rule_expectations=[
                    RuleOutcomeExpectation(
                        rule_id="RULE-PROVENANCE-BOUNDARY",
                        expected_outcome="contradicted",
                        expected_certainty="conflicting_evidence",
                    )
                ],
            ),
            rationale="Unwarranted mixing of synthetic fixtures and physical device data undermines integrity.",
            limitations=[],
            tags=["rule", "RULE-PROVENANCE-BOUNDARY", "mixed_provenance"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="RULE-11-PROVENANCE-BOUNDARY-PURE",
            title="RULE-PROVENANCE-BOUNDARY: Supported for Pure Synthetic Corpus",
            category="rule_evaluation",
            description="Verify boundary rule outcome supported when all evidence shares uniform synthetic provenance.",
            provenance="synthetic_fixture",
            inputs=[
                {"type": "inline_json", "name": "synth_dev.json", "data": _get_base_phase1_device_data()},
                {"type": "inline_json", "name": "synth_snap.json", "data": _get_base_phase2_snapshot_data(is_synthetic=True)},
            ],
            expectation=CaseExpectation(
                expected_status="passed",
                rule_expectations=[
                    RuleOutcomeExpectation(
                        rule_id="RULE-PROVENANCE-BOUNDARY",
                        expected_outcome="supported",
                        expected_certainty="directly_observed",
                    )
                ],
            ),
            rationale="All inputs share uniform provenance; no boundary crossing.",
            limitations=[],
            tags=["rule", "RULE-PROVENANCE-BOUNDARY", "pure_provenance"],
        )
    )

    # 6. RULE-INACCESSIBLE-EVIDENCE-LIMIT
    inaccessible_data = _get_base_phase1_device_data()
    inaccessible_data["observations"].append({
        "key": "ro.secure",
        "label": "SELinux Security State",
        "status": "inaccessible",
        "value": None,
        "raw_value": None,
        "source_command": ["adb", "shell", "getprop", "ro.secure"],
        "collected_at": "2026-10-22T00:00:00Z",
        "error": "Permission denied by SELinux policy",
        "caveat": "Telemetry restricted by platform.",
        "redacted": False,
    })
    cases.append(
        EvaluationCase(
            case_id="RULE-12-INACCESSIBLE-EVIDENCE-LIMIT-POS",
            title="RULE-INACCESSIBLE-EVIDENCE-LIMIT: Documents Observation Perimeter",
            category="rule_evaluation",
            description="Evaluate rule when one or more properties are inaccessible or unsupported.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "inaccessible_dev.json", "data": inaccessible_data}],
            expectation=CaseExpectation(
                expected_status="passed",
                rule_expectations=[
                    RuleOutcomeExpectation(
                        rule_id="RULE-INACCESSIBLE-EVIDENCE-LIMIT",
                        expected_outcome="supported",
                        expected_certainty="directly_observed",
                    )
                ],
            ),
            rationale="Inaccessible properties define explicit limits on conclusions.",
            limitations=[],
            tags=["rule", "RULE-INACCESSIBLE-EVIDENCE-LIMIT", "inaccessible"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="RULE-13-INACCESSIBLE-EVIDENCE-LIMIT-VERIFIED-ACCESSIBLE",
            title="RULE-INACCESSIBLE-EVIDENCE-LIMIT: Confirms Accessible When Zero Inaccessible",
            category="rule_evaluation",
            description="Rule confirms accessibility when zero inaccessible properties are present.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "all_observed.json", "data": _get_base_phase1_device_data()}],
            expectation=CaseExpectation(
                expected_status="passed",
                rule_expectations=[
                    RuleOutcomeExpectation(
                        rule_id="RULE-INACCESSIBLE-EVIDENCE-LIMIT",
                        expected_outcome="supported",
                        expected_certainty="directly_observed",
                    )
                ],
            ),
            rationale="No inaccessible properties present in observation set; accessibility boundary verified.",
            limitations=[],
            tags=["rule", "RULE-INACCESSIBLE-EVIDENCE-LIMIT", "accessible"],
        )
    )

    # =========================================================================
    # CATEGORY D: Cross-Source Correlation
    # =========================================================================
    cases.append(
        EvaluationCase(
            case_id="CORR-01-CONFLICTING-MODEL-VALUES",
            title="Correlate Conflicting Product Model Values",
            category="cross_source_correlation",
            description="Ingest reports where device asserts Pixel 8 but firmware asserts Pixel 7.",
            provenance="synthetic_fixture",
            inputs=[
                {"type": "inline_json", "name": "device.json", "data": _get_base_phase1_device_data()},
                {"type": "inline_json", "name": "fw_pixel7.json", "data": _get_base_phase3_firmware_data(os_version="14", model="Pixel 7")},
            ],
            expectation=CaseExpectation(
                expected_status="passed",
                expected_conflict_count=1,
            ),
            rationale="Model name discrepancy is logged as an unresolved cross-source conflict.",
            limitations=[],
            tags=["correlation", "conflict", "model"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="CORR-02-PARTIAL-CORRELATION-GAPS",
            title="Partial Correlation with Cataloged Missing Inventory",
            category="cross_source_correlation",
            description="Correlate device telemetry missing security patch with baseline missing inventory catalog.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "partial.json", "data": missing_boot_data}],
            expectation=CaseExpectation(
                expected_status="passed",
                expected_missing_inventory_keys=["ro.boot.verifiedbootstate"],
            ),
            rationale="Missing baseline boot targets must be explicitly itemized in missing_evidence_inventory.",
            limitations=[],
            tags=["correlation", "missing_inventory"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="CORR-03-DUPLICATE-SOURCE-ARTIFACTS",
            title="Deduplicate Repeated Identical Source Artifacts",
            category="cross_source_correlation",
            description="Analyze repeated identical report inputs and ensure clean deduplication without artifact explosion.",
            provenance="synthetic_fixture",
            inputs=[
                {"type": "inline_json", "name": "dev1.json", "data": _get_base_phase1_device_data()},
                {"type": "inline_json", "name": "dev1_dup.json", "data": _get_base_phase1_device_data()},
            ],
            expectation=CaseExpectation(
                expected_status="passed",
            ),
            rationale="Deduplication ensures graph and evaluations remain deterministic and bounded.",
            limitations=[],
            tags=["correlation", "deduplication"],
        )
    )

    # =========================================================================
    # CATEGORY E: Security and Robustness
    # =========================================================================
    xss_device_data = _get_base_phase1_device_data()
    xss_device_data["device"]["model"] = "<script>alert('xss')</script>"
    xss_device_data["observations"][0]["value"] = "<b>Injected</b>"
    cases.append(
        EvaluationCase(
            case_id="SEC-01-HTML-INJECTION-DEFENSE",
            title="HTML/Script Injection Escaping in Report Fields",
            category="security_robustness",
            description="Inject HTML and script payloads in device properties and verify strict escaping in HTML report.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "xss_dev.json", "data": xss_device_data}],
            expectation=CaseExpectation(
                expected_status="passed",
            ),
            rationale="All dynamic values must be HTML-escaped to prevent script execution in web views.",
            limitations=[],
            tags=["security", "xss", "escaping"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="SEC-02-SYMLINK-ESCAPE-PREVENTION",
            title="Symlink Escape Prevention Outside Target Directory",
            category="security_robustness",
            description="Verify that directory input scanning rejects symlinks escaping target directory.",
            provenance="synthetic_fixture",
            inputs=[{"type": "symlink_escape_test"}],
            expectation=CaseExpectation(
                expected_status="passed",
            ),
            rationale="Directory scanning must strictly reject symlinks that escape target boundaries.",
            limitations=[],
            tags=["security", "symlink_escape", "path_traversal"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="SEC-03-OVERSIZED-INPUT-PROTECTION",
            title="Oversized Input Handling and Resource Bounds",
            category="security_robustness",
            description="Ensure oversized or truncated files are handled safely without unhandled memory exhaustion.",
            provenance="synthetic_fixture",
            inputs=[{"type": "oversized_input_test"}],
            expectation=CaseExpectation(
                expected_status="passed",
            ),
            rationale="Unbounded memory allocation from large files is prevented.",
            limitations=[],
            tags=["security", "oversized", "dos_defense"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="SEC-04-OFFLINE-EXECUTION-CONFIRMATION",
            title="Zero Network Activity and No Code Execution",
            category="security_robustness",
            description="Verify that evaluation runner executes 100% offline without opening network sockets or subshells.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "offline_check.json", "data": _get_base_phase1_device_data()}],
            expectation=CaseExpectation(
                expected_status="passed",
            ),
            rationale="AEGIS evaluation must operate offline without telemetry, cloud dependencies, or subprocess exploits.",
            limitations=[],
            tags=["security", "offline", "zero_network"],
        )
    )

    # =========================================================================
    # CATEGORY F: Reproducibility and Regression
    # =========================================================================
    cases.append(
        EvaluationCase(
            case_id="REPRO-01-DETERMINISTIC-REPORT-HASH",
            title="Repeated Ingestion Produces Bit-Identical Report and Hash",
            category="reproducibility",
            description="Execute analysis twice on identical inputs and verify byte-for-byte identical content excluding timestamp.",
            provenance="synthetic_fixture",
            inputs=[{"type": "inline_json", "name": "repro_dev.json", "data": _get_base_phase1_device_data()}],
            expectation=CaseExpectation(
                expected_status="passed",
                reproducibility_check=True,
            ),
            rationale="Deterministic analysis guarantees reproducible scientific verification.",
            limitations=[],
            tags=["reproducibility", "determinism", "hash_stability"],
        )
    )

    cases.append(
        EvaluationCase(
            case_id="REPRO-02-FILESYSTEM-ORDER-INDEPENDENCE",
            title="Determinism Independent of Input Argument Order",
            category="reproducibility",
            description="Verify that passing inputs in forward vs reverse order yields identical evaluations and graph nodes.",
            provenance="synthetic_fixture",
            inputs=[
                {"type": "inline_json", "name": "dev_a.json", "data": _get_base_phase1_device_data()},
                {"type": "inline_json", "name": "fw_b.json", "data": _get_base_phase3_firmware_data()},
            ],
            expectation=CaseExpectation(
                expected_status="passed",
                reproducibility_check=True,
            ),
            rationale="Canonical sorting ensures graph referential order does not depend on file traversal sequence.",
            limitations=[],
            tags=["reproducibility", "ordering_independence"],
        )
    )

    # Physical device observation case (using existing consented Xiaomi report)
    cases.append(
        EvaluationCase(
            case_id="REAL-01-PHYSICAL-HANDSET-EVAL",
            title="Physical Handset Observation Telemetry Evaluation",
            category="reproducibility",
            description="Exercise research rules against real physical device telemetry from existing consented Xiaomi fixture.",
            provenance="physical_handset",
            inputs=[{"type": "file_path", "path": "reports/real-device-20261022/evidence.json"}],
            expectation=CaseExpectation(
                expected_status="passed",
                rule_expectations=[
                    RuleOutcomeExpectation(
                        rule_id="RULE-PROVENANCE-BOUNDARY",
                        expected_outcome="supported",
                        expected_certainty="directly_observed",
                    )
                ],
            ),
            rationale="Confirms engine operates seamlessly on physical-handset observations while strictly preserving physical provenance.",
            limitations=["Single device model (Xiaomi 2312DRAABI, HyperOS/Android 15)."],
            tags=["physical_handset", "provenance", "xiaomi"],
        )
    )

    return cases


def load_default_manifest() -> EvaluationManifest:
    """Construct the official default evaluation manifest."""
    cases = build_evaluation_corpus()
    return EvaluationManifest(
        schema_version=EVALUATION_SCHEMA_VERSION,
        corpus_version=EVALUATION_CORPUS_VERSION,
        title="AEGIS Ground-Truth Research Evaluation Corpus",
        description="Comprehensive ground-truth evaluation corpus for AEGIS Phases 1-4 capabilities.",
        created_at_utc="2026-10-22T00:00:00Z",
        cases=cases,
    )
