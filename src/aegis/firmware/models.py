"""Data models and validation for offline firmware intelligence reports."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from aegis.schema import VALID_STATUSES

FIRMWARE_SCHEMA_VERSION = "0.1.0"
SUPPORTED_FIRMWARE_SCHEMA_VERSIONS = {FIRMWARE_SCHEMA_VERSION}

DEFAULT_FIRMWARE_LIMITATIONS = [
    "Offline static firmware analysis extracts headers and container metadata only.",
    "File hashes verify integrity of the inspected file; they do NOT prove OEM cryptographic signatures or vendor authenticity.",
    "Absence of a partition or header field in user-supplied files is NOT proof that the vendor firmware omitted it.",
    "AEGIS does NOT execute firmware binaries, decrypt encrypted images, or modify hardware state.",
    "Static property values in build.prop or headers may not reflect dynamic kernel or bootloader enforcement.",
]


class FirmwareReportError(Exception):
    """Base exception for firmware report errors."""


class FirmwareValidationError(FirmwareReportError):
    """Raised when a firmware report fails schema validation."""


@dataclass
class ArtifactInventory:
    """An individual inspected file or container artifact within the firmware target."""

    path: str
    size_bytes: int
    sha256: str
    detected_format: str
    parser_used: str | None = None
    parse_status: str = "observed"
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    def __post_init__(self) -> None:
        if self.parse_status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid parse_status '{self.parse_status}'. Must be one of {sorted(VALID_STATUSES)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FirmwareFinding:
    """A granular finding extracted from a firmware artifact."""

    finding_id: str
    category: str
    key: str
    label: str
    status: str
    value: Any = None
    evidence_source: str = ""
    parser: str = ""
    parser_version: str = "0.1.0"
    confidence: str = "authoritative"
    caveat: str | None = None
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{self.status}'. Must be one of {sorted(VALID_STATUSES)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FirmwareReport:
    """A versioned, self-contained firmware analysis report."""

    schema_version: str
    aegis_version: str
    analyzed_at_utc: str
    target_name: str
    target_type: str
    artifacts: list[ArtifactInventory]
    findings: list[FirmwareFinding]
    summary: dict[str, int]
    limitations: list[str] = field(default_factory=lambda: list(DEFAULT_FIRMWARE_LIMITATIONS))
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "aegis_version": self.aegis_version,
            "analyzed_at_utc": self.analyzed_at_utc,
            "target_name": self.target_name,
            "target_type": self.target_type,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "findings": [f.to_dict() for f in self.findings],
            "summary": dict(self.summary),
            "limitations": list(self.limitations),
            "warnings": list(self.warnings),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FirmwareReport:
        validate_firmware_report_dict(data)
        artifacts = [ArtifactInventory(**a) for a in data["artifacts"]]
        findings = [FirmwareFinding(**f) for f in data["findings"]]
        return cls(
            schema_version=data["schema_version"],
            aegis_version=data["aegis_version"],
            analyzed_at_utc=data["analyzed_at_utc"],
            target_name=data["target_name"],
            target_type=data["target_type"],
            artifacts=artifacts,
            findings=findings,
            summary=dict(data["summary"]),
            limitations=list(data.get("limitations", DEFAULT_FIRMWARE_LIMITATIONS)),
            warnings=list(data.get("warnings", [])),
        )

    @classmethod
    def from_json(cls, json_str: str) -> FirmwareReport:
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise FirmwareValidationError(f"Malformed JSON firmware report: {exc}") from exc
        return cls.from_dict(data)


def validate_firmware_report_dict(data: dict[str, Any]) -> None:
    """Validate structure and required fields of a firmware report dictionary."""
    if not isinstance(data, dict):
        raise FirmwareValidationError("Firmware report document must be a JSON object.")

    version = data.get("schema_version")
    if not version:
        raise FirmwareValidationError("Missing required field 'schema_version'.")
    if version not in SUPPORTED_FIRMWARE_SCHEMA_VERSIONS:
        raise FirmwareValidationError(
            f"Unsupported firmware schema_version '{version}'. Supported: {sorted(SUPPORTED_FIRMWARE_SCHEMA_VERSIONS)}"
        )

    for req in (
        "aegis_version",
        "analyzed_at_utc",
        "target_name",
        "target_type",
        "artifacts",
        "findings",
        "summary",
    ):
        if req not in data:
            raise FirmwareValidationError(f"Firmware report missing required field '{req}'.")

    if not isinstance(data["artifacts"], list):
        raise FirmwareValidationError("Field 'artifacts' must be a list.")
    if not isinstance(data["findings"], list):
        raise FirmwareValidationError("Field 'findings' must be a list.")
    if not isinstance(data["summary"], dict):
        raise FirmwareValidationError("Field 'summary' must be an object.")
