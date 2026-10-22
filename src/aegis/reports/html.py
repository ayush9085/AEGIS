"""Self-contained, accessible HTML report generator with strict escaping and zero remote assets."""

from __future__ import annotations

import html
from typing import Any

from aegis.schema import EvidenceReport

STATUS_COLORS = {
    "observed": ("#0f5132", "#d1e7dd"),        # Dark green text, light green bg
    "unsupported": ("#664d03", "#fff3cd"),     # Amber text, light yellow bg
    "inaccessible": ("#842029", "#f8d7da"),    # Dark red text, light red bg
    "not_applicable": ("#41464b", "#e2e3e5"),  # Grey text, light grey bg
    "unknown": ("#495057", "#e9ecef"),         # Dark grey text, light grey bg
    "error": ("#842029", "#f8d7da"),           # Dark red text, light red bg
}


def _esc(val: Any) -> str:
    """Safely escape any value for embedding into HTML text or attribute."""
    if val is None:
        return ""
    return html.escape(str(val), quote=True)


def render_html_report(report: EvidenceReport) -> str:
    """Generate a clean, responsive, self-contained HTML report with zero external dependencies."""
    r = report
    dev = r.device
    coll = r.collection
    summary = r.summary

    # Prepare status badge markup
    def render_badge(status: str) -> str:
        s_clean = status.lower().strip()
        fg, bg = STATUS_COLORS.get(s_clean, ("#212529", "#e2e3e5"))
        return (
            f'<span style="display:inline-block; padding:3px 8px; font-size:0.75rem; '
            f'font-weight:600; text-transform:uppercase; border-radius:4px; '
            f'background-color:{bg}; color:{fg};">{_esc(s_clean)}</span>'
        )

    # Observations rows
    rows_html = []
    error_rows_html = []
    for obs in r.observations:
        cmd_str = " ".join(obs.source_command)
        badge = render_badge(obs.status)
        val_display = obs.value if obs.value is not None else f'<span style="color:#6c757d; font-style:italic;">{_esc(obs.error or "None")}</span>'
        if obs.value is not None:
            val_display = f"<code>{_esc(obs.value)}</code>"

        rows_html.append(
            f"""
            <tr>
                <td style="padding:10px 12px; font-weight:600; white-space:nowrap;">{_esc(obs.label)}<br><small style="color:#6c757d; font-weight:normal;">{_esc(obs.key)}</small></td>
                <td style="padding:10px 12px;">{val_display}</td>
                <td style="padding:10px 12px;">{badge}</td>
                <td style="padding:10px 12px; font-family:monospace; font-size:0.8rem; color:#495057;">{_esc(cmd_str)}</td>
                <td style="padding:10px 12px; font-size:0.85rem; color:#495057;">{_esc(obs.caveat)}</td>
            </tr>
            """
        )

        if obs.status in {"error", "inaccessible"}:
            error_rows_html.append(
                f"""
                <li style="margin-bottom:6px;">
                    <strong>{_esc(obs.label)}</strong> (<code>{_esc(obs.key)}</code>): {_esc(obs.error or "No details available")}
                </li>
                """
            )

    errors_section = ""
    if error_rows_html:
        errors_section = f"""
        <div style="background:#fff5f5; border:1px solid #fed7d7; border-radius:8px; padding:16px 20px; margin-bottom:24px;">
            <h3 style="margin-top:0; color:#c53030; font-size:1.1rem;">Inaccessible or Failed Probes</h3>
            <ul style="margin:0; padding-left:20px; font-size:0.9rem; color:#742a2a;">
                {"".join(error_rows_html)}
            </ul>
        </div>
        """

    limitations_items = "".join(f"<li style='margin-bottom:6px;'>{_esc(lim)}</li>" for lim in r.limitations)
    nongoals_items = "".join(f"<li style='margin-bottom:6px;'>{_esc(ng)}</li>" for ng in r.non_goals)

    if coll.is_synthetic:
        provenance_banner = """
        <div style="background:#fff3cd; border:2px solid #ffc107; color:#856404; padding:16px 20px; border-radius:8px; font-weight:700; font-size:1.05rem; text-align:center; margin-bottom:20px; letter-spacing:0.02em;">
            ⚠️ SYNTHETIC DEMO DATA — NOT COLLECTED FROM A PHYSICAL DEVICE
        </div>
        """
    else:
        provenance_banner = f"""
        <div style="background:#e8f4fd; border:2px solid #3b82f6; color:#1e40af; padding:14px 20px; border-radius:8px; font-size:0.95rem; margin-bottom:20px;">
            <strong>Real Device ADB Collection:</strong> Recorded from active Android handset at <code>{_esc(coll.timestamp_utc)}</code>. This report records observable properties and does not certify device security.
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AEGIS Evidence Report — {_esc(dev.model or dev.serial_redacted)}</title>
    <style>
        :root {{
            --bg: #f8fafc;
            --surface: #ffffff;
            --border: #e2e8f0;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --accent: #2563eb;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            padding: 32px 16px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            line-height: 1.5;
        }}
        .container {{
            max-width: 1080px;
            margin: 0 auto;
        }}
        header {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px 28px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .badge-notice {{
            display: inline-block;
            background: #eff6ff;
            color: #1d4ed8;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 9999px;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 12px;
        }}
        h1 {{
            margin: 0 0 6px 0;
            font-size: 1.75rem;
            font-weight: 700;
        }}
        .header-meta {{
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        }}
        .card h2 {{
            margin-top: 0;
            font-size: 1.05rem;
            font-weight: 600;
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
            margin-bottom: 12px;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            text-align: center;
        }}
        .stat-box {{
            padding: 10px;
            border-radius: 6px;
            background: #f1f5f9;
        }}
        .stat-num {{
            font-size: 1.35rem;
            font-weight: 700;
            display: block;
        }}
        .stat-lbl {{
            font-size: 0.7rem;
            text-transform: uppercase;
            color: var(--text-muted);
            font-weight: 600;
        }}
        .table-wrap {{
            overflow-x: auto;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            margin-bottom: 24px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.9rem;
        }}
        th {{
            background: #f8fafc;
            border-bottom: 2px solid var(--border);
            padding: 12px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }}
        tr:not(:last-child) td {{
            border-bottom: 1px solid var(--border);
        }}
        code {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.85em;
        }}
        .callout {{
            border-left: 4px solid var(--accent);
            background: #f0fdf4;
            border-color: #22c55e;
            padding: 14px 18px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 24px;
            font-size: 0.9rem;
        }}
        footer {{
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 32px;
        }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <span class="badge-notice">AEGIS Ground-Truth Evidence Report</span>
        <h1>{_esc(dev.manufacturer or "Android")} {_esc(dev.model or dev.product_name or "Device")}</h1>
        <div class="header-meta">
            Target Serial: <code>{_esc(dev.serial_redacted)}</code> &bull; 
            Collection Time: {_esc(coll.timestamp_utc)} &bull; 
            AEGIS v{_esc(r.tool.get("version", "unknown"))} &bull; 
            Schema v{_esc(r.schema_version)}
        </div>
    </header>

    {provenance_banner}

    <div class="callout">
        <strong>Security & Ground-Truth Principle:</strong>
        This report records observable system properties collected via read-only ADB commands.
        <strong>No overall 'secure' badge is granted.</strong> Individual checks document the reported system state alongside relevant limitations and verification caveats.
    </div>

    <div class="grid">
        <div class="card">
            <h2>Device Identity & Build</h2>
            <table style="width:100%; font-size:0.85rem;">
                <tr><td style="color:var(--text-muted); width:130px; padding:4px 0;">Manufacturer:</td><td><strong>{_esc(dev.manufacturer or "Unknown")}</strong></td></tr>
                <tr><td style="color:var(--text-muted); padding:4px 0;">Model:</td><td><strong>{_esc(dev.model or "Unknown")}</strong></td></tr>
                <tr><td style="color:var(--text-muted); padding:4px 0;">Android Release:</td><td><strong>{_esc(dev.android_version or "Unknown")}</strong> (API {_esc(dev.sdk_version or "?")})</td></tr>
                <tr><td style="color:var(--text-muted); padding:4px 0;">Patch Level:</td><td><code>{_esc(dev.security_patch or "Unknown")}</code></td></tr>
                <tr><td style="color:var(--text-muted); padding:4px 0;">Build ID:</td><td><code>{_esc(dev.build_id or "Unknown")}</code></td></tr>
                <tr><td style="color:var(--text-muted); padding:4px 0;">Fingerprint:</td><td style="word-break:break-all;"><code>{_esc(dev.fingerprint or "Unknown")}</code></td></tr>
            </table>
        </div>

        <div class="card">
            <h2>Collection Status Summary</h2>
            <div class="stat-grid">
                <div class="stat-box"><span class="stat-num" style="color:#0f5132;">{summary.observed}</span><span class="stat-lbl">Observed</span></div>
                <div class="stat-box"><span class="stat-num" style="color:#664d03;">{summary.unsupported}</span><span class="stat-lbl">Unsupported</span></div>
                <div class="stat-box"><span class="stat-num" style="color:#842029;">{summary.inaccessible}</span><span class="stat-lbl">Inaccessible</span></div>
                <div class="stat-box"><span class="stat-num" style="color:#41464b;">{summary.not_applicable}</span><span class="stat-lbl">Not Applicable</span></div>
                <div class="stat-box"><span class="stat-num" style="color:#495057;">{summary.unknown}</span><span class="stat-lbl">Unknown</span></div>
                <div class="stat-box"><span class="stat-num" style="color:#842029;">{summary.error}</span><span class="stat-lbl">Errors</span></div>
            </div>
            <div style="margin-top:14px; font-size:0.8rem; color:var(--text-muted); text-align:center;">
                Total Probes Evaluated: <strong>{summary.total}</strong> &bull; Consent Verified: <strong>{_esc(coll.consent_given)}</strong>
            </div>
        </div>
    </div>

    {errors_section}

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Evidence Probe</th>
                    <th>Observed Value</th>
                    <th>Status</th>
                    <th>Source Command</th>
                    <th>Limitation / Caveat</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows_html)}
            </tbody>
        </table>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Scope Limitations</h2>
            <ul style="font-size:0.85rem; padding-left:18px; margin:0; color:#334155;">
                {limitations_items}
            </ul>
        </div>
        <div class="card">
            <h2>Non-Goals</h2>
            <ul style="font-size:0.85rem; padding-left:18px; margin:0; color:#334155;">
                {nongoals_items}
            </ul>
        </div>
    </div>

    <div class="card" style="margin-top:16px;">
        <h2>Audit & Provenance Metadata</h2>
        <div style="font-size:0.85rem; color:#475569; display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:8px;">
            <div><strong>Host Platform:</strong> {_esc(coll.host_os)}</div>
            <div><strong>Host Python:</strong> {_esc(coll.host_python)}</div>
            <div><strong>Host ADB Version:</strong> {_esc(coll.host_adb_version or "Unknown")}</div>
            <div><strong>Method:</strong> {_esc(coll.method)}</div>
            <div><strong>Scope:</strong> {_esc(coll.scope)}</div>
            <div><strong>Consent Confirmed:</strong> {_esc(coll.consent_given)}</div>
        </div>
    </div>

    <footer>
        AEGIS &bull; Android Execution, Ground-Truth Inspection & Security &bull; Open-Source Research Toolkit
    </footer>
</div>
</body>
</html>
"""
    return html_content
