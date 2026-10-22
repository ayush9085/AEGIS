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


def test_cli_collect_auto_detects_single_device(tmp_path, capsys):
    sample_file = FIXTURES_DIR / "sample_evidence.json"
    from aegis.schema import EvidenceReport
    report = EvidenceReport.from_json(sample_file.read_text(encoding="utf-8"))

    dev = AdbDevice(serial="AUTO_SERIAL_123", state="device")
    out_dir = str(tmp_path / "autodetect_run")

    with (
        patch("aegis.cli.list_devices", return_value=[dev]),
        patch("aegis.cli.collect_device_evidence", return_value=report) as mock_collect,
    ):
        ret = main(["collect", "--yes", "--out", out_dir])
        assert ret == 0
        mock_collect.assert_called_once_with(serial="AUTO_SERIAL_123", consent_given=True)
        captured = capsys.readouterr()
        assert "Auto-selected connected device:" in captured.out
        assert "Collection successful!" in captured.out
        assert (Path(out_dir) / "evidence.json").is_file()
        assert (Path(out_dir) / "report.html").is_file()


def test_cli_collect_no_devices_helpful_message(capsys):
    with patch("aegis.cli.list_devices", return_value=[]):
        ret = main(["collect"])
        assert ret == 2
        captured = capsys.readouterr()
        assert "error: No Android devices detected via ADB" in captured.err


