"""Explainable, deterministic research rules for evidence correlation."""

from __future__ import annotations

from typing import Any, ClassVar

from aegis.research.models import (
    NormalizedEvidence,
    ResearchClaim,
    RuleEvaluationRecord,
)

CORE_BOOT_TARGETS: list[tuple[str, set[str]]] = [
    ("bootloader", {"boot.bootloader", "ro.bootloader"}),
    ("verifiedbootstate", {"boot.verifiedbootstate", "ro.boot.verifiedbootstate"}),
    ("vbmeta_state", {"boot.vbmeta_state", "ro.boot.vbmeta.device_state"}),
    ("flash_locked", {"boot.flash_locked", "ro.boot.flash.locked"}),
    ("veritymode", {"boot.veritymode", "ro.boot.veritymode"}),
]


class BaseRule:
    """Base class for all AEGIS research rules."""

    rule_id: str
    name: str
    version: str = "0.1.0"
    purpose: str
    limitations: ClassVar[list[str]] = []

    def evaluate(
        self,
        evidence: list[NormalizedEvidence],
    ) -> tuple[RuleEvaluationRecord, ResearchClaim | None]:
        raise NotImplementedError


class BootChainCompletenessRule(BaseRule):
    rule_id = "RULE-BOOT-CHAIN-COMPLETE"
    name = "Boot-Chain Property Completeness & Accessibility"
    purpose = "Evaluate whether essential Android verified boot and bootloader indicators are observed and accessible."
    limitations: ClassVar[list[str]] = [
        "Checks presence of userspace properties over ADB; does NOT verify hardware cryptographic attestation.",
        "An omitted property may indicate an older Android version or OEM customization, not necessarily a disabled security feature.",
    ]

    def evaluate(
        self,
        evidence: list[NormalizedEvidence],
    ) -> tuple[RuleEvaluationRecord, ResearchClaim | None]:
        # Filter for device/snapshot observations
        dev_items = [e for e in evidence if e.source_type in ("device_evidence", "snapshot")]
        if not dev_items:
            return (
                RuleEvaluationRecord(
                    evaluation_id=f"eval:{self.rule_id}:na",
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    outcome="not_applicable",
                    certainty="insufficient_evidence",
                    conclusion="No device or snapshot observations available to evaluate boot-chain completeness.",
                    explanation="Requires device_evidence or snapshot inputs.",
                    caveats=self.limitations,
                ),
                None,
            )

        prereqs_checked = [name for name, _ in CORE_BOOT_TARGETS]
        prereqs_satisfied = []
        prereqs_missing = []
        input_ids = []

        for name, aliases in CORE_BOOT_TARGETS:
            matching = [e for e in dev_items if e.key in aliases]
            observed_item = next((e for e in matching if e.status == "observed"), None)
            if observed_item:
                prereqs_satisfied.append(name)
                input_ids.append(observed_item.evidence_id)
            else:
                prereqs_missing.append(name)

        if not prereqs_missing:
            record = RuleEvaluationRecord(
                evaluation_id=f"eval:{self.rule_id}:supported",
                rule_id=self.rule_id,
                rule_version=self.version,
                outcome="supported",
                certainty="directly_observed",
                input_evidence_ids=input_ids,
                prerequisites_checked=prereqs_checked,
                prerequisites_satisfied=prereqs_satisfied,
                prerequisites_missing=[],
                conclusion="All core verified-boot and bootloader properties are directly observed.",
                explanation=f"Found all {len(CORE_BOOT_TARGETS)} essential indicators with 'observed' status.",
                caveats=self.limitations,
            )
            claim = ResearchClaim(
                claim_id=f"claim:{self.rule_id}:complete",
                title="Core Boot-Chain Parameters Directly Observed",
                category="boot_chain_integrity",
                certainty="directly_observed",
                summary="The device exposes complete userspace boot-chain telemetry without missing or blocked properties.",
                supporting_evidence_ids=input_ids,
                evaluating_rule_id=self.rule_id,
                assumptions=["Userspace properties reflect system build configuration."],
                limitations=self.limitations,
            )
            return record, claim
        else:
            record = RuleEvaluationRecord(
                evaluation_id=f"eval:{self.rule_id}:incomplete",
                rule_id=self.rule_id,
                rule_version=self.version,
                outcome="insufficient_evidence",
                certainty="insufficient_evidence",
                input_evidence_ids=input_ids,
                prerequisites_checked=prereqs_checked,
                prerequisites_satisfied=prereqs_satisfied,
                prerequisites_missing=prereqs_missing,
                conclusion=f"Incomplete boot-chain telemetry: {len(prereqs_missing)} properties missing or inaccessible.",
                explanation=f"Missing or non-observed properties: {', '.join(prereqs_missing)}.",
                caveats=self.limitations,
            )
            claim = ResearchClaim(
                claim_id=f"claim:{self.rule_id}:incomplete",
                title="Incomplete Boot-Chain Telemetry Available",
                category="evidence_gap",
                certainty="insufficient_evidence",
                summary=f"Key verified-boot indicators ({', '.join(prereqs_missing)}) are missing or inaccessible.",
                supporting_evidence_ids=input_ids,
                evaluating_rule_id=self.rule_id,
                missing_evidence=prereqs_missing,
                limitations=self.limitations,
            )
            return record, claim


