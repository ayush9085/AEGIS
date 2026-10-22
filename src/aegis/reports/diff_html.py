"""Self-contained, accessible HTML diff report generator for AEGIS snapshots."""

from __future__ import annotations

import html
from typing import Any

from aegis.diff import SemanticDiff

CLASSIFICATION_STYLES = {
    "unchanged": ("#0f5132", "#d1e7dd", "Unchanged"),
    "value_changed": ("#084298", "#cfe2ff", "Value Changed"),
    "status_changed": ("#664d03", "#fff3cd", "Status Changed"),
    "added": ("#0f5132", "#d1e7dd", "Added"),
    "removed": ("#842029", "#f8d7da", "Removed"),
    "incomparable": ("#41464b", "#e2e3e5", "Incomparable"),
}


def _esc(val: Any) -> str:
    """Safely escape any value for HTML text or attributes."""
    if val is None:
        return ""
    return html.escape(str(val), quote=True)


def render_html_diff_report(diff: SemanticDiff) -> str:
    """Generate self-contained HTML comparison report with strict escaping and zero remote assets."""
    d = diff
    s = d.summary

    # Classification badge helper
    def render_class_badge(classification: str) -> str:
        fg, bg, label = CLASSIFICATION_STYLES.get(
            classification, ("#212529", "#e2e3e5", classification.title())
        )
        return (
            f'<span style="display:inline-block; padding:3px 8px; font-size:0.75rem; '
            f'font-weight:700; text-transform:uppercase; border-radius:4px; '
            f'background-color:{bg}; color:{fg};">{_esc(label)}</span>'
        )

    # Status pill helper
    def render_status_pill(status: str | None) -> str:
        if not status:
            return '<span style="color:#6c757d; font-style:italic;">None</span>'
        return (
            f'<span style="display:inline-block; padding:1px 6px; font-size:0.7rem; '
            f'font-weight:600; border-radius:3px; background:#e9ecef; color:#495057;">{_esc(status)}</span>'
        )

    # Value formatting helper
    def format_val(val: Any, raw: str | None) -> str:
        if val is None:
            return '<span style="color:#adb5bd; font-style:italic;">(none)</span>'
        display = _esc(val)
        return f'<code style="font-family:ui-monospace,Menlo,Consolas,monospace; word-break:break-all;">{display}</code>'

    # Rows generation
    diff_rows = []
    for item in d.changes:
        badge = render_class_badge(item.classification)
        old_val_html = format_val(item.old_value, item.old_raw_value)
        new_val_html = format_val(item.new_value, item.new_raw_value)
        old_status_html = render_status_pill(item.old_status)
        new_status_html = render_status_pill(item.new_status)

        # Highlight row background slightly if changed
        row_bg = "#ffffff"
        if item.classification == "value_changed":
            row_bg = "#f0f7ff"
        elif item.classification == "status_changed":
            row_bg = "#fffdf0"
        elif item.classification == "added":
            row_bg = "#f4fdf8"
        elif item.classification == "removed":
            row_bg = "#fdf5f5"

        diff_rows.append(
            f"""
            <tr style="background:{row_bg}; border-bottom:1px solid #e9ecef;">
                <td style="padding:12px 14px; font-weight:600; white-space:nowrap; vertical-align:top;">
                    {_esc(item.label)}<br>
                    <code style="font-size:0.75rem; color:#6c757d; font-weight:normal;">{_esc(item.key)}</code>
                </td>
                <td style="padding:12px 14px; vertical-align:top;">{badge}</td>
                <td style="padding:12px 14px; vertical-align:top; font-size:0.9rem;">
                    <div>{old_val_html}</div>
                    <div style="margin-top:4px;">{old_status_html}</div>
                </td>
                <td style="padding:12px 14px; vertical-align:top; font-size:0.9rem;">
                    <div>{new_val_html}</div>
                    <div style="margin-top:4px;">{new_status_html}</div>
                </td>
                <td style="padding:12px 14px; vertical-align:top; font-size:0.85rem; color:#495057;">
                    {_esc(item.explanation)}
                    {f'<br><small style="color:#856404; font-style:italic;">{_esc(item.caveat)}</small>' if item.caveat else ''}
                </td>
            </tr>
            """
        )

    # Empty state if no differences found
    total_changes = s.value_changed + s.status_changed + s.added + s.removed + s.incomparable
    if total_changes == 0:
        table_content = f"""
        <div style="text-align:center; padding:48px 24px; background:#f8f9fa; border:1px solid #dee2e6; border-radius:8px; margin:20px 0;">
            <div style="font-size:2.5rem; margin-bottom:12px;">✅</div>
            <h3 style="margin:0 0 8px 0; color:#198754; font-size:1.3rem;">Identical Snapshots — Zero Differences Detected</h3>
            <p style="margin:0; color:#6c757d; font-size:0.95rem;">
                All {s.unchanged} observations have identical statuses and values across both snapshots.
            </p>
        </div>
        """
    else:
        table_content = f"""
        <div style="overflow-x:auto; border:1px solid #dee2e6; border-radius:8px; margin:20px 0; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
            <table style="width:100%; border-collapse:collapse; text-align:left; font-size:0.9rem;">
                <thead>
                    <tr style="background:#f8f9fa; border-bottom:2px solid #dee2e6;">
                        <th style="padding:12px 14px; font-weight:700; color:#495057;">Observation Key</th>
                        <th style="padding:12px 14px; font-weight:700; color:#495057;">Classification</th>
                        <th style="padding:12px 14px; font-weight:700; color:#495057;">Baseline Snapshot</th>
                        <th style="padding:12px 14px; font-weight:700; color:#495057;">Current Snapshot</th>
                        <th style="padding:12px 14px; font-weight:700; color:#495057;">Semantic Analysis</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(diff_rows)}
                </tbody>
            </table>
        </div>
        """

    # Provenance banners
    provenance_banners = []
    if d.is_cross_device_override:
        provenance_banners.append(
            """
            <div style="background:#fff3cd; border:2px solid #ffc107; color:#664d03; padding:16px 20px; border-radius:8px; margin-bottom:20px; font-size:0.95rem;">
                <strong>⚠️ Cross-Device Comparison Override Active:</strong> This diff compares snapshots from two different devices or firmware streams. Differences reflect architectural/OEM divergence rather than state changes on a single handset.
            </div>
            """
        )
    elif d.comparability_state == "identity_unverified":
        provenance_banners.append(
            """
            <div style="background:#e2e3e5; border:1px solid #d3d6d8; color:#41464b; padding:14px 20px; border-radius:8px; margin-bottom:20px; font-size:0.95rem;">
                <strong>Notice (Identity Unverified):</strong> One or both snapshots lack sufficient identity fields to verify device parity. Comparisons are performed based on matching observation keys.
            </div>
            """
        )

    if d.baseline_is_synthetic or d.current_is_synthetic:
        synthetic_note = []
        if d.baseline_is_synthetic:
            synthetic_note.append("Baseline snapshot uses synthetic fixture data")
        if d.current_is_synthetic:
            synthetic_note.append("Current snapshot uses synthetic fixture data")
        note_str = " & ".join(synthetic_note)
        provenance_banners.append(
            f"""
            <div style="background:#fff3cd; border:1px solid #ffe69c; color:#856404; padding:12px 20px; border-radius:8px; font-weight:600; margin-bottom:20px; font-size:0.9rem;">
                🧪 Synthetic Evidence Alert: {note_str}. Not collected from a live physical phone.
            </div>
            """
        )

    # Device descriptions
    def dev_label(dev: dict[str, Any]) -> str:
        parts = [dev.get("manufacturer") or "", dev.get("model") or ""]
        name = " ".join(p for p in parts if p).strip() or "Unknown Device"
        if dev.get("android_version"):
            name += f" (Android {dev.get('android_version')})"
        return name

    b_dev_str = dev_label(d.baseline_device)
    c_dev_str = dev_label(d.current_device)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AEGIS Semantic Comparison Report</title>
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
                        <span>🛡️</span> AEGIS Semantic Diff Report
                    </h1>
                    <p style="margin:6px 0 0 0; color:#64748b; font-size:0.95rem;">
                        Deterministic comparison of Android evidence snapshots (Diff Schema v{_esc(d.diff_version)})
                    </p>
                </div>
                <div style="text-align:right;">
                    <span style="display:inline-block; padding:4px 10px; border-radius:6px; font-size:0.8rem; font-weight:700; text-transform:uppercase; background:{'#d1e7dd' if d.comparability_state == 'match' else '#fff3cd'}; color:{'#0f5132' if d.comparability_state == 'match' else '#664d03'};">
                        {_esc(d.comparability_state.replace('_', ' '))}
                    </span>
                </div>
            </div>
        </header>

        <!-- Provenance Banners -->
        {"".join(provenance_banners)}

        <!-- Snapshots Compared Grid -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:20px; margin-bottom:28px;">
            <!-- Baseline -->
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:18px;">
                <div style="font-size:0.75rem; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px;">
                    Baseline Snapshot (Old)
                </div>
                <div style="font-size:1.15rem; font-weight:700; color:#0f172a; margin-bottom:8px;">
                    {_esc(b_dev_str)}
                </div>
                <div style="font-size:0.85rem; color:#475569; display:grid; gap:4px;">
                    <div><strong>Snapshot ID:</strong> <code>{_esc(d.baseline_id)}</code></div>
                    <div><strong>Content Hash:</strong> <code style="word-break:break-all;">{_esc(d.baseline_hash)}</code></div>
                    <div><strong>Source Time:</strong> {_esc(d.baseline_timestamp)}</div>
                    <div><strong>Provenance:</strong> {'🧪 Synthetic' if d.baseline_is_synthetic else '📱 Physical Handset'}</div>
                </div>
            </div>

            <!-- Current -->
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:18px;">
                <div style="font-size:0.75rem; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px;">
                    Current Snapshot (New)
                </div>
                <div style="font-size:1.15rem; font-weight:700; color:#0f172a; margin-bottom:8px;">
                    {_esc(c_dev_str)}
                </div>
                <div style="font-size:0.85rem; color:#475569; display:grid; gap:4px;">
                    <div><strong>Snapshot ID:</strong> <code>{_esc(d.current_id)}</code></div>
                    <div><strong>Content Hash:</strong> <code style="word-break:break-all;">{_esc(d.current_hash)}</code></div>
                    <div><strong>Source Time:</strong> {_esc(d.current_timestamp)}</div>
                    <div><strong>Provenance:</strong> {'🧪 Synthetic' if d.current_is_synthetic else '📱 Physical Handset'}</div>
                </div>
            </div>
        </div>

        <!-- Metrics Cards -->
        <div style="display:flex; flex-wrap:wrap; gap:12px; margin-bottom:28px;">
            <div class="metric-card">
                <div class="metric-val" style="color:#0f172a;">{s.unchanged}</div>
                <div class="metric-label">Unchanged</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color:#0284c7;">{s.value_changed}</div>
                <div class="metric-label">Value Changed</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color:#d97706;">{s.status_changed}</div>
                <div class="metric-label">Status Changed</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color:#16a34a;">{s.added}</div>
                <div class="metric-label">Added</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color:#dc2626;">{s.removed}</div>
                <div class="metric-label">Removed</div>
            </div>
        </div>

        <!-- Diff Table -->
        <section>
            <h2 style="font-size:1.25rem; color:#0f172a; margin:0 0 12px 0;">Observation Changes & Analysis</h2>
            {table_content}
        </section>

        <!-- Methodology & Safeguards -->
        <footer style="margin-top:36px; padding-top:20px; border-top:1px solid #e9ecef; font-size:0.85rem; color:#64748b;">
            <h3 style="font-size:0.95rem; color:#334155; margin:0 0 8px 0;">Methodology & Limitations</h3>
            <p style="margin:0 0 6px 0;">
                AEGIS semantic diffing is deterministic and based on unprivileged userspace properties collected over ADB.
                Changes in observed values (e.g. security patches or verified boot flags) document configuration drift but do not independently establish hardware root-of-trust authenticity or compromise.
            </p>
            <p style="margin:0;">
                Generated locally with AEGIS — strictly read-only, consent-gated, and privacy-preserving.
            </p>
        </footer>
    </div>
</body>
</html>
"""
