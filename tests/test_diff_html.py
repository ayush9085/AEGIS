from pathlib import Path

from aegis.diff import compare_snapshots
from aegis.reports.diff_html import render_html_diff_report
from aegis.schema import EvidenceReport
from aegis.snapshots import create_snapshot_from_evidence

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_html_diff_report_basic_structure():
    ev1 = EvidenceReport.from_json((FIXTURES_DIR / "sample_evidence.json").read_text(encoding="utf-8"))
    ev2 = EvidenceReport.from_json((FIXTURES_DIR / "sample_evidence_updated.json").read_text(encoding="utf-8"))
    s1 = create_snapshot_from_evidence(ev1)
    s2 = create_snapshot_from_evidence(ev2)
    diff = compare_snapshots(s1, s2)

    html = render_html_diff_report(diff)
    assert html.startswith("<!DOCTYPE html>")
    assert "<title>AEGIS Semantic Comparison Report</title>" in html
    assert "Diff Schema v0.1.0" in html
    assert "build.version.release" in html
    assert "build.version.security_patch" in html
    # Check that there are no external dependencies
    assert "http://" not in html
    assert "https://" not in html
    # No executable JavaScript
    assert "<script" not in html.lower()


def test_html_diff_report_empty_state_zero_differences():
    ev = EvidenceReport.from_json((FIXTURES_DIR / "sample_evidence.json").read_text(encoding="utf-8"))
    s1 = create_snapshot_from_evidence(ev)
    s2 = create_snapshot_from_evidence(ev)
    diff = compare_snapshots(s1, s2)

    html = render_html_diff_report(diff)
    assert "Identical Snapshots — Zero Differences Detected" in html
    assert "All 6 observations have identical statuses and values" in html
    # Table should not be rendered
    assert "Observation Changes & Analysis" in html
    assert "✅" in html


def test_html_diff_report_synthetic_alert_banner():
    ev1 = EvidenceReport.from_json((FIXTURES_DIR / "sample_evidence.json").read_text(encoding="utf-8"))
    ev2 = EvidenceReport.from_json((FIXTURES_DIR / "sample_evidence_updated.json").read_text(encoding="utf-8"))
    s1 = create_snapshot_from_evidence(ev1)
    s2 = create_snapshot_from_evidence(ev2)
    diff = compare_snapshots(s1, s2)

    html = render_html_diff_report(diff)
    assert "Synthetic Evidence Alert" in html
    assert "Not collected from a live physical phone" in html


def test_html_diff_report_physical_handset_provenance():
    ev1 = EvidenceReport.from_json((FIXTURES_DIR / "sample_evidence.json").read_text(encoding="utf-8"))
    ev1_dict = ev1.to_dict()
    ev1_dict["collection"]["is_synthetic"] = False
    ev1_phys = EvidenceReport.from_dict(ev1_dict)

    ev2_dict = ev1.to_dict()
    ev2_dict["collection"]["is_synthetic"] = False
    ev2_phys = EvidenceReport.from_dict(ev2_dict)

    s1 = create_snapshot_from_evidence(ev1_phys)
    s2 = create_snapshot_from_evidence(ev2_phys)
    diff = compare_snapshots(s1, s2)

    html = render_html_diff_report(diff)
    assert "Synthetic Evidence Alert" not in html
    assert "📱 Physical Handset" in html


def test_html_diff_report_cross_device_override_banner():
    ev1 = EvidenceReport.from_json((FIXTURES_DIR / "sample_evidence.json").read_text(encoding="utf-8"))
    ev2 = EvidenceReport.from_json((FIXTURES_DIR / "sample_evidence.json").read_text(encoding="utf-8"))
    ev2_dict = ev2.to_dict()
    ev2_dict["device"]["model"] = "Pixel 7"
    ev2_mod = EvidenceReport.from_dict(ev2_dict)

    s1 = create_snapshot_from_evidence(ev1)
    s2 = create_snapshot_from_evidence(ev2_mod)
    diff = compare_snapshots(s1, s2, allow_different_devices=True)

    html = render_html_diff_report(diff)
    assert "Cross-Device Comparison Override Active" in html
    assert "Differences reflect architectural/OEM divergence" in html


def test_html_diff_report_identity_unverified_notice():
    ev1 = EvidenceReport.from_json((FIXTURES_DIR / "sample_evidence.json").read_text(encoding="utf-8"))
    ev2 = EvidenceReport.from_json((FIXTURES_DIR / "sample_evidence.json").read_text(encoding="utf-8"))
    ev1_dict = ev1.to_dict()
    ev1_dict["device"]["model"] = None
    ev1_dict["device"]["serial_redacted"] = "UNKNOWN"
    ev1_dict["device"]["build_fingerprint"] = None
    ev1_mod = EvidenceReport.from_dict(ev1_dict)

    s1 = create_snapshot_from_evidence(ev1_mod)
    s2 = create_snapshot_from_evidence(ev2)
    diff = compare_snapshots(s1, s2)

    html = render_html_diff_report(diff)
    assert "Identity Unverified" in html
    assert "lack sufficient identity fields" in html


def test_html_diff_report_strict_xss_escaping():
    ev1 = EvidenceReport.from_json((FIXTURES_DIR / "sample_evidence.json").read_text(encoding="utf-8"))
    ev2 = EvidenceReport.from_json((FIXTURES_DIR / "sample_evidence.json").read_text(encoding="utf-8"))

    # Inject potentially malicious scripts in values, models, labels
    ev2_dict = ev2.to_dict()
    ev2_dict["device"]["model"] = "<script>alert('xss_model')</script>"
    ev2_dict["observations"].append({
        "collector": "adb_prop",
        "command": "getprop xss.test",
        "key": "xss.test",
        "label": "<img src=x onerror=alert('xss_label')>",
        "status": "observed",
        "value": "<script>alert('xss_val')</script>",
        "raw_value": "<script>raw</script>",
        "collected_at": "2026-10-22T00:00:00Z",
        "error": "<marquee>alert('xss_err')</marquee>",
        "redacted": False,
    })
    ev2_mod = EvidenceReport.from_dict(ev2_dict)

    s1 = create_snapshot_from_evidence(ev1)
    s2 = create_snapshot_from_evidence(ev2_mod)
    diff = compare_snapshots(s1, s2, allow_different_devices=True)

    html = render_html_diff_report(diff)
    # Check that unescaped script tags do NOT exist
    assert "<script>alert('xss_model')</script>" not in html
    assert "<img src=x onerror=alert('xss_label')>" not in html
    assert "<script>alert('xss_val')</script>" not in html
    # But escaped versions DO exist
    assert "&lt;script&gt;alert(&#x27;xss_model&#x27;)&lt;/script&gt;" in html
    assert "&lt;img src=x onerror=alert(&#x27;xss_label&#x27;)&gt;" in html
    assert "&lt;script&gt;alert(&#x27;xss_val&#x27;)&lt;/script&gt;" in html