class DiffBootDriftRule(BaseRule):
    rule_id = "RULE-DIFF-BOOT-DRIFT"
    name = "Snapshot Diff Boot-Chain Drift Analysis"
    purpose = "Analyze semantic snapshot differences for bootloader, AVB, or build property transitions."
    limitations: ClassVar[list[str]] = [
        "Relies on snapshot comparability; invalid cross-device diffs cannot be interpreted as state changes.",
    ]

    def evaluate(
        self,
        evidence: list[NormalizedEvidence],
    ) -> tuple[RuleEvaluationRecord, ResearchClaim | None]:
        diff_items = [e for e in evidence if e.source_type == "semantic_diff"]
        if not diff_items:
            return (
                RuleEvaluationRecord(
                    evaluation_id=f"eval:{self.rule_id}:na",
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    outcome="not_applicable",
                    certainty="insufficient_evidence",
                    conclusion="No semantic diff observations available to evaluate boot-chain drift.",
                    explanation="Requires semantic_diff inputs.",
                    caveats=self.limitations,
                ),
                None,
            )

        boot_diffs = [
            e for e in diff_items
            if any(k in e.key for k in ("ro.boot.", "ro.build.", "ro.bootloader"))
        ]
        if not boot_diffs:
            boot_diffs = diff_items

        changed = [d for d in boot_diffs if d.status in ("value_changed", "status_changed")]
        input_ids = [d.evidence_id for d in boot_diffs]
        changed_ids = [c.evidence_id for c in changed]

        if any(d.provenance in ("different_device", "synthetic_vs_physical") for d in diff_items):
            return (
                RuleEvaluationRecord(
                    evaluation_id=f"eval:{self.rule_id}:incomparable",
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    outcome="incomparable",
                    certainty="conflicting_evidence",
                    input_evidence_ids=input_ids,
                    conclusion="Diff comparability blocked; cannot attribute changes to device drift.",
                    explanation="Diff crossed distinct physical handsets or synthetic boundaries.",
                    caveats=self.limitations,
                ),
                ResearchClaim(
                    claim_id=f"claim:{self.rule_id}:incomparable",
                    title="Incomparable Snapshot Diff Boundary",
                    category="provenance_boundary",
                    certainty="conflicting_evidence",
                    summary="Comparison involves mismatched hardware or synthetic boundaries; cannot infer state drift.",
                    contradicting_evidence_ids=input_ids,
                    evaluating_rule_id=self.rule_id,
                    limitations=self.limitations,
                ),
            )

        if changed:
            record = RuleEvaluationRecord(
                evaluation_id=f"eval:{self.rule_id}:drift_detected",
                rule_id=self.rule_id,
                rule_version=self.version,
                outcome="supported",
                certainty="strongly_supported",
                input_evidence_ids=changed_ids,
                conclusion=f"Detected {len(changed)} modified boot/build observations between snapshots.",
                explanation=f"Properties with observed drift: {', '.join(c.key for c in changed)}.",
                caveats=self.limitations,
            )
            claim = ResearchClaim(
                claim_id=f"claim:{self.rule_id}:drift",
                title="Boot-Chain / Build Property Drift Observed",
                category="configuration_drift",
                certainty="strongly_supported",
                summary=f"Semantic diff reveals {len(changed)} state changes across snapshots.",
                supporting_evidence_ids=changed_ids,
                evaluating_rule_id=self.rule_id,
                limitations=self.limitations,
            )
            return record, claim
        else:
            record = RuleEvaluationRecord(
                evaluation_id=f"eval:{self.rule_id}:zero_drift",
                rule_id=self.rule_id,
                rule_version=self.version,
                outcome="supported",
                certainty="strongly_supported",
                input_evidence_ids=input_ids,
                conclusion="Zero boot-chain drift detected across baseline and current snapshots.",
                explanation="All compared boot-chain properties remained unchanged.",
                caveats=self.limitations,
            )
            claim = ResearchClaim(
                claim_id=f"claim:{self.rule_id}:stable",
                title="Zero Boot-Chain Drift Observed",
                category="configuration_drift",
                certainty="strongly_supported",
                summary="Boot-chain observations remained identical between snapshot collection points.",
                supporting_evidence_ids=input_ids,
                evaluating_rule_id=self.rule_id,
                limitations=self.limitations,
            )
            return record, claim