def test_cli_demo_command(tmp_path, capsys):
    with patch("aegis.cli.open_in_browser") as mock_open:
        ret = main(["demo"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "Demo report generated successfully!" in captured.out
        mock_open.assert_called_once()


def test_cli_menu_quit(capsys):
    with patch("builtins.input", return_value="0"):
        ret = main(["menu"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "Welcome to AEGIS" in captured.out
        assert "Goodbye!" in captured.out


def test_cli_menu_routes_to_doctor(capsys):
    with (
        patch("builtins.input", return_value="3"),
        patch("aegis.cli.find_adb", return_value="/usr/bin/adb"),
        patch("aegis.cli.get_adb_version", return_value="Android Debug Bridge version 1.0.41"),
        patch("aegis.cli.list_devices", return_value=[]),
    ):
        ret = main(["menu"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "Welcome to AEGIS" in captured.out
        assert "ADB Binary: /usr/bin/adb" in captured.out


def test_cli_devices_with_model_label(capsys):
    devs = [AdbDevice(serial="DEV_M11", state="device")]
    with (
        patch("aegis.cli.list_devices", return_value=devs),
        patch("aegis.cli._get_device_model_label", return_value="Samsung Galaxy M11 (Android 12)"),
    ):
        ret = main(["devices"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "DEV_M11\tdevice" in captured.out
        assert "Samsung Galaxy M11 (Android 12)" in captured.out


def test_cli_collect_with_explicit_serial_when_adb_missing_on_host(capsys):
    with (
        patch("aegis.cli.find_adb", return_value=None),
        patch("builtins.input", return_value="n"),
    ):
        ret = main(["collect", "--device", "TEST_DEV", "--out", "./mock_out"])
        assert ret == 1
        captured = capsys.readouterr()
        assert "Target Handset:" in captured.out
        assert "Collection aborted by user." in captured.err


def test_cli_snapshot_success_and_overwrite(tmp_path, capsys):
    sample_file = FIXTURES_DIR / "sample_evidence.json"
    snap_out = tmp_path / "baseline_snap.json"

    # 1. Create snapshot
    ret = main(["snapshot", str(sample_file), "--out", str(snap_out), "--label", "Baseline"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Snapshot created successfully!" in captured.out
    assert "Content Hash:" in captured.out
    assert snap_out.is_file()

    # 2. Refuse overwrite without --overwrite
    ret2 = main(["snapshot", str(sample_file), "--out", str(snap_out)])
    assert ret2 == 2
    captured2 = capsys.readouterr()
    assert "already exists. Use overwrite option" in captured2.err

    # 3. Overwrite with --overwrite
    ret3 = main(["snapshot", str(sample_file), "--out", str(snap_out), "--overwrite"])
    assert ret3 == 0
    captured3 = capsys.readouterr()
    assert "Snapshot created successfully!" in captured3.out


def test_cli_snapshot_missing_or_corrupt_file(tmp_path, capsys):
    # Missing file
    ret = main(["snapshot", "nonexistent.json"])
    assert ret == 2
    captured = capsys.readouterr()
    assert "error: Evidence file not found" in captured.err

    # Corrupt file
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid_json", encoding="utf-8")
    ret2 = main(["snapshot", str(bad_file)])
    assert ret2 == 2
    captured2 = capsys.readouterr()
    assert "error: Failed to load evidence" in captured2.err


def test_cli_diff_terminal_and_formats(tmp_path, capsys):
    sample_file1 = FIXTURES_DIR / "sample_evidence.json"
    sample_file2 = FIXTURES_DIR / "sample_evidence_updated.json"

    snap1 = tmp_path / "snap1.json"
    snap2 = tmp_path / "snap2.json"
    main(["snapshot", str(sample_file1), "--out", str(snap1)])
    main(["snapshot", str(sample_file2), "--out", str(snap2)])
    capsys.readouterr()  # flush output

    # 1. Terminal diff
    ret = main(["diff", str(snap1), str(snap2)])
    assert ret == 0
    captured = capsys.readouterr()
    assert "AEGIS Semantic Snapshot Comparison" in captured.out
    assert "Status:" in captured.out
    assert "build.version.release" in captured.out

    # 2. JSON diff
    diff_json_out = tmp_path / "diff.json"
    ret_json = main(["diff", str(snap1), str(snap2), "--format", "json", "--out", str(diff_json_out)])
    assert ret_json == 0
    assert diff_json_out.is_file()
    loaded_diff = json.loads(diff_json_out.read_text(encoding="utf-8"))
    assert loaded_diff["diff_version"] == "0.1.0"
    assert loaded_diff["summary"]["value_changed"] > 0

    # 3. HTML diff
    diff_html_out = tmp_path / "diff.html"
    ret_html = main(["diff", str(snap1), str(snap2), "--format", "html", "--out", str(diff_html_out)])
    assert ret_html == 0
    assert diff_html_out.is_file()
    html_text = diff_html_out.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_text
    assert "AEGIS Semantic Diff Report" in html_text

    # Rejects existing without --overwrite
    ret_reject = main(["diff", str(snap1), str(snap2), "--format", "html", "--out", str(diff_html_out)])
    assert ret_reject == 2
    captured = capsys.readouterr()
    assert "already exists. Use --overwrite" in captured.err

    # With --overwrite
    ret_overwrite = main(["diff", str(snap1), str(snap2), "--format", "html", "--out", str(diff_html_out), "--overwrite"])
    assert ret_overwrite == 0


def test_cli_diff_cross_device_blocked_and_override(tmp_path, capsys):
    sample_file1 = FIXTURES_DIR / "sample_evidence.json"
    snap1 = tmp_path / "snap1.json"
    main(["snapshot", str(sample_file1), "--out", str(snap1)])

    # Create snap2 with different model
    from aegis.schema import EvidenceReport
    from aegis.snapshots import create_snapshot_from_evidence, save_snapshot
    ev = EvidenceReport.from_json(sample_file1.read_text(encoding="utf-8"))
    ev_dict = ev.to_dict()
    ev_dict["device"]["model"] = "DifferentPhone"
    ev_diff = EvidenceReport.from_dict(ev_dict)
    snap2 = tmp_path / "snap2.json"
    save_snapshot(create_snapshot_from_evidence(ev_diff), snap2)
    capsys.readouterr()

    # Diff blocked by default
    ret_blocked = main(["diff", str(snap1), str(snap2)])
    assert ret_blocked == 2
    captured = capsys.readouterr()
    assert "Cannot compare snapshots from different devices" in captured.err

    # Allowed with flag
    ret_allowed = main(["diff", str(snap1), str(snap2), "--allow-different-devices"])
    assert ret_allowed == 0
    captured_allowed = capsys.readouterr()
    assert "AEGIS Semantic Snapshot Comparison" in captured_allowed.out
    assert "Cross-device comparison override is ACTIVE" in captured_allowed.out


def test_cli_diff_integrity_tamper_detection(tmp_path, capsys):
    sample_file = FIXTURES_DIR / "sample_evidence.json"
    snap1 = tmp_path / "snap1.json"
    snap2 = tmp_path / "snap2.json"
    main(["snapshot", str(sample_file), "--out", str(snap1)])
    main(["snapshot", str(sample_file), "--out", str(snap2)])
    capsys.readouterr()

    # Tamper with snap2 content without updating hash
    snap_data = json.loads(snap2.read_text(encoding="utf-8"))
    snap_data["device"]["model"] = "TamperedModel"
    snap2.write_text(json.dumps(snap_data), encoding="utf-8")

    ret = main(["diff", str(snap1), str(snap2)])
    assert ret == 2
    captured = capsys.readouterr()
    assert "Snapshot integrity verification failed" in captured.err



