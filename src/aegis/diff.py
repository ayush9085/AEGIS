"""Semantic comparison engine for AEGIS evidence snapshots."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from aegis.snapshots import EvidenceSnapshot

DIFF_FORMAT_VERSION = "0.1.0"


class DiffError(Exception):
    """Base exception for snapshot comparison errors."""


class IncomparableDeviceError(DiffError):
    """Raised when comparing snapshots from conflicting devices without explicit override."""


@dataclass
class ObservationDiff:
    """Semantic comparison record for an individual observation key."""

    key: str
    label: str
    classification: str  # unchanged, value_changed, status_changed, added, removed, incomparable
    old_status: str | None
    new_status: str | None
    old_value: Any
    new_value: Any
    old_raw_value: str | None
    new_raw_value: str | None
    explanation: str
    caveat: str = ""


@dataclass
class DiffSummary:
    """Reconciled statistical counts for snapshot comparison."""

    total_baseline: int
    total_current: int
    unchanged: int
    value_changed: int
    status_changed: int
    added: int
    removed: int
    incomparable: int


@dataclass
class SemanticDiff:
    """The complete structured semantic comparison between two snapshots."""

    diff_version: str
    baseline_id: str
    baseline_hash: str
    baseline_timestamp: str
    baseline_device: dict[str, Any]
    baseline_is_synthetic: bool
    current_id: str
    current_hash: str
    current_timestamp: str
    current_device: dict[str, Any]
    current_is_synthetic: bool
    comparability_state: str  # match, identity_unverified, mismatch_override
    is_cross_device_override: bool
    summary: DiffSummary
    changes: list[ObservationDiff]

    def to_dict(self) -> dict[str, Any]:
        """Convert diff result to a dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert diff result to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def check_device_comparability(
    baseline_dev: dict[str, Any],
    current_dev: dict[str, Any],
    baseline_synthetic: bool,
    current_synthetic: bool,
    allow_different_devices: bool = False,
) -> tuple[str, bool]:
    """Evaluate comparability of two snapshots based on sanitized device identities.

    Returns (comparability_state, is_cross_device_override).
    Raises IncomparableDeviceError if devices conflict and override is not enabled.
    """
    # 1. Provenance check (synthetic vs physical)
    provenance_mismatch = baseline_synthetic != current_synthetic

    UNKNOWN_TOKENS = {"", "unknown", "unavailable", "none", "null", "not available"}

    def _clean(val: Any) -> str:
        if val is None:
            return ""
        s = str(val).strip()
        return "" if s.lower() in UNKNOWN_TOKENS else s

    b_serial = _clean(baseline_dev.get("serial_redacted"))
    c_serial = _clean(current_dev.get("serial_redacted"))
    b_manuf = _clean(baseline_dev.get("manufacturer")).lower()
    c_manuf = _clean(current_dev.get("manufacturer")).lower()
    b_model = _clean(baseline_dev.get("model")).lower()
    c_model = _clean(current_dev.get("model")).lower()
    b_prod = _clean(baseline_dev.get("product_name")).lower()
    c_prod = _clean(current_dev.get("product_name")).lower()

    # Confirmed mismatch indicators: both sides have known values and they differ
    serial_mismatch = bool(b_serial and c_serial and b_serial != c_serial)
    manuf_mismatch = bool(b_manuf and c_manuf and b_manuf != c_manuf)
    model_mismatch = bool(b_model and c_model and b_model != c_model)
    prod_mismatch = bool(b_prod and c_prod and b_prod != c_prod)

    is_confirmed_mismatch = (
        provenance_mismatch
        or serial_mismatch
        or manuf_mismatch
        or model_mismatch
        or prod_mismatch
    )

    if is_confirmed_mismatch:
        if not allow_different_devices:
            reasons = []
            if provenance_mismatch:
                b_prov = "synthetic fixture" if baseline_synthetic else "physical handset"
                c_prov = "synthetic fixture" if current_synthetic else "physical handset"
                reasons.append(f"provenance mismatch ({b_prov} vs {c_prov})")
            if serial_mismatch:
                reasons.append(f"serial mismatch ('{b_serial}' vs '{c_serial}')")
            if manuf_mismatch or model_mismatch:
                reasons.append(
                    f"device mismatch ('{baseline_dev.get('manufacturer')} {baseline_dev.get('model')}' "
                    f"vs '{current_dev.get('manufacturer')} {current_dev.get('model')}')"
                )
            reason_str = ", ".join(reasons)
            raise IncomparableDeviceError(
                f"Cannot compare snapshots from different devices: {reason_str}.\n"
                f"AEGIS safeguards prevent comparing unrelated handsets by default.\n"
                f"To explicitly compare different devices for research, pass --allow-different-devices."
            )
        return "mismatch_override", True

    # Check if identity is missing / unverified
    # Missing identity must NOT be treated as a match
    has_sufficient_identity = bool(
        (b_serial and c_serial and b_serial == c_serial)
        and (b_model and c_model and b_model == c_model)
    )
    if not has_sufficient_identity:
        return "identity_unverified", False

    return "match", False


