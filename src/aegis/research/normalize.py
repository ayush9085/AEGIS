"""Normalization of Phase 1, Phase 2, and Phase 3 evidence into standard research items."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from aegis.research.models import (
    NormalizedEvidence,
    ResearchCompatibilityError,
    ResearchValidationError,
)


def compute_file_sha256(path: Path) -> str:
    """Compute streaming SHA-256 hash of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def detect_source_type(data: dict[str, Any]) -> str:
    """Identify the AEGIS report type from dictionary keys."""
    if "snapshot_format_version" in data and "content_hash" in data:
        return "snapshot"
    if ("diff_version" in data or "diff_schema_version" in data) and (
        "comparability_state" in data or "device_comparability" in data
    ):
        return "semantic_diff"
    if "schema_version" in data and "artifacts" in data and "findings" in data:
        return "firmware_report"
    if "schema_version" in data and "device" in data and "observations" in data:
        return "device_evidence"
    raise ResearchCompatibilityError("Unrecognized AEGIS evidence format or missing required schema markers")


def normalize_source_data(
    data: dict[str, Any],
    source_ref: str,
    file_hash: str | None = None,
) -> tuple[dict[str, Any], list[NormalizedEvidence]]:
    """Normalize any supported AEGIS report dictionary into standardized NormalizedEvidence items.

    Returns: (source_input_metadata, list_of_normalized_evidence)
    """
    if not isinstance(data, dict):
        raise ResearchValidationError(f"Expected JSON object for source '{source_ref}', got {type(data).__name__}")

    source_type = detect_source_type(data)

    if source_type == "device_evidence":
        return _normalize_device_evidence(data, source_ref, file_hash)
    elif source_type == "snapshot":
        return _normalize_snapshot(data, source_ref, file_hash)
    elif source_type == "semantic_diff":
        return _normalize_semantic_diff(data, source_ref, file_hash)
    elif source_type == "firmware_report":
        return _normalize_firmware_report(data, source_ref, file_hash)
    else:
        raise ResearchCompatibilityError(f"Unsupported source type '{source_type}' for research correlation")


def _normalize_device_evidence(
    data: dict[str, Any],
    source_ref: str,
    file_hash: str | None,
) -> tuple[dict[str, Any], list[NormalizedEvidence]]:
    schema_version = str(data.get("schema_version", "0.1.0"))
    device = data.get("device", {})
    collection = data.get("collection", {})
    is_synth = bool(collection.get("is_synthetic", False) or device.get("is_synthetic", False))
    prov = "synthetic" if is_synth else "physical_handset"
    dev_fp = {
        "manufacturer": device.get("manufacturer"),
        "model": device.get("model"),
        "product_name": device.get("product_name"),
        "android_version": device.get("android_version"),
        "security_patch": device.get("security_patch"),
        "build_id": device.get("build_id"),
        "is_synthetic": is_synth,
    }

    ref_id = file_hash[:8] if file_hash else Path(source_ref).stem

    meta = {
        "source_ref": source_ref,
        "source_type": "device_evidence",
        "schema_version": schema_version,
        "content_hash": file_hash,
        "device_fingerprint": dev_fp,
        "provenance": prov,
    }

    items: list[NormalizedEvidence] = []
    for obs in data.get("observations", []):
        key = str(obs.get("key", ""))
        if not key:
            continue
        items.append(
            NormalizedEvidence(
                evidence_id=f"ev:dev:{ref_id}:{key}",
                source_type="device_evidence",
                source_ref=source_ref,
                source_schema_version=schema_version,
                source_content_hash=file_hash,
                category=str(obs.get("collector", "device_property")),
                key=key,
                label=str(obs.get("label", key)),
                status=str(obs.get("status", "unknown")),
                value=obs.get("value"),
                raw_value=obs.get("raw_value"),
                provenance=prov,
                device_fingerprint=dev_fp,
                collector_or_parser=str(obs.get("collector", "")),
                collected_at_utc=obs.get("collected_at"),
                redacted=bool(obs.get("redacted", False)),
            )
        )

    return meta, items


def _normalize_snapshot(
    data: dict[str, Any],
    source_ref: str,
    file_hash: str | None,
) -> tuple[dict[str, Any], list[NormalizedEvidence]]:
    schema_version = str(data.get("snapshot_format_version", data.get("source_schema_version", "0.1.0")))
    content_hash = str(data.get("content_hash", ""))
    device = data.get("device", {})
    prov_dict = data.get("provenance", {})
    is_synth = bool(prov_dict.get("is_synthetic", False) or device.get("is_synthetic", False))
    prov = "synthetic" if is_synth else "physical_handset"
    dev_fp = {
        "manufacturer": device.get("manufacturer"),
        "model": device.get("model"),
        "product_name": device.get("product_name"),
        "android_version": device.get("android_version"),
        "security_patch": device.get("security_patch"),
        "build_id": device.get("build_id"),
        "is_synthetic": is_synth,
    }

    ref_id = content_hash[:8] if content_hash else (file_hash[:8] if file_hash else Path(source_ref).stem)

    meta = {
        "source_ref": source_ref,
        "source_type": "snapshot",
        "schema_version": schema_version,
        "content_hash": content_hash or file_hash,
        "device_fingerprint": dev_fp,
        "provenance": prov,
    }

    items: list[NormalizedEvidence] = []
    for obs in data.get("observations", []):
        key = str(obs.get("key", ""))
        if not key:
            continue
        items.append(
            NormalizedEvidence(
                evidence_id=f"ev:snap:{ref_id}:{key}",
                source_type="snapshot",
                source_ref=source_ref,
                source_schema_version=schema_version,
                source_content_hash=content_hash,
                category=str(obs.get("collector", "device_property")),
                key=key,
                label=str(obs.get("label", key)),
                status=str(obs.get("status", "unknown")),
                value=obs.get("value"),
                raw_value=obs.get("raw_value"),
                provenance=prov,
                device_fingerprint=dev_fp,
                collector_or_parser=str(obs.get("collector", "")),
                collected_at_utc=obs.get("collected_at"),
                redacted=bool(obs.get("redacted", False)),
            )
        )

    return meta, items


