"""Integration tests for Research CLI workflows and commands."""

from pathlib import Path
from unittest.mock import patch

from aegis.cli import main

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_cli_research_analyze_terminal(capsys):
    ev_path = str(FIXTURES_DIR / "sample_evidence.json")
    ret = main(["research", "analyze", ev_path])
    assert ret == 0

    captured = capsys.readouterr()
    assert "AEGIS Evidence-Linked Research Intelligence Report" in captured.out
    assert "Sources:" in captured.out
    assert "Graph:" in captured.out
    assert "Derived Research Claims:" in captured.out


def test_cli_research_analyze_json_and_html_formats(tmp_path):
    ev_path = str(FIXTURES_DIR / "sample_evidence.json")

    # JSON export
    out_json = tmp_path / "research.json"
    ret = main(["research", "analyze", ev_path, "--format", "json", "--out", str(out_json)])
    assert ret == 0
    assert out_json.is_file()

    # Overwrite protection
    ret_blocked = main(["research", "analyze", ev_path, "--format", "json", "--out", str(out_json)])
    assert ret_blocked == 2

    # Overwrite permitted with flag
    ret_overwrite = main(["research", "analyze", ev_path, "--format", "json", "--out", str(out_json), "--overwrite"])
    assert ret_overwrite == 0

    # HTML export
    out_html = tmp_path / "research.html"
    ret_html = main(["research", "analyze", ev_path, "--format", "html", "--out", str(out_html)])
    assert ret_html == 0
    assert out_html.is_file()
    assert "<!DOCTYPE html>" in out_html.read_text(encoding="utf-8")


def test_cli_research_validate_success_and_failure(tmp_path, capsys):
    ev_path = str(FIXTURES_DIR / "sample_evidence.json")
    out_json = tmp_path / "research.json"
    main(["research", "analyze", ev_path, "--format", "json", "--out", str(out_json)])

    # Validate success
    ret_ok = main(["research", "validate", str(out_json)])
    assert ret_ok == 0
    cap_ok = capsys.readouterr()
    assert "Validation passed" in cap_ok.out

    # Corrupt file
    corrupt_json = tmp_path / "corrupt.json"
    corrupt_json.write_text("{\"schema_version\": \"99.9.9\"}", encoding="utf-8")
    ret_fail = main(["research", "validate", str(corrupt_json)])
    assert ret_fail == 2


def test_cli_research_report_command(tmp_path, capsys):
    ev_path = str(FIXTURES_DIR / "sample_evidence.json")
    out_json = tmp_path / "research.json"
    main(["research", "analyze", ev_path, "--format", "json", "--out", str(out_json)])

    out_html = tmp_path / "rendered.html"
    ret = main(["research", "report", str(out_json), "--out", str(out_html)])
    assert ret == 0
    assert out_html.is_file()
    assert "AEGIS Research Intelligence Report" in out_html.read_text(encoding="utf-8")


def test_cli_menu_routes_to_research(capsys):
    with patch("builtins.input", side_effect=["8", ""]):
        ret = main(["menu"])
    assert ret == 0

    captured = capsys.readouterr()
    assert "AEGIS Evidence-Linked Research Intelligence Report" in captured.out
