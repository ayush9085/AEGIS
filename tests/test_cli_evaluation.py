"""Unit and integration tests for CLI evaluation commands."""

import json
from pathlib import Path

from aegis.cli import main


def test_cli_evaluation_run_terminal_default(capsys):
    rc = main(["evaluation", "run"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "AEGIS PHASE 5 — RESEARCH EVALUATION" in captured.out
    assert "EXECUTIVE SUMMARY" in captured.out
    assert "RESULTS BY EVALUATION CATEGORY" in captured.out


def test_cli_evaluation_run_json_out(tmp_path: Path):
    dest = tmp_path / "custom_eval.json"
    rc = main(["evaluation", "run", "--out", str(dest), "--format", "json"])
    assert rc == 0
    assert dest.is_file()

    data = json.loads(dest.read_text(encoding="utf-8"))
    assert data["schema_version"] == "0.1.0"
    assert data["metrics"]["total_cases"] > 0
    assert data["metrics"]["failed"] == 0


def test_cli_evaluation_run_html_out(tmp_path: Path):
    dest = tmp_path / "custom_eval.json"
    rc = main(["evaluation", "run", "--out", str(dest), "--format", "html"])
    assert rc == 0
    assert dest.is_file()
    html_dest = dest.with_suffix(".html")
    assert html_dest.is_file()
    html_text = html_dest.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_text
    assert "AEGIS Evaluation &amp; Reproducibility Report" in html_text


def test_cli_evaluation_validate_success(tmp_path: Path, capsys):
    dest = tmp_path / "valid_eval.json"
    main(["evaluation", "run", "--out", str(dest)])

    rc = main(["evaluation", "validate", str(dest)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Validation passed: Valid AEGIS evaluation report" in captured.out


def test_cli_evaluation_validate_missing_file(capsys):
    rc = main(["evaluation", "validate", "nonexistent_file_path.json"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "File not found" in captured.err


def test_cli_evaluation_report_command(tmp_path: Path, capsys):
    report_json = tmp_path / "eval.json"
    main(["evaluation", "run", "--out", str(report_json)])

    # Report terminal
    rc = main(["evaluation", "report", str(report_json), "--format", "terminal"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "AEGIS PHASE 5 — RESEARCH EVALUATION" in captured.out

    # Report HTML
    out_html = tmp_path / "rendered.html"
    rc = main(["evaluation", "report", str(report_json), "--format", "html", "--out", str(out_html)])
    assert rc == 0
    assert out_html.is_file()
    assert "<!DOCTYPE html>" in out_html.read_text(encoding="utf-8")
