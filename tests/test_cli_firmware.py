"""Integration tests for AEGIS firmware CLI command family."""

import json
import struct
from unittest.mock import patch

from aegis.cli import main


def _create_synthetic_boot_img(path):
    magic = b"ANDROID!"
    hdr = struct.pack("<8s4I4II1536s", magic, 4096, 2048, 0, 4096, 0, 0, 0, 0, 3, b"\x00" * 1536)
    path.write_bytes(hdr.ljust(4096 + 4096 + 2048, b"\x00"))


def test_cli_firmware_inspect_terminal(tmp_path, capsys):
    boot_file = tmp_path / "boot.img"
    _create_synthetic_boot_img(boot_file)

    ret = main(["firmware", "inspect", str(boot_file)])
    assert ret == 0
    captured = capsys.readouterr()
    assert "AEGIS Firmware Intelligence Report" in captured.out
    assert "boot.img" in captured.out
    assert "android_boot_image" in captured.out
    assert "boot.header_version" in captured.out


def test_cli_firmware_inspect_json_and_html_formats(tmp_path, capsys):
    boot_file = tmp_path / "boot.img"
    _create_synthetic_boot_img(boot_file)

    # 1. JSON output
    json_out = tmp_path / "report.json"
    ret_json = main(["firmware", "inspect", str(boot_file), "--format", "json", "--out", str(json_out)])
    assert ret_json == 0
    assert json_out.is_file()
    data = json.loads(json_out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "0.1.0"
    assert len(data["artifacts"]) == 1

    # Overwrite protection
    ret_no_overwrite = main(["firmware", "inspect", str(boot_file), "--format", "json", "--out", str(json_out)])
    assert ret_no_overwrite == 2
    captured = capsys.readouterr()
    assert "already exists. Use --overwrite" in captured.err

    # Overwrite enabled
    ret_overwrite = main(["firmware", "inspect", str(boot_file), "--format", "json", "--out", str(json_out), "--overwrite"])
    assert ret_overwrite == 0

    # 2. HTML output
    html_out = tmp_path / "report.html"
    ret_html = main(["firmware", "inspect", str(boot_file), "--format", "html", "--out", str(html_out)])
    assert ret_html == 0
    assert html_out.is_file()
    html_text = html_out.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_text
    assert "AEGIS Firmware Intelligence Report" in html_text


def test_cli_firmware_inspect_missing_target(capsys):
    ret = main(["firmware", "inspect", "nonexistent_file_path.img"])
    assert ret == 2
    captured = capsys.readouterr()
    assert "error: Target firmware path not found" in captured.err


def test_cli_firmware_validate_success_and_failure(tmp_path, capsys):
    boot_file = tmp_path / "boot.img"
    _create_synthetic_boot_img(boot_file)
    report_file = tmp_path / "valid_report.json"
    main(["firmware", "inspect", str(boot_file), "--format", "json", "--out", str(report_file)])
    capsys.readouterr()

    # Success
    ret_val = main(["firmware", "validate", str(report_file)])
    assert ret_val == 0
    captured_val = capsys.readouterr()
    assert "Validation passed: Valid AEGIS firmware report" in captured_val.out

    # Corrupted / invalid file
    bad_file = tmp_path / "bad.json"
    bad_file.write_text('{"schema_version": "99.0.0"}', encoding="utf-8")
    ret_bad = main(["firmware", "validate", str(bad_file)])
    assert ret_bad == 2
    captured_bad = capsys.readouterr()
    assert "Firmware validation failed" in captured_bad.err

    # Missing file
    ret_miss = main(["firmware", "validate", "missing.json"])
    assert ret_miss == 2


def test_cli_firmware_report_command(tmp_path, capsys):
    boot_file = tmp_path / "boot.img"
    _create_synthetic_boot_img(boot_file)
    report_file = tmp_path / "saved_report.json"
    main(["firmware", "inspect", str(boot_file), "--format", "json", "--out", str(report_file)])
    capsys.readouterr()

    html_dest = tmp_path / "rendered.html"
    ret = main(["firmware", "report", str(report_file), "--out", str(html_dest)])
    assert ret == 0
    assert html_dest.is_file()
    captured = capsys.readouterr()
    assert "Report successfully generated" in captured.out


def test_cli_menu_routes_to_firmware_inspect(tmp_path, capsys):
    boot_file = tmp_path / "boot.img"
    _create_synthetic_boot_img(boot_file)

    with patch("builtins.input", side_effect=["7", str(boot_file), "0"]):
        ret = main(["menu"])
        assert ret == 0
        captured = capsys.readouterr()
        assert "Welcome to AEGIS" in captured.out
        assert "Offline Firmware Inspection" in captured.out
        assert "boot.img" in captured.out