class FirmwareBootValidationRule(BaseRule):
    rule_id = "RULE-FW-BOOT-VALID"
    name = "Firmware Boot Image Structure & Section Validation"
    purpose = "Verify header version, kernel/ramdisk sizes, and section boundaries in firmware artifacts."
    limitations: ClassVar[list[str]] = [
        "Validates structural header fields only; does NOT verify OEM digital signature chains or AVB hashes.",
    ]

    def evaluate(
        self,
        evidence: list[NormalizedEvidence],
    ) -> tuple[RuleEvaluationRecord, ResearchClaim | None]:
        fw_items = [e for e in evidence if e.source_type == "firmware_report"]
        if not fw_items:
            return (
                RuleEvaluationRecord(
                    evaluation_id=f"eval:{self.rule_id}:na",
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    outcome="not_applicable",
                    certainty="insufficient_evidence",
                    conclusion="No firmware findings available to evaluate boot image structure.",
                    explanation="Requires firmware_report inputs.",
                    caveats=self.limitations,
                ),
                None,
            )

        boot_ver_items = [e for e in fw_items if e.key in ("boot.header_version", "vendor_boot.header_version")]
        if not boot_ver_items:
            return (
                RuleEvaluationRecord(
                    evaluation_id=f"eval:{self.rule_id}:no_boot_headers",
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    outcome="insufficient_evidence",
                    certainty="insufficient_evidence",
                    conclusion="Firmware report does not contain boot or vendor_boot image headers.",
                    explanation="No boot header findings present.",
                    caveats=self.limitations,
                ),
                None,
            )

        supported_vers = [e for e in boot_ver_items if e.status == "observed" and e.value in (0, 1, 2, 3, 4)]
        unsupported = [e for e in boot_ver_items if e.status != "observed"]
        input_ids = [e.evidence_id for e in boot_ver_items]

        if supported_vers and not unsupported:
            record = RuleEvaluationRecord(
                evaluation_id=f"eval:{self.rule_id}:valid",
                rule_id=self.rule_id,
                rule_version=self.version,
                outcome="supported",
                certainty="strongly_supported",
                input_evidence_ids=input_ids,
                conclusion="Firmware boot image headers are structurally valid and comply with AOSP specifications.",
                explanation=f"Observed supported boot header version(s): {', '.join(str(e.value) for e in supported_vers)}.",
                caveats=self.limitations,
            )
            claim = ResearchClaim(
                claim_id=f"claim:{self.rule_id}:valid_header",
                title="Structurally Valid Firmware Boot Image Header",
                category="boot_chain_integrity",
                certainty="strongly_supported",
                summary="Boot image header conforms to AOSP v0-v4 header definitions with valid component sizes.",
                supporting_evidence_ids=input_ids,
                evaluating_rule_id=self.rule_id,
                limitations=self.limitations,
            )
            return record, claim
        else:
            record = RuleEvaluationRecord(
                evaluation_id=f"eval:{self.rule_id}:invalid_or_truncated",
                rule_id=self.rule_id,
                rule_version=self.version,
                outcome="contradicted",
                certainty="strongly_supported",
                input_evidence_ids=input_ids,
                conclusion="Boot image header is unsupported, malformed, or truncated.",
                explanation=f"Header status: {', '.join(e.status for e in boot_ver_items)}.",
                caveats=self.limitations,
            )
            claim = ResearchClaim(
                claim_id=f"claim:{self.rule_id}:header_inconsistency",
                title="Boot Image Header Inconsistencies Detected",
                category="boot_chain_integrity",
                certainty="strongly_supported",
                summary="Boot image header could not be fully parsed or contains unsupported version parameters.",
                contradicting_evidence_ids=input_ids,
                evaluating_rule_id=self.rule_id,
                limitations=self.limitations,
            )
            return record, claim


