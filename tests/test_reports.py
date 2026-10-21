from pathlib import Path

from aegis.reports.html import render_html_report
from aegis.schema import EvidenceReport, Observation

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_html_report_rendering():
    sample_path = FIXTURES_DIR / "sample_evidence.json"
    report = EvidenceReport.from_json(sample_path.read_text(encoding="utf-8"))

    html_out = render_html_report(report)

    # Basic structural requirements
    assert "<!DOCTYPE html>" in html_out
    assert "<title>AEGIS Evidence Report — SM-M115F</title>" in html_out
    assert "Samsung" in html_out
    assert "SM-M115F" in html_out
    assert "SM***01" in html_out

    # Status badges
    assert "observed" in html_out
    assert "unsupported" in html_out
    assert "inaccessible" in html_out

    # Limitations & Non-goals
    assert "Unprivileged ADB read-only inspection cannot verify hardware root of trust." in html_out
    assert "Not a one-click root" in html_out

    # Self-contained: No remote fonts or external scripts/CDNs
    assert "https://" not in html_out
    assert "http://" not in html_out
    assert "<script" not in html_out


def test_html_report_xss_escaping():
    sample_path = FIXTURES_DIR / "sample_evidence.json"
    report = EvidenceReport.from_json(sample_path.read_text(encoding="utf-8"))

    # Inject malicious payload
    payload = '<script>alert("pwned")</script><img src="x" onerror="alert(1)">'
    report.device.model = payload
    report.observations.append(
        Observation(
            key="exploit.test",
            label="XSS Probe",
            status="observed",
            value=payload,
            error=payload,
            caveat=payload,
        )
    )

    html_out = render_html_report(report)

    # Ensure dangerous literal script tag was NOT rendered unescaped
    assert '<script>alert("pwned")</script>' not in html_out
    assert '<img src="x" onerror="alert(1)">' not in html_out

    # Ensure properly escaped entity versions are present
    assert "&lt;script&gt;alert(&quot;pwned&quot;)&lt;/script&gt;" in html_out