def compare_snapshots(
    baseline: EvidenceSnapshot,
    current: EvidenceSnapshot,
    allow_different_devices: bool = False,
) -> SemanticDiff:
    """Perform deterministic semantic diff between baseline and current snapshots."""
    b_synthetic = bool(baseline.provenance.get("is_synthetic", False))
    c_synthetic = bool(current.provenance.get("is_synthetic", False))

    comp_state, is_override = check_device_comparability(
        baseline_dev=baseline.device,
        current_dev=current.device,
        baseline_synthetic=b_synthetic,
        current_synthetic=c_synthetic,
        allow_different_devices=allow_different_devices,
    )

    # Index observations by canonical key
    b_map: dict[str, dict[str, Any]] = {o["key"]: o for o in baseline.observations}
    c_map: dict[str, dict[str, Any]] = {o["key"]: o for o in current.observations}

    all_keys = sorted(set(b_map.keys()) | set(c_map.keys()))

    diff_records: list[ObservationDiff] = []
    unchanged_cnt = 0
    val_changed_cnt = 0
    status_changed_cnt = 0
    added_cnt = 0
    removed_cnt = 0
    incomparable_cnt = 0

    for key in all_keys:
        in_b = key in b_map
        in_c = key in c_map

        if in_b and not in_c:
            old_obs = b_map[key]
            removed_cnt += 1
            diff_records.append(
                ObservationDiff(
                    key=key,
                    label=old_obs.get("label", key),
                    classification="removed",
                    old_status=old_obs.get("status"),
                    new_status=None,
                    old_value=old_obs.get("value"),
                    new_value=None,
                    old_raw_value=old_obs.get("raw_value"),
                    new_raw_value=None,
                    explanation=f"Observation '{key}' present in baseline but missing in current snapshot.",
                    caveat=old_obs.get("caveat", ""),
                )
            )
        elif in_c and not in_b:
            new_obs = c_map[key]
            added_cnt += 1
            diff_records.append(
                ObservationDiff(
                    key=key,
                    label=new_obs.get("label", key),
                    classification="added",
                    old_status=None,
                    new_status=new_obs.get("status"),
                    old_value=None,
                    new_value=new_obs.get("value"),
                    old_raw_value=None,
                    new_raw_value=new_obs.get("raw_value"),
                    explanation=f"Observation '{key}' added in current snapshot with status '{new_obs.get('status')}'.",
                    caveat=new_obs.get("caveat", ""),
                )
            )
        else:
            old_obs = b_map[key]
            new_obs = c_map[key]
            old_status = old_obs.get("status")
            new_status = new_obs.get("status")
            old_val = old_obs.get("value")
            new_val = new_obs.get("value")
            label = new_obs.get("label") or old_obs.get("label", key)
            caveat = new_obs.get("caveat") or old_obs.get("caveat", "")

            # 1. Status transition check
            if old_status != new_status:
                status_changed_cnt += 1
                diff_records.append(
                    ObservationDiff(
                        key=key,
                        label=label,
                        classification="status_changed",
                        old_status=old_status,
                        new_status=new_status,
                        old_value=old_val,
                        new_value=new_val,
                        old_raw_value=old_obs.get("raw_value"),
                        new_raw_value=new_obs.get("raw_value"),
                        explanation=(
                            f"Observation status transitioned from '{old_status}' to '{new_status}' "
                            f"(value: '{old_val}' -> '{new_val}')."
                        ),
                        caveat=caveat,
                    )
                )
            # 2. Value comparison check
            elif old_val != new_val:
                val_changed_cnt += 1
                diff_records.append(
                    ObservationDiff(
                        key=key,
                        label=label,
                        classification="value_changed",
                        old_status=old_status,
                        new_status=new_status,
                        old_value=old_val,
                        new_value=new_val,
                        old_raw_value=old_obs.get("raw_value"),
                        new_raw_value=new_obs.get("raw_value"),
                        explanation=f"Value changed from '{old_val}' to '{new_val}'.",
                        caveat=caveat,
                    )
                )
            # 3. Unchanged
            else:
                unchanged_cnt += 1
                diff_records.append(
                    ObservationDiff(
                        key=key,
                        label=label,
                        classification="unchanged",
                        old_status=old_status,
                        new_status=new_status,
                        old_value=old_val,
                        new_value=new_val,
                        old_raw_value=old_obs.get("raw_value"),
                        new_raw_value=new_obs.get("raw_value"),
                        explanation="Status and value are identical across snapshots.",
                        caveat=caveat,
                    )
                )

    summary = DiffSummary(
        total_baseline=len(b_map),
        total_current=len(c_map),
        unchanged=unchanged_cnt,
        value_changed=val_changed_cnt,
        status_changed=status_changed_cnt,
        added=added_cnt,
        removed=removed_cnt,
        incomparable=incomparable_cnt,
    )

    return SemanticDiff(
        diff_version=DIFF_FORMAT_VERSION,
        baseline_id=baseline.snapshot_id,
        baseline_hash=baseline.content_hash,
        baseline_timestamp=baseline.source_timestamp_utc,
        baseline_device=dict(baseline.device),
        baseline_is_synthetic=b_synthetic,
        current_id=current.snapshot_id,
        current_hash=current.content_hash,
        current_timestamp=current.source_timestamp_utc,
        current_device=dict(current.device),
        current_is_synthetic=c_synthetic,
        comparability_state=comp_state,
        is_cross_device_override=is_override,
        summary=summary,
        changes=diff_records,
    )