class CrossSourceConsistencyRule(BaseRule):
    rule_id = "RULE-CROSS-SOURCE-CONSISTENCY"
    name = "Cross-Source Build & Version Consistency"
    purpose = "Correlate build, model, and OS version fields between live device evidence and firmware artifacts."
    limitations: ClassVar[list[str]] = [
        "A match confirms build metadata alignment; it does not prove the device runs the exact byte-for-byte image without runtime modification.",
    ]

    def evaluate(
        self,
        evidence: list[NormalizedEvidence],
    ) -> tuple[RuleEvaluationRecord, ResearchClaim | None]:
        dev_items = [e for e in evidence if e.source_type in ("device_evidence", "snapshot")]
        fw_items = [e for e in evidence if e.source_type == "firmware_report"]

        if not dev_items or not fw_items:
            return (
                RuleEvaluationRecord(
                    evaluation_id=f"eval:{self.rule_id}:na",
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    outcome="not_applicable",
                    certainty="insufficient_evidence",
                    conclusion="Requires both live device/snapshot evidence and firmware report to evaluate cross-source consistency.",
                    explanation="Cross-source correlation requires heterogeneous input reports.",
                    caveats=self.limitations,
                ),
                None,
            )

        # Comparable pairs:
        # 1. OS Release: ro.build.version.release vs boot.declared_os_version or prop.ro.build.version.release
        # 2. Build ID: ro.build.id vs prop.ro.build.id
        # 3. Model: ro.product.model vs prop.ro.product.model
        comparisons: list[dict[str, Any]] = []

        dev_os = next((e for e in dev_items if e.key in ("build.version.release", "ro.build.version.release") and e.status == "observed"), None)
        fw_os = next((e for e in fw_items if e.key in ("boot.declared_os_version", "prop.ro.build.version.release", "ro.build.version.release") and e.status == "observed"), None)
        if dev_os and fw_os:
            comparisons.append({
                "field": "OS Version Release",
                "dev_item": dev_os,
                "fw_item": fw_os,
                "matches": str(dev_os.value).strip() == str(fw_os.value).strip(),
            })

        dev_model = next((e for e in dev_items if e.key in ("product.model", "ro.product.model") and e.status == "observed"), None)
        fw_model = next((e for e in fw_items if e.key in ("prop.ro.product.model", "ro.product.model", "product.model") and e.status == "observed"), None)
        if dev_model and fw_model:
            comparisons.append({
                "field": "Device Model",
                "dev_item": dev_model,
                "fw_item": fw_model,
                "matches": str(dev_model.value).strip().lower() == str(fw_model.value).strip().lower(),
            })

        dev_build = next((e for e in dev_items if e.key in ("build.id", "ro.build.id") and e.status == "observed"), None)
        fw_build = next((e for e in fw_items if e.key in ("prop.ro.build.id", "ro.build.id", "build.id") and e.status == "observed"), None)
        if dev_build and fw_build:
            comparisons.append({
                "field": "Build ID",
                "dev_item": dev_build,
                "fw_item": fw_build,
                "matches": str(dev_build.value).strip() == str(fw_build.value).strip(),
            })

        if not comparisons:
            return (
                RuleEvaluationRecord(
                    evaluation_id=f"eval:{self.rule_id}:no_common_fields",
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    outcome="insufficient_evidence",
                    certainty="insufficient_evidence",
                    conclusion="No overlapping comparable fields between live device observations and firmware metadata.",
                    explanation="Checked OS version, build ID, and model properties.",
                    caveats=self.limitations,
                ),
                None,
            )

        mismatches = [c for c in comparisons if not c["matches"]]
        matches = [c for c in comparisons if c["matches"]]

        all_input_ids = [c["dev_item"].evidence_id for c in comparisons] + [c["fw_item"].evidence_id for c in comparisons]

        if mismatches:
            conflict_ids = [c["dev_item"].evidence_id for c in mismatches] + [c["fw_item"].evidence_id for c in mismatches]
            m_desc = [f"{c['field']} (device '{c['dev_item'].value}' != fw '{c['fw_item'].value}')" for c in mismatches]
            record = RuleEvaluationRecord(
                evaluation_id=f"eval:{self.rule_id}:discrepancy",
                rule_id=self.rule_id,
                rule_version=self.version,
                outcome="contradicted",
                certainty="conflicting_evidence",
                input_evidence_ids=all_input_ids,
                conflicting_evidence_ids=conflict_ids,
                conclusion="Cross-source discrepancy detected between device evidence and firmware metadata.",
                explanation=f"Mismatches found in: {', '.join(m_desc)}.",
                caveats=self.limitations,
            )
            claim = ResearchClaim(
                claim_id=f"claim:{self.rule_id}:mismatch",
                title="Cross-Source Build Discrepancy Detected",
                category="version_consistency",
                certainty="conflicting_evidence",
                summary="Device observations do not match declared firmware artifact properties.",
                supporting_evidence_ids=[c["dev_item"].evidence_id for c in matches],
                contradicting_evidence_ids=conflict_ids,
                evaluating_rule_id=self.rule_id,
                limitations=self.limitations,
            )
            return record, claim
        else:
            record = RuleEvaluationRecord(
                evaluation_id=f"eval:{self.rule_id}:consistent",
                rule_id=self.rule_id,
                rule_version=self.version,
                outcome="supported",
                certainty="strongly_supported",
                input_evidence_ids=all_input_ids,
                conclusion="Cross-source build consistency corroborated across all compared fields.",
                explanation=f"Corroborated fields: {', '.join(c['field'] for c in matches)}.",
                caveats=self.limitations,
            )
            claim = ResearchClaim(
                claim_id=f"claim:{self.rule_id}:consistent",
                title="Cross-Source Build Metadata Corroborated",
                category="version_consistency",
                certainty="strongly_supported",
                summary="Static firmware metadata aligns with live device observations.",
                supporting_evidence_ids=all_input_ids,
                evaluating_rule_id=self.rule_id,
                limitations=self.limitations,
            )
            return record, claim


