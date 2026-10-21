from pathlib import Path

import pytest

from aegis.schema import (
    CURRENT_SCHEMA_VERSION,
    EvidenceReport,
    Observation,
    SummaryCounts,
    validate_evidence_dict,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_schema_valid_fixture():
    sample_path = FIXTURES_DIR / "sample_evidence.json"
    content = sample_path.read_text(encoding="utf-8")
    report = EvidenceReport.from_json(content)

    assert report.schema_version == CURRENT_SCHEMA_VERSION
    assert report.tool["name"] == "aegis"
    assert report.device.model == "SM-M115F"
    assert report.summary.total == 6
    assert report.summary.observed == 4
    assert report.summary.unsupported == 1
    assert report.summary.inaccessible == 1

    # Round-trip serialization
    json_out = report.to_json()
    reparsed = EvidenceReport.from_json(json_out)
    assert reparsed.device.model == report.device.model


def test_schema_rejects_non_dict():
    with pytest.raises(TypeError, match="must be a JSON object"):
        validate_evidence_dict(["not", "a", "dict"])  # type: ignore[arg-type]


def test_schema_missing_version():
    data = {"tool": {"name": "aegis", "version": "0.1.0"}}
    with pytest.raises(ValueError, match="Missing required field 'schema_version'"):
        validate_evidence_dict(data)


def test_schema_unsupported_version():
    data = {"schema_version": "9.9.9", "tool": {"name": "aegis", "version": "0.1.0"}}
    with pytest.raises(ValueError, match="Unsupported schema_version '9.9.9'"):
        validate_evidence_dict(data)


def test_schema_missing_collection():
    data = {"schema_version": CURRENT_SCHEMA_VERSION, "tool": {"name": "aegis", "version": "0.1.0"}}
    with pytest.raises(TypeError, match="Missing or invalid 'collection'"):
        validate_evidence_dict(data)


def test_schema_missing_device():
    data = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "tool": {"name": "aegis", "version": "0.1.0"},
        "collection": {
            "timestamp_utc": "2026-10-21T00:00:00Z",
            "method": "adb_read_only",
            "scope": "test",
            "consent_given": True,
        },
    }
    with pytest.raises(TypeError, match="Missing or invalid 'device'"):
        validate_evidence_dict(data)


def test_schema_invalid_observation_status():
    obs_invalid = {
        "key": "test.key",
        "label": "Test",
        "status": "compromised",  # Disallowed non-neutral verdict
    }
    data = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "tool": {"name": "aegis", "version": "0.1.0"},
        "collection": {
            "timestamp_utc": "2026-10-21T00:00:00Z",
            "method": "adb_read_only",
            "scope": "test",
            "consent_given": True,
        },
        "device": {"serial_redacted": "TEST", "state": "device"},
        "observations": [obs_invalid],
        "summary": {
            "total": 1,
            "observed": 0,
            "unsupported": 0,
            "inaccessible": 0,
            "not_applicable": 0,
            "unknown": 0,
            "error": 0,
        },
    }
    with pytest.raises(ValueError, match="invalid status 'compromised'"):
        validate_evidence_dict(data)


def test_summary_counts_covers_all_statuses():
    observations = [
        Observation(key="k1", label="L1", status="observed"),
        Observation(key="k2", label="L2", status="unsupported"),
        Observation(key="k3", label="L3", status="inaccessible"),
        Observation(key="k4", label="L4", status="not_applicable"),
        Observation(key="k5", label="L5", status="unknown"),
        Observation(key="k6", label="L6", status="error"),
    ]
    summary = SummaryCounts.from_observations(observations)
    assert summary.total == 6
    assert summary.observed == 1
    assert summary.unsupported == 1
    assert summary.inaccessible == 1
    assert summary.not_applicable == 1
    assert summary.unknown == 1
    assert summary.error == 1


def test_observation_invalid_status_instantiation():
    with pytest.raises(ValueError, match="Invalid status 'safe'"):
        Observation(key="test", label="Test", status="safe")


def test_malformed_json_raises_value_error():
    with pytest.raises(ValueError, match="Malformed JSON"):
        EvidenceReport.from_json("invalid-json{}}")
