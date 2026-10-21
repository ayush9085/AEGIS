"""Versioned evidence schema, status vocabulary, and validation logic."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

CURRENT_SCHEMA_VERSION = "0.1.0"
SUPPORTED_SCHEMA_VERSIONS = {"0.1.0"}

# Controlled status vocabulary
VALID_STATUSES = {
    "observed",
    "unsupported",
    "inaccessible",
    "not_applicable",
    "unknown",
    "error",
}

DEFAULT_LIMITATIONS = [
    "Unprivileged ADB read-only inspection cannot verify hardware root of trust or hardware-enforced rollback counters.",
    "System properties reported by getprop are provided by the running Android userspace and may be spoofed on modified systems.",
    "No proprietary bootloader stages, TrustZone/TEE code, or modem firmware were dumped, decompiled, or executed.",
    "Absence of an observable property is NOT proof that the underlying hardware or security subsystem is missing or disabled.",
    "This tool does NOT provide a binary 'safe' or 'compromised' certification.",
]

DEFAULT_NON_GOALS = [
    "Not a one-click root, bootloader unlocker, or exploit tool.",
    "Not an automated malware scanner or anti-virus engine.",
    "Not a full firmware extractor or partition dumping framework.",
    "Not an attestation authority.",
]


@dataclass
class Observation:
    """An individual recorded evidence item."""

    key: str
    label: str
    status: str
    value: Any = None
    raw_value: str | None = None
    source_command: list[str] = field(default_factory=list)
    collected_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    error: str | None = None
    caveat: str = ""
    redacted: bool = False

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{self.status}'. Must be one of {sorted(VALID_STATUSES)}"
            )


@dataclass
class DeviceContext:
    """Non-sensitive device identification and operating context."""

    serial_redacted: str
    state: str
    manufacturer: str | None = None
    model: str | None = None
    product_name: str | None = None
    android_version: str | None = None
    sdk_version: str | None = None
    security_patch: str | None = None
    build_id: str | None = None
    fingerprint: str | None = None


@dataclass
class CollectionMetadata:
    """Context and consent metadata regarding the collection session."""

    timestamp_utc: str
    method: str
    scope: str
    consent_given: bool
    host_os: str
    host_python: str
    host_adb_version: str | None = None


@dataclass
class SummaryCounts:
    """Summary counts of observations grouped by status."""

    total: int
    observed: int
    unsupported: int
    inaccessible: int
    not_applicable: int
    unknown: int
    error: int

    @classmethod
    def from_observations(cls, observations: list[Observation]) -> SummaryCounts:
        counts = {s: 0 for s in VALID_STATUSES}
        for obs in observations:
            counts[obs.status] = counts.get(obs.status, 0) + 1
        return cls(
            total=len(observations),
            observed=counts["observed"],
            unsupported=counts["unsupported"],
            inaccessible=counts["inaccessible"],
            not_applicable=counts["not_applicable"],
            unknown=counts["unknown"],
            error=counts["error"],
        )


@dataclass
class EvidenceReport:
    """The complete versioned evidence document."""

    schema_version: str
    tool: dict[str, str]
    collection: CollectionMetadata
    device: DeviceContext
    observations: list[Observation]
    summary: SummaryCounts
    limitations: list[str] = field(default_factory=lambda: list(DEFAULT_LIMITATIONS))
    non_goals: list[str] = field(default_factory=lambda: list(DEFAULT_NON_GOALS))

    def to_dict(self) -> dict[str, Any]:
        """Convert the report to a JSON-serializable dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert the report to a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceReport:
        """Validate and construct an EvidenceReport from a dictionary."""
        validate_evidence_dict(data)

        tool = data["tool"]
        coll_data = data["collection"]
        dev_data = data["device"]
        obs_data = data["observations"]
        sum_data = data["summary"]

        collection = CollectionMetadata(
            timestamp_utc=coll_data["timestamp_utc"],
            method=coll_data["method"],
            scope=coll_data["scope"],
            consent_given=coll_data["consent_given"],
            host_os=coll_data["host_os"],
            host_python=coll_data["host_python"],
            host_adb_version=coll_data.get("host_adb_version"),
        )
        device = DeviceContext(
            serial_redacted=dev_data["serial_redacted"],
            state=dev_data["state"],
            manufacturer=dev_data.get("manufacturer"),
            model=dev_data.get("model"),
            product_name=dev_data.get("product_name"),
            android_version=dev_data.get("android_version"),
            sdk_version=dev_data.get("sdk_version"),
            security_patch=dev_data.get("security_patch"),
            build_id=dev_data.get("build_id"),
            fingerprint=dev_data.get("fingerprint"),
        )
        observations = [
            Observation(
                key=o["key"],
                label=o["label"],
                status=o["status"],
                value=o.get("value"),
                raw_value=o.get("raw_value"),
                source_command=o.get("source_command", []),
                collected_at=o.get("collected_at", ""),
                error=o.get("error"),
                caveat=o.get("caveat", ""),
                redacted=o.get("redacted", False),
            )
            for o in obs_data
        ]
        summary = SummaryCounts(
            total=sum_data["total"],
            observed=sum_data["observed"],
            unsupported=sum_data["unsupported"],
            inaccessible=sum_data["inaccessible"],
            not_applicable=sum_data["not_applicable"],
            unknown=sum_data["unknown"],
            error=sum_data["error"],
        )
        return cls(
            schema_version=data["schema_version"],
            tool=tool,
            collection=collection,
            device=device,
            observations=observations,
            summary=summary,
            limitations=data.get("limitations", list(DEFAULT_LIMITATIONS)),
            non_goals=data.get("non_goals", list(DEFAULT_NON_GOALS)),
        )

    @classmethod
    def from_json(cls, json_str: str) -> EvidenceReport:
        """Parse and validate JSON string into an EvidenceReport."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON evidence document: {exc}") from exc
        return cls.from_dict(data)


def validate_evidence_dict(data: dict[str, Any]) -> None:
    """Validate structure and constraints of an evidence dictionary.

    Raises ValueError or TypeError with actionable context on validation failure.
    """
    if not isinstance(data, dict):
        raise TypeError("Evidence document must be a JSON object.")

    # 1. Schema version
    version = data.get("schema_version")
    if not version:
        raise ValueError("Missing required field 'schema_version'.")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(
            f"Unsupported schema_version '{version}'. Supported versions: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )

    # 2. Tool metadata
    tool = data.get("tool")
    if not isinstance(tool, dict) or "name" not in tool or "version" not in tool:
        raise ValueError("Field 'tool' must be an object with 'name' and 'version'.")

    # 3. Collection metadata
    coll = data.get("collection")
    if not isinstance(coll, dict):
        raise TypeError("Missing or invalid 'collection' metadata object.")
    for req in ("timestamp_utc", "method", "scope", "consent_given"):
        if req not in coll:
            raise ValueError(f"Missing required collection field: '{req}'.")

    # 4. Device context
    device = data.get("device")
    if not isinstance(device, dict):
        raise TypeError("Missing or invalid 'device' context object.")
    if "serial_redacted" not in device or "state" not in device:
        raise ValueError("Device context must contain 'serial_redacted' and 'state'.")

    # 5. Observations
    obs_list = data.get("observations")
    if not isinstance(obs_list, list):
        raise TypeError("Field 'observations' must be a list.")

    for idx, obs in enumerate(obs_list):
        if not isinstance(obs, dict):
            raise TypeError(f"Observation at index {idx} must be an object.")
        for req in ("key", "label", "status"):
            if req not in obs:
                raise ValueError(f"Observation at index {idx} is missing required field '{req}'.")
        status = obs["status"]
        if status not in VALID_STATUSES:
            raise ValueError(
                f"Observation '{obs['key']}' has invalid status '{status}'. Must be one of {sorted(VALID_STATUSES)}."
            )

    # 6. Summary
    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise TypeError("Missing or invalid 'summary' object.")
    for count_key in ("total", "observed", "unsupported", "inaccessible", "not_applicable", "unknown", "error"):
        if count_key not in summary or not isinstance(summary[count_key], int):
            raise ValueError(f"Summary missing integer field '{count_key}'.")