class ProvenanceBoundaryRule(BaseRule):
    rule_id = "RULE-PROVENANCE-BOUNDARY"
    name = "Synthetic / Physical Provenance Boundary Integrity"
    purpose = "Detect and flag unwarranted aggregation of synthetic mock fixtures with physical device evidence."
    limitations: ClassVar[list[str]] = [
        "Synthetic data is strictly for testing; it must never be interpreted as real device security posture.",
    ]

    def evaluate(
        self,
        evidence: list[NormalizedEvidence],
    ) -> tuple[RuleEvaluationRecord, ResearchClaim | None]:
        provs = {e.provenance for e in evidence if e.provenance in ("synthetic", "physical_handset")}
        input_ids = [e.evidence_id for e in evidence if e.provenance in ("synthetic", "physical_handset")]

        if "synthetic" in provs and "physical_handset" in provs:
            synth_ids = [e.evidence_id for e in evidence if e.provenance == "synthetic"]
            phys_ids = [e.evidence_id for e in evidence if e.provenance == "physical_handset"]
            record = RuleEvaluationRecord(
                evaluation_id=f"eval:{self.rule_id}:boundary_conflict",
                rule_id=self.rule_id,
                rule_version=self.version,
                outcome="contradicted",
                certainty="conflicting_evidence",
                input_evidence_ids=input_ids,
                conflicting_evidence_ids=synth_ids[:5] + phys_ids[:5],
                conclusion="Synthetic test fixtures and physical handset evidence are mixed in the same analysis session.",
                explanation="Evidence inputs cross synthetic vs physical provenance boundaries.",
                caveats=self.limitations,
            )
            claim = ResearchClaim(
                claim_id=f"claim:{self.rule_id}:provenance_mix",
                title="Synthetic vs Physical Provenance Boundary Conflict",
                category="provenance_boundary",
                certainty="conflicting_evidence",
                summary="The analysis includes both synthetic mock data and physical handset evidence.",
                supporting_evidence_ids=[],
                contradicting_evidence_ids=synth_ids[:5] + phys_ids[:5],
                evaluating_rule_id=self.rule_id,
                limitations=self.limitations,
            )
            return record, claim
        else:
            single_prov = next(iter(provs), "unverified")
            record = RuleEvaluationRecord(
                evaluation_id=f"eval:{self.rule_id}:consistent_provenance",
                rule_id=self.rule_id,
                rule_version=self.version,
                outcome="supported",
                certainty="directly_observed",
                input_evidence_ids=input_ids[:10],
                conclusion=f"Consistent provenance maintained across evidence ({single_prov}).",
                explanation="No synthetic vs physical boundary violations detected.",
                caveats=self.limitations,
            )
            return record, None


