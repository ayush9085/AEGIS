import json
from pathlib import Path
from unittest.mock import patch

import pytest

from aegis.adb import AdbDevice
from aegis.cli import main

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "AEGIS:" in captured.out
    assert "doctor" in captured.out
    assert "devices" in captured.out
    assert "collect" in captured.out
    assert "report" in captured.out
    assert "validate" in captured.out


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "aegis" in captured.out


def test_cli_no_args_shows_help(capsys):
    ret = main([])
    assert ret == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out


def test_cli_doctor_with_adb(capsys):
    with (
        patch("aegis.cli.find_adb", return_value="/usr/bin/adb"),
        patch("aegis.cli.get_adb_version", return_value="Android Debug Bridge version 1.0.41"),
    ):
        ret = main(["doctor"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "ADB Binary: /usr/bin/adb" in captured.out
        assert "Environment ready" in captured.out


def test_cli_doctor_without_adb(capsys):
    with patch("aegis.cli.find_adb", return_value=None):
        ret = main(["doctor"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "ADB Binary: NOT FOUND" in captured.out
        assert "brew install android-platform-tools" in captured.out


def test_cli_devices_empty(capsys):
    with patch("aegis.cli.list_devices", return_value=[]):
        ret = main(["devices"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "No ADB-visible devices found." in captured.out


def test_cli_devices_listed(capsys):
    devs = [
        AdbDevice(serial="DEV001", state="device"),
        AdbDevice(serial="DEV002", state="unauthorized"),
        AdbDevice(serial="DEV003", state="offline"),
    ]
    with patch("aegis.cli.list_devices", return_value=devs):
        ret = main(["devices"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "DEV001\tdevice" in captured.out
        assert "DEV002\tunauthorized" in captured.out
        assert "DEV003\toffline" in captured.out
        assert "One or more devices are 'unauthorized'" in captured.out
        assert "One or more devices are 'offline'" in captured.out


def test_cli_devices_adb_error(capsys):
    with patch("aegis.cli.list_devices", side_effect=FileNotFoundError("ADB was not found.")):
        ret = main(["devices"])
        assert ret == 2
        captured = capsys.readouterr()
        assert "error: ADB was not found" in captured.err


def test_cli_collect_declined_consent(capsys):
    with patch("builtins.input", return_value="n"):
        ret = main(["collect", "--device", "TEST_DEV", "--out", "./mock_out"])
        assert ret == 1
        captured = capsys.readouterr()
        assert "Collection aborted by user." in captured.err


def test_cli_collect_keyboard_interrupt(capsys):
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        ret = main(["collect", "--device", "TEST_DEV", "--out", "./mock_out"])
        assert ret == 1
        captured = capsys.readouterr()
        assert "Collection aborted by user." in captured.err


def test_cli_collect_success_interactive(tmp_path, capsys):
    sample_file = FIXTURES_DIR / "sample_evidence.json"
    from aegis.schema import EvidenceReport
    report = EvidenceReport.from_json(sample_file.read_text(encoding="utf-8"))

    with (
        patch("builtins.input", return_value="y"),
        patch("aegis.cli.collect_device_evidence", return_value=report),
    ):
        out_dir = str(tmp_path / "run_01")
        ret = main(["collect", "--device", "TEST_DEV", "--out", out_dir])
        assert ret == 0
        captured = capsys.readouterr()
        assert "Collection successful!" in captured.out

        ev_file = Path(out_dir) / "evidence.json"
        assert ev_file.is_file()
        loaded = json.loads(ev_file.read_text(encoding="utf-8"))
        assert loaded["schema_version"] == "0.1.0"


def test_cli_collect_success_non_interactive(tmp_path, capsys):
    sample_file = FIXTURES_DIR / "sample_evidence.json"
    from aegis.schema import EvidenceReport
    report = EvidenceReport.from_json(sample_file.read_text(encoding="utf-8"))

    with patch("aegis.cli.collect_device_evidence", return_value=report):
        out_dir = str(tmp_path / "run_02")
        ret = main(["collect", "--device", "TEST_DEV", "--out", out_dir, "--yes"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "Proceeding (consent specified via --yes flag)." in captured.out
        assert "Collection successful!" in captured.out

        ev_file = Path(out_dir) / "evidence.json"
        assert ev_file.is_file()


def test_cli_collect_device_error(capsys):
    with (
        patch("aegis.cli.collect_device_evidence", side_effect=RuntimeError("Device is unauthorized")),
    ):
        ret = main(["collect", "--device", "UNAUTH_DEV", "--out", "./out", "--yes"])
        assert ret == 2
        captured = capsys.readouterr()
        assert "error: Device is unauthorized" in captured.err


def test_cli_report_success(tmp_path, capsys):
    sample_file = FIXTURES_DIR / "sample_evidence.json"
    report_out = tmp_path / "custom_report.html"

    ret = main(["report", str(sample_file), "--out", str(report_out)])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Report successfully generated" in captured.out
    assert report_out.is_file()
    assert "<!DOCTYPE html>" in report_out.read_text(encoding="utf-8")


def test_cli_report_missing_file(capsys):
    ret = main(["report", "nonexistent_evidence.json"])
    assert ret == 2
    captured = capsys.readouterr()
    assert "error: Evidence file not found" in captured.err


def test_cli_report_malformed_file(tmp_path, capsys):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{malformed:json", encoding="utf-8")

    ret = main(["report", str(bad_file)])
    assert ret == 2
    captured = capsys.readouterr()
    assert "error: Failed to parse evidence document" in captured.err


def test_cli_validate_success(capsys):
    sample_file = FIXTURES_DIR / "sample_evidence.json"
    ret = main(["validate", str(sample_file)])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Validation passed: Valid AEGIS evidence document" in captured.out


def test_cli_validate_failure(tmp_path, capsys):
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text('{"schema_version": "9.9.9"}', encoding="utf-8")

    ret = main(["validate", str(invalid_file)])
    assert ret == 2
    captured = capsys.readouterr()
    assert "error: Validation failed" in captured.err


def test_cli_validate_missing_file(capsys):
    ret = main(["validate", "missing.json"])
    assert ret == 2
    captured = capsys.readouterr()
    assert "error: Evidence file not found" in captured.err
