"""Evidence snapshots, canonical hashing, and integrity verification."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aegis.schema import EvidenceReport, validate_evidence_dict

SNAPSHOT_FORMAT_VERSION = "0.1.0"
SUPPORTED_SNAPSHOT_VERSIONS = {SNAPSHOT_FORMAT_VERSION}


class SnapshotError(Exception):
    """Base exception for snapshot errors."""


class SnapshotIntegrityError(SnapshotError):
    """Raised when a snapshot's content hash does not match computed hash."""


class SnapshotFormatError(SnapshotError):
    """Raised when snapshot structure or version is invalid."""


@dataclass
class EvidenceSnapshot:
    """A versioned, canonical evidence snapshot with cryptographic content hash."""

    snapshot_format_version: str
    snapshot_id: str
    content_hash: str
    created_at_utc: str
    source_schema_version: str
    source_timestamp_utc: str
    provenance: dict[str, Any]
    device: dict[str, Any]
    observations: list[dict[str, Any]]
    summary: dict[str, int]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert snapshot to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize snapshot to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceSnapshot:
        """Construct EvidenceSnapshot from dictionary with validation."""
        validate_snapshot_dict(data)
        return cls(
            snapshot_format_version=data["snapshot_format_version"],
            snapshot_id=data["snapshot_id"],
            content_hash=data["content_hash"],
            created_at_utc=data["created_at_utc"],
            source_schema_version=data["source_schema_version"],
            source_timestamp_utc=data["source_timestamp_utc"],
            provenance=data["provenance"],
            device=data["device"],
            observations=data["observations"],
            summary=data["summary"],
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> EvidenceSnapshot:
        """Parse JSON string into an EvidenceSnapshot."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise SnapshotFormatError(f"Malformed snapshot JSON document: {exc}") from exc
        return cls.from_dict(data)


def build_canonical_payload(
    source_schema_version: str,
    is_synthetic: bool,
    device: dict[str, Any],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Construct canonical evidence structure for deterministic hashing.

    Excludes ephemeral metadata (timestamps, host runtime, paths) while
    retaining all security-relevant device identities and observations.
    """
    clean_device = {
        "serial_redacted": device.get("serial_redacted", ""),
        "manufacturer": device.get("manufacturer"),
        "model": device.get("model"),
        "product_name": device.get("product_name"),
        "android_version": device.get("android_version"),
        "sdk_version": device.get("sdk_version"),
        "build_id": device.get("build_id"),
        "fingerprint": device.get("fingerprint"),
    }

    clean_observations = []
    for obs in observations:
        clean_observations.append(
            {
                "key": obs["key"],
                "label": obs.get("label", obs["key"]),
                "status": obs["status"],
                "value": obs.get("value"),
                "raw_value": obs.get("raw_value"),
                "error": obs.get("error"),
                "redacted": bool(obs.get("redacted", False)),
            }
        )

    # Deterministic sorting by observation key
    clean_observations.sort(key=lambda o: o["key"])

    return {
        "source_schema_version": str(source_schema_version),
        "is_synthetic": bool(is_synthetic),
        "device": clean_device,
        "observations": clean_observations,
    }


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    """Serialize dictionary to canonical JSON bytes with strict deterministic rules.

    - Sorted keys (sort_keys=True)
    - Compact separators (',', ':')
    - Strict UTF-8 without ASCII escapes (ensure_ascii=False)
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_content_hash(payload: dict[str, Any]) -> str:
    """Calculate SHA-256 content hash of the canonical evidence payload."""
    raw_bytes = canonical_json_bytes(payload)
    return hashlib.sha256(raw_bytes).hexdigest()


def create_snapshot(
    evidence: EvidenceReport | dict[str, Any],
    notes: str | None = None,
    parent_snapshot_hash: str | None = None,
) -> EvidenceSnapshot:
    """Create a validated EvidenceSnapshot from an EvidenceReport or evidence dictionary."""
    if isinstance(evidence, EvidenceReport):
        ev_dict = evidence.to_dict()
    else:
        ev_dict = dict(evidence)
        validate_evidence_dict(ev_dict)

    source_schema_version = ev_dict["schema_version"]
    coll = ev_dict["collection"]
    dev = ev_dict["device"]
    obs_list = ev_dict["observations"]
    summary = ev_dict["summary"]

    is_synthetic = bool(coll.get("is_synthetic", False))
    canonical_payload = build_canonical_payload(
        source_schema_version=source_schema_version,
        is_synthetic=is_synthetic,
        device=dev,
        observations=obs_list,
    )
    content_hash = compute_content_hash(canonical_payload)
    snapshot_id = content_hash[:16]

    # Deterministically order snapshot observations by key
    sorted_obs = sorted(obs_list, key=lambda o: o["key"])

    now_utc = datetime.now(UTC).isoformat()
    meta: dict[str, Any] = {}
    if notes:
        meta["notes"] = notes
    if parent_snapshot_hash:
        meta["parent_snapshot_hash"] = parent_snapshot_hash

    return EvidenceSnapshot(
        snapshot_format_version=SNAPSHOT_FORMAT_VERSION,
        snapshot_id=snapshot_id,
        content_hash=content_hash,
        created_at_utc=now_utc,
        source_schema_version=source_schema_version,
        source_timestamp_utc=coll.get("timestamp_utc", now_utc),
        provenance={
            "is_synthetic": is_synthetic,
            "method": coll.get("method", "adb_read_only"),
            "scope": coll.get("scope", "phase_one_allowlist"),
        },
        device=dict(dev),
        observations=sorted_obs,
        summary=dict(summary),
        metadata=meta,
    )


def validate_snapshot_dict(data: dict[str, Any]) -> None:
    """Validate structure and fields of a snapshot dictionary."""
    if not isinstance(data, dict):
        raise SnapshotFormatError("Snapshot document must be a JSON object.")

    version = data.get("snapshot_format_version")
    if not version:
        raise SnapshotFormatError("Missing required field 'snapshot_format_version'.")
    if version not in SUPPORTED_SNAPSHOT_VERSIONS:
        raise SnapshotFormatError(
            f"Unsupported snapshot_format_version '{version}'. Supported: {sorted(SUPPORTED_SNAPSHOT_VERSIONS)}"
        )

    for req in (
        "snapshot_id",
        "content_hash",
        "created_at_utc",
        "source_schema_version",
        "source_timestamp_utc",
        "provenance",
        "device",
        "observations",
        "summary",
    ):
        if req not in data:
            raise SnapshotFormatError(f"Snapshot missing required field '{req}'.")

    if not isinstance(data["device"], dict):
        raise SnapshotFormatError("Field 'device' must be an object.")
    if not isinstance(data["observations"], list):
        raise SnapshotFormatError("Field 'observations' must be a list.")
    if not isinstance(data["summary"], dict):
        raise SnapshotFormatError("Field 'summary' must be an object.")


def save_snapshot(
    snapshot: EvidenceSnapshot,
    file_path: Path | str,
    overwrite: bool = False,
) -> Path:
    """Atomically write a snapshot to disk with overwrite protection."""
    dest = Path(file_path).resolve()
    if dest.exists() and not overwrite:
        raise FileExistsError(
            f"Snapshot destination '{dest}' already exists. Use overwrite option to replace."
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    temp_file = dest.with_name(f".{dest.name}.tmp.{os.getpid()}")
    try:
        temp_file.write_text(snapshot.to_json(indent=2), encoding="utf-8")
        temp_file.replace(dest)
    except Exception:
        if temp_file.exists():
            temp_file.unlink(missing_ok=True)
        raise

    return dest


def load_snapshot(
    file_path: Path | str,
    verify_integrity: bool = True,
) -> EvidenceSnapshot:
    """Load, parse, and optionally verify cryptographic integrity of a snapshot file."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Snapshot file not found: {path}")

    content = path.read_text(encoding="utf-8")
    snapshot = EvidenceSnapshot.from_json(content)

    if verify_integrity:
        canonical_payload = build_canonical_payload(
            source_schema_version=snapshot.source_schema_version,
            is_synthetic=snapshot.provenance.get("is_synthetic", False),
            device=snapshot.device,
            observations=snapshot.observations,
        )
        computed_hash = compute_content_hash(canonical_payload)
        if computed_hash != snapshot.content_hash:
            raise SnapshotIntegrityError(
                f"Snapshot integrity verification failed for '{path}'.\n"
                f"Recorded content hash: {snapshot.content_hash}\n"
                f"Recomputed hash:       {computed_hash}\n"
                f"The snapshot file may have been altered or corrupted."
            )

    return snapshot


# Convenience alias for snapshot creation from evidence
create_snapshot_from_evidence = create_snapshot