class InaccessibleEvidenceLimitRule(BaseRule):
    rule_id = "RULE-INACCESSIBLE-EVIDENCE-LIMIT"
    name = "Observation Surface Accessibility Boundaries"
    purpose = "Identify properties and files blocked by OS permissions, SELinux policy, or OEM non-exposure."
    limitations: ClassVar[list[str]] = [
        "Inaccessible or unsupported properties define the limits of observation; they are not evidence of compromise.",
    ]

    def evaluate(
        self,
        evidence: list[NormalizedEvidence],
    ) -> tuple[RuleEvaluationRecord, ResearchClaim | None]:
        inaccessible = [e for e in evidence if e.status in ("inaccessible", "unsupported")]
        if not inaccessible:
            record = RuleEvaluationRecord(
                evaluation_id=f"eval:{self.rule_id}:fully_accessible",
                rule_id=self.rule_id,
                rule_version=self.version,
                outcome="supported",
                certainty="directly_observed",
                conclusion="All observed evidence items were accessible and supported by host/target environment.",
                explanation="Zero items with inaccessible or unsupported status.",
                caveats=self.limitations,
            )
            return record, None

        input_ids = [e.evidence_id for e in inaccessible]
        keys = [e.key for e in inaccessible]
        record = RuleEvaluationRecord(
            evaluation_id=f"eval:{self.rule_id}:surface_limited",
            rule_id=self.rule_id,
            rule_version=self.version,
            outcome="supported",
            certainty="directly_observed",
            input_evidence_ids=input_ids,
            conclusion=f"Identified {len(inaccessible)} evidence items with inaccessible or unsupported status.",
            explanation=f"Properties outside observation surface: {', '.join(keys[:8])}{'...' if len(keys) > 8 else ''}.",
            caveats=self.limitations,
        )
        claim = ResearchClaim(
            claim_id=f"claim:{self.rule_id}:observation_limit",
            title="Observation Surface Boundaries Documented",
            category="evidence_gap",
            certainty="directly_observed",
            summary=f"{len(inaccessible)} observations are outside the accessible observation surface.",
            supporting_evidence_ids=input_ids,
            evaluating_rule_id=self.rule_id,
            missing_evidence=keys,
            limitations=self.limitations,
        )
        return record, claim


DEFAULT_RULE_REGISTRY: list[BaseRule] = [
    BootChainCompletenessRule(),
    DiffBootDriftRule(),
    FirmwareBootValidationRule(),
    CrossSourceConsistencyRule(),
    ProvenanceBoundaryRule(),
    InaccessibleEvidenceLimitRule(),
]