def _normalize_semantic_diff(
    data: dict[str, Any],
    source_ref: str,
    file_hash: str | None,
) -> tuple[dict[str, Any], list[NormalizedEvidence]]:
    schema_version = str(data.get("diff_version", data.get("diff_schema_version", "0.1.0")))
    b_hash = str(data.get("baseline_hash", data.get("baseline_snapshot_hash", "")))[:8]
    c_hash = str(data.get("current_hash", data.get("current_snapshot_hash", "")))[:8]
    comparability = str(data.get("comparability_state", data.get("device_comparability", "unknown")))

    ref_id = f"{b_hash}_{c_hash}" if b_hash and c_hash else Path(source_ref).stem

    meta = {
        "source_ref": source_ref,
        "source_type": "semantic_diff",
        "schema_version": schema_version,
        "content_hash": file_hash,
        "device_comparability": comparability,
        "baseline_snapshot_hash": data.get("baseline_hash", data.get("baseline_snapshot_hash")),
        "current_snapshot_hash": data.get("current_hash", data.get("current_snapshot_hash")),
    }

    items: list[NormalizedEvidence] = []
    change_list = data.get("changes", data.get("observations", []))
    for obs in change_list:
        key = str(obs.get("key", ""))
        if not key:
            continue
        classification = str(obs.get("classification", "unknown"))
        old_val = obs.get("old_value", obs.get("baseline_value"))
        new_val = obs.get("new_value", obs.get("current_value"))
        old_st = obs.get("old_status", obs.get("baseline_status"))
        new_st = obs.get("new_status", obs.get("current_status"))

        items.append(
            NormalizedEvidence(
                evidence_id=f"ev:diff:{ref_id}:{key}",
                source_type="semantic_diff",
                source_ref=source_ref,
                source_schema_version=schema_version,
                source_content_hash=file_hash,
                category="diff_observation",
                key=key,
                label=str(obs.get("label", key)),
                status=classification,
                value={
                    "baseline_value": old_val,
                    "current_value": new_val,
                    "baseline_status": old_st,
                    "current_status": new_st,
                },
                provenance=comparability,
                caveats=[f"Semantic diff classification: {classification}"],
            )
        )

    return meta, items


def _normalize_firmware_report(
    data: dict[str, Any],
    source_ref: str,
    file_hash: str | None,
) -> tuple[dict[str, Any], list[NormalizedEvidence]]:
    schema_version = str(data.get("schema_version", "0.1.0"))
    target_name = str(data.get("target_name", ""))
    target_type = str(data.get("target_type", ""))
    ref_id = file_hash[:8] if file_hash else Path(source_ref).stem

    meta = {
        "source_ref": source_ref,
        "source_type": "firmware_report",
        "schema_version": schema_version,
        "content_hash": file_hash,
        "target_name": target_name,
        "target_type": target_type,
        "provenance": "firmware_artifact",
    }

    items: list[NormalizedEvidence] = []

    # Findings
    for f in data.get("findings", []):
        key = str(f.get("key", ""))
        fid = str(f.get("finding_id", key))
        safe_fid = "".join(c if c.isalnum() or c in "._-" else "_" for c in fid)
        caveats = [f["caveat"]] if f.get("caveat") else []
        items.append(
            NormalizedEvidence(
                evidence_id=f"ev:fw:{ref_id}:{safe_fid}",
                source_type="firmware_report",
                source_ref=str(f.get("evidence_source", source_ref)),
                source_schema_version=schema_version,
                source_content_hash=file_hash,
                category=str(f.get("category", "firmware_finding")),
                key=key,
                label=str(f.get("label", key)),
                status=str(f.get("status", "unknown")),
                value=f.get("value"),
                provenance="firmware_artifact",
                collector_or_parser=f"{f.get('parser', '')}:{f.get('parser_version', '')}",
                caveats=caveats,
            )
        )

    # Artifacts overview items
    for a in data.get("artifacts", []):
        rel_path = str(a.get("path", ""))
        fmt = str(a.get("detected_format", "unknown"))
        safe_path = "".join(c if c.isalnum() or c in "._-" else "_" for c in rel_path)
        items.append(
            NormalizedEvidence(
                evidence_id=f"ev:fw_art:{ref_id}:{safe_path}",
                source_type="firmware_report",
                source_ref=rel_path,
                source_schema_version=schema_version,
                source_content_hash=a.get("sha256"),
                category="firmware_artifact",
                key=f"artifact.{rel_path}",
                label=f"Artifact {rel_path} ({fmt})",
                status=str(a.get("parse_status", "unknown")),
                value={
                    "format": fmt,
                    "size_bytes": a.get("size_bytes"),
                    "sha256": a.get("sha256"),
                },
                provenance="firmware_artifact",
                collector_or_parser=str(a.get("parser_used", "")),
                caveats=list(a.get("warnings", [])),
            )
        )

    return meta, items


def load_and_normalize_path(path: Path) -> tuple[dict[str, Any], list[NormalizedEvidence]]:
    """Read a JSON file, compute its hash, and return normalized items."""
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchValidationError(f"Failed to read/parse JSON from '{path}': {exc}") from exc

    file_hash = compute_file_sha256(path)
    return normalize_source_data(data, str(path), file_hash=file_hash)
