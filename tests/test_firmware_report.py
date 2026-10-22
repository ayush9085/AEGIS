"""Unit tests for firmware report model, serialization, and validation."""

import pytest

from aegis.firmware.models import (
    ArtifactInventory,
    FirmwareFinding,
    FirmwareReport,
    FirmwareValidationError,
    validate_firmware_report_dict,
)


def test_firmware_report_roundtrip_serialization():
    art = ArtifactInventory(
        path="boot.img",
        size_bytes=4096,
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        detected_format="android_boot_image",
        parser_used="aegis_boot_img_parser",
        parse_status="observed",
        warnings=["Non-critical warning"],
    )
    finding = FirmwareFinding(
        finding_id="boot.img:header:header_version",
        category="header",
        key="boot.header_version",
        label="Boot Image Header Version",
        status="observed",
        value=3,
        evidence_source="boot.img",
        parser="aegis_boot_img_parser",
    )
    report = FirmwareReport(
        schema_version="0.1.0",
        aegis_version="0.1.0",
        analyzed_at_utc="2026-10-22T08:00:00Z",
        target_name="sample_fw",
        target_type="directory",
        artifacts=[art],
        findings=[finding],
        summary={
            "total_artifacts": 1,
            "total_findings": 1,
            "observed": 1,
            "unsupported": 0,
            "inaccessible": 0,
            "not_applicable": 0,
            "unknown": 0,
            "error": 0,
            "warnings_count": 1,
        },
        warnings=["Sample global warning"],
    )

    json_str = report.to_json(indent=2)
    reparsed = FirmwareReport.from_json(json_str)

    assert reparsed.schema_version == report.schema_version
    assert reparsed.target_name == report.target_name
    assert len(reparsed.artifacts) == 1
    assert reparsed.artifacts[0].detected_format == "android_boot_image"
    assert len(reparsed.findings) == 1
    assert reparsed.findings[0].value == 3
    assert reparsed.summary == report.summary


def test_firmware_report_validation_errors():
    # Not a dict
    with pytest.raises(FirmwareValidationError, match="must be a JSON object"):
        validate_firmware_report_dict(["not", "a", "dict"])

    # Missing schema_version
    with pytest.raises(FirmwareValidationError, match="Missing required field 'schema_version'"):
        validate_firmware_report_dict({"aegis_version": "0.1.0"})

    # Unsupported schema version
    with pytest.raises(FirmwareValidationError, match="Unsupported firmware schema_version"):
        validate_firmware_report_dict({"schema_version": "99.0.0"})

    # Missing required field
    valid_base = {
        "schema_version": "0.1.0",
        "aegis_version": "0.1.0",
        "analyzed_at_utc": "2026-10-22T00:00:00Z",
        "target_name": "target",
        "target_type": "file",
        "artifacts": [],
        "findings": [],
        "summary": {},
    }
    for req in ("aegis_version", "analyzed_at_utc", "target_name", "target_type", "artifacts", "findings", "summary"):
        bad_copy = dict(valid_base)
        del bad_copy[req]
        with pytest.raises(FirmwareValidationError, match=f"missing required field '{req}'"):
            validate_firmware_report_dict(bad_copy)

    # Malformed JSON
    with pytest.raises(FirmwareValidationError, match="Malformed JSON"):
        FirmwareReport.from_json("{invalid_json:123")
