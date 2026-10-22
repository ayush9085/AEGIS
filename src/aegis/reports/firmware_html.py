"""Self-contained, accessible HTML firmware intelligence report generator."""

from __future__ import annotations

import html
from typing import Any

from aegis.firmware.models import FirmwareReport

STATUS_STYLES = {
    "observed": ("#0f5132", "#d1e7dd", "Observed"),
    "unsupported": ("#664d03", "#fff3cd", "Unsupported"),
    "inaccessible": ("#41464b", "#e2e3e5", "Inaccessible"),
    "not_applicable": ("#495057", "#e9ecef", "Not Applicable"),
    "unknown": ("#41464b", "#e2e3e5", "Unknown"),
    "error": ("#842029", "#f8d7da", "Error"),
}


def _esc(val: Any) -> str:
    """Safely escape any value for HTML text or attributes."""
    if val is None:
        return ""
    return html.escape(str(val), quote=True)


def _fmt_size(size_bytes: int) -> str:
    """Format size into human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def render_html_firmware_report(report: FirmwareReport) -> str:
    """Generate self-contained HTML report with strict escaping and zero remote assets."""
    r = report
    s = r.summary

    def render_status_pill(status: str) -> str:
        fg, bg, label = STATUS_STYLES.get(status, ("#212529", "#e2e3e5", status.title()))
        return (
            f'<span style="display:inline-block; padding:3px 8px; font-size:0.75rem; '
            f'font-weight:700; text-transform:uppercase; border-radius:4px; '
            f'background-color:{bg}; color:{fg};">{_esc(label)}</span>'
        )

    # Artifact Rows
    artifact_rows = []
    for art in r.artifacts:
        status_pill = render_status_pill(art.parse_status)
        warn_html = ""
        if art.warnings:
            warn_items = "".join(f"<li>{_esc(w)}</li>" for w in art.warnings)
            warn_html = f'<ul style="margin:4px 0 0 16px; padding:0; color:#856404; font-size:0.8rem;">{warn_items}</ul>'
        if art.error:
            warn_html += f'<div style="color:#842029; font-size:0.8rem; margin-top:2px;">Error: {_esc(art.error)}</div>'

        artifact_rows.append(
            f"""
            <tr style="border-bottom:1px solid #e9ecef;">
                <td style="padding:10px 14px; font-weight:600; vertical-align:top;">
                    <code>{_esc(art.path)}</code>
                    {warn_html}
                </td>
                <td style="padding:10px 14px; vertical-align:top;">
                    <span style="display:inline-block; padding:2px 6px; font-size:0.75rem; font-weight:600; border-radius:3px; background:#e9ecef; color:#495057;">
                        {_esc(art.detected_format)}
                    </span>
                </td>
                <td style="padding:10px 14px; vertical-align:top; white-space:nowrap; font-size:0.85rem;">
                    {_esc(_fmt_size(art.size_bytes))}
                </td>
                <td style="padding:10px 14px; vertical-align:top; font-size:0.8rem;">
                    <code style="word-break:break-all;">{_esc(art.sha256[:16])}...{_esc(art.sha256[-8:])}</code>
                </td>
                <td style="padding:10px 14px; vertical-align:top;">{status_pill}</td>
            </tr>
            """
        )

    # Finding Rows
    finding_rows = []
    for f in r.findings:
        status_pill = render_status_pill(f.status)
        val_display = _esc(f.value)
        if isinstance(f.value, (dict, list)):
            import json
            val_display = f"<pre style='margin:0; font-size:0.75rem; max-height:120px; overflow-y:auto;'>{_esc(json.dumps(f.value, indent=2))}</pre>"
        else:
            val_display = f"<code>{val_display}</code>"

        caveat_html = ""
        if f.caveat:
            caveat_html = f"<div style='margin-top:4px; font-size:0.8rem; color:#6c757d; font-style:italic;'>{_esc(f.caveat)}</div>"

        finding_rows.append(
            f"""
            <tr style="border-bottom:1px solid #e9ecef;">
                <td style="padding:10px 14px; vertical-align:top;">
                    <strong>{_esc(f.label)}</strong><br>
                    <code style="font-size:0.75rem; color:#6c757d;">{_esc(f.key)}</code>
                </td>
                <td style="padding:10px 14px; vertical-align:top;">
                    <span style="display:inline-block; padding:2px 6px; font-size:0.75rem; font-weight:600; border-radius:3px; background:#f1f3f5; color:#343a40;">
                        {_esc(f.category)}
                    </span>
                </td>
                <td style="padding:10px 14px; vertical-align:top;">{status_pill}</td>
                <td style="padding:10px 14px; vertical-align:top;">
                    {val_display}
                    {caveat_html}
                </td>
                <td style="padding:10px 14px; vertical-align:top; font-size:0.85rem; color:#495057;">
                    <code>{_esc(f.evidence_source)}</code>
                </td>
            </tr>
            """
        )

    warnings_banner = ""
    if r.warnings:
        warn_li = "".join(f"<li>{_esc(w)}</li>" for w in r.warnings)
        warnings_banner = f"""
        <div style="background:#fff3cd; border:1px solid #ffe69c; color:#856404; padding:14px 20px; border-radius:8px; margin-bottom:24px; font-size:0.9rem;">
            <strong>⚠️ Inspection Warnings:</strong>
            <ul style="margin:6px 0 0 16px; padding:0;">{warn_li}</ul>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AEGIS Firmware Intelligence Report — {_esc(r.target_name)}</title>
    <style>
        :root {{
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}
        body {{
            font-family: var(--font-sans);
            line-height: 1.5;
            color: #212529;
            background-color: #f8f9fa;
            margin: 0;
            padding: 24px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 12px;
            border: 1px solid #e9ecef;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            padding: 32px;
        }}
        .metric-card {{
            flex: 1;
            min-width: 130px;
            background: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 14px;
            text-align: center;
        }}
        .metric-val {{
            font-size: 1.8rem;
            font-weight: 700;
            line-height: 1.1;
        }}
        .metric-label {{
            font-size: 0.75rem;
            font-weight: 600;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 6px;
        }}
        code {{
            font-family: var(--font-mono);
            font-size: 0.85em;
            padding: 2px 4px;
            background-color: #f1f3f5;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header style="border-bottom: 2px solid #f1f3f5; padding-bottom: 20px; margin-bottom: 24px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
                <div>
                    <h1 style="margin:0; font-size:1.75rem; color:#0f172a; display:flex; align-items:center; gap:10px;">
                        <span>📦</span> AEGIS Firmware Intelligence Report
                    </h1>
                    <p style="margin:6px 0 0 0; color:#64748b; font-size:0.95rem;">
                        Offline Static Analysis of <strong>{_esc(r.target_name)}</strong> ({_esc(r.target_type)})
                    </p>
                </div>
                <div style="text-align:right; font-size:0.85rem; color:#64748b;">
                    <div><strong>Schema:</strong> v{_esc(r.schema_version)} | <strong>AEGIS:</strong> v{_esc(r.aegis_version)}</div>
                    <div><strong>Analyzed:</strong> {_esc(r.analyzed_at_utc)}</div>
                </div>
            </div>
        </header>

        {warnings_banner}

        <!-- Metrics Cards -->
        <div style="display:flex; flex-wrap:wrap; gap:12px; margin-bottom:28px;">
            <div class="metric-card">
                <div class="metric-val" style="color:#0f172a;">{s.get('total_artifacts', 0)}</div>
                <div class="metric-label">Artifacts</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color:#0284c7;">{s.get('total_findings', 0)}</div>
                <div class="metric-label">Findings</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color:#16a34a;">{s.get('observed', 0)}</div>
                <div class="metric-label">Observed</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color:#d97706;">{s.get('unsupported', 0)}</div>
                <div class="metric-label">Unsupported</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color:#dc2626;">{s.get('error', 0)}</div>
                <div class="metric-label">Errors</div>
            </div>
        </div>

        <!-- Artifact Inventory Table -->
        <section style="margin-bottom:32px;">
            <h2 style="font-size:1.25rem; color:#0f172a; margin:0 0 12px 0;">Artifact Inventory ({len(r.artifacts)})</h2>
            <div style="overflow-x:auto; border:1px solid #dee2e6; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                <table style="width:100%; border-collapse:collapse; text-align:left; font-size:0.9rem;">
                    <thead>
                        <tr style="background:#f8f9fa; border-bottom:2px solid #dee2e6;">
                            <th style="padding:10px 14px; font-weight:700; color:#495057;">Artifact Path</th>
                            <th style="padding:10px 14px; font-weight:700; color:#495057;">Format</th>
                            <th style="padding:10px 14px; font-weight:700; color:#495057;">Size</th>
                            <th style="padding:10px 14px; font-weight:700; color:#495057;">SHA-256</th>
                            <th style="padding:10px 14px; font-weight:700; color:#495057;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(artifact_rows) if artifact_rows else "<tr><td colspan='5' style='padding:20px; text-align:center;'>No artifacts found.</td></tr>"}
                    </tbody>
                </table>
            </div>
        </section>

        <!-- Extracted Findings Table -->
        <section style="margin-bottom:32px;">
            <h2 style="font-size:1.25rem; color:#0f172a; margin:0 0 12px 0;">Extracted Findings ({len(r.findings)})</h2>
            <div style="overflow-x:auto; border:1px solid #dee2e6; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                <table style="width:100%; border-collapse:collapse; text-align:left; font-size:0.9rem;">
                    <thead>
                        <tr style="background:#f8f9fa; border-bottom:2px solid #dee2e6;">
                            <th style="padding:10px 14px; font-weight:700; color:#495057;">Finding</th>
                            <th style="padding:10px 14px; font-weight:700; color:#495057;">Category</th>
                            <th style="padding:10px 14px; font-weight:700; color:#495057;">Status</th>
                            <th style="padding:10px 14px; font-weight:700; color:#495057;">Extracted Value</th>
                            <th style="padding:10px 14px; font-weight:700; color:#495057;">Source</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(finding_rows) if finding_rows else "<tr><td colspan='5' style='padding:20px; text-align:center;'>No extractable findings.</td></tr>"}
                    </tbody>
                </table>
            </div>
        </section>

        <!-- Methodology & Safeguards -->
        <footer style="margin-top:36px; padding-top:20px; border-top:1px solid #e9ecef; font-size:0.85rem; color:#64748b;">
            <h3 style="font-size:0.95rem; color:#334155; margin:0 0 8px 0;">Methodology & Limitations</h3>
            <ul style="margin:0 0 12px 16px; padding:0;">
                {"".join(f"<li>{_esc(lim)}</li>" for lim in r.limitations)}
            </ul>
            <p style="margin:0;">
                Generated locally with AEGIS — strictly read-only, offline, and non-destructive.
            </p>
        </footer>
    </div>
</body>
</html>
"""
