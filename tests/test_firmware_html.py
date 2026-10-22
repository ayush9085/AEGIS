"""Unit tests for firmware HTML report generation and XSS mitigation."""

from aegis.firmware.models import ArtifactInventory, FirmwareFinding, FirmwareReport
from aegis.reports.firmware_html import render_html_firmware_report


def test_firmware_html_basic_structure():
    art = ArtifactInventory(
        path="boot.img",
        size_bytes=2048,
        sha256="abcd1234ef567890abcd1234ef567890abcd1234ef567890abcd1234ef567890",
        detected_format="android_boot_image",
        parser_used="aegis_boot_img_parser",
        parse_status="observed",
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
        target_name="sample_target",
        target_type="file",
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
            "warnings_count": 0,
        },
    )

    html = render_html_firmware_report(report)
    assert html.startswith("<!DOCTYPE html>")
    assert "AEGIS Firmware Intelligence Report" in html
    assert "sample_target" in html
    assert "boot.img" in html
    assert "boot.header_version" in html
    # Zero external CDN links
    assert "http://" not in html
    assert "https://" not in html
    # No script execution
    assert "<script" not in html.lower()


def test_firmware_html_xss_escaping():
    art = ArtifactInventory(
        path="<script>alert('xss_path')</script>",
        size_bytes=100,
        sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        detected_format="<img src=x onerror=alert('xss_fmt')>",
        parser_used="custom_parser",
        parse_status="observed",
        warnings=["<svg onload=alert('xss_warn')>"],
        error="<marquee>xss_err</marquee>",
    )
    finding = FirmwareFinding(
        finding_id="xss:test",
        category="<script>xss_cat</script>",
        key="xss.key",
        label="<img src=x onerror=alert('xss_label')>",
        status="observed",
        value="<script>alert('xss_val')</script>",
        evidence_source="<script>xss_src</script>",
        caveat="<style>body{display:none}</style>",
    )
    report = FirmwareReport(
        schema_version="0.1.0",
        aegis_version="0.1.0",
        analyzed_at_utc="2026-10-22T08:00:00Z",
        target_name="<script>alert('xss_target')</script>",
        target_type="file",
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
        warnings=["<script>alert('global_warn')</script>"],
    )

    html = render_html_firmware_report(report)

    # Check unescaped payloads do NOT exist
    assert "<script>alert('xss_path')</script>" not in html
    assert "<img src=x onerror=alert('xss_fmt')>" not in html
    assert "<script>alert('xss_val')</script>" not in html
    assert "<style>body{display:none}</style>" not in html
    assert "<script>alert('global_warn')</script>" not in html

    # Check escaped versions DO exist
    assert "&lt;script&gt;alert(&#x27;xss_path&#x27;)&lt;/script&gt;" in html
    assert "&lt;img src=x onerror=alert(&#x27;xss_fmt&#x27;)&gt;" in html
    assert "&lt;script&gt;alert(&#x27;xss_val&#x27;)&lt;/script&gt;" in html
