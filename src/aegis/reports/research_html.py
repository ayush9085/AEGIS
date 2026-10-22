"""Self-contained, offline HTML report generator for AEGIS evidence-linked research."""

from __future__ import annotations

import html
import json
from typing import Any

from aegis.research.models import ResearchReport


def _escape(val: Any) -> str:
    """Strictly HTML escape a value for safe interpolation."""
    if val is None:
        return ""
    if isinstance(val, (dict, list)):
        return html.escape(json.dumps(val, indent=1, ensure_ascii=False), quote=True)
    return html.escape(str(val), quote=True)


def _badge(outcome_or_certainty: str) -> str:
    oc = outcome_or_certainty.lower()
    color_map = {
        "supported": ("#10b981", "#064e3b", "✓ Supported"),
        "directly_observed": ("#10b981", "#064e3b", "Directly Observed"),
        "strongly_supported": ("#3b82f6", "#1e3a8a", "Strongly Supported"),
        "tentatively_supported": ("#06b6d4", "#164e63", "Tentatively Supported"),
        "insufficient_evidence": ("#f59e0b", "#78350f", "Insufficient Evidence"),
        "contradicted": ("#ef4444", "#7f1d1d", "✗ Contradicted"),
        "conflicting_evidence": ("#ef4444", "#7f1d1d", "⚠ Conflicting Evidence"),
        "incomparable": ("#a855f7", "#581c87", "Incomparable"),
        "not_applicable": ("#64748b", "#1e293b", "Not Applicable"),
        "error": ("#ef4444", "#7f1d1d", "Error"),
    }
    fg, bg, label = color_map.get(oc, ("#94a3b8", "#1e293b", outcome_or_certainty))
    return f'<span style="display:inline-block;padding:2px 8px;font-size:0.75rem;font-weight:600;border-radius:4px;color:{fg};background:{bg};border:1px solid {fg}40;">{_escape(label)}</span>'


def render_html_research_report(report: ResearchReport) -> str:
    """Render a fully self-contained, offline HTML report from a ResearchReport."""
    summary = report.summary
    claims = report.claims
    evals = report.evaluations
    sources = report.source_inputs
    conflicts = report.conflicts
    missing_inv = report.missing_evidence_inventory
    graph = report.graph

    # Check synthetic provenance presence
    has_synth = any(s.get("provenance") == "synthetic" for s in sources)
    has_conflicts = len(conflicts) > 0

    # Build Claims HTML
    claims_html = []
    for c in claims:
        supp_badges = "".join(f'<code class="tag tag-supp">{_escape(eid)}</code> ' for eid in c.supporting_evidence_ids) or '<span class="text-muted">None</span>'
        contra_badges = "".join(f'<code class="tag tag-contra">{_escape(eid)}</code> ' for eid in c.contradicting_evidence_ids) or '<span class="text-muted">None</span>'
        assump_html = "".join(f"<li>{_escape(a)}</li>" for a in c.assumptions) or "<li>None documented</li>"
        limit_html = "".join(f"<li>{_escape(l)}</li>" for l in c.limitations) or "<li>None</li>"

        claims_html.append(f"""
        <div class="card claim-card">
          <div class="card-header">
            <div class="claim-title-row">
              <span class="claim-title">{_escape(c.title)}</span>
              <div>{_badge(c.certainty)}</div>
            </div>
            <div class="claim-cat text-muted">Category: {_escape(c.category)} &bull; Rule: <code>{_escape(c.evaluating_rule_id)}</code></div>
          </div>
          <div class="card-body">
            <p class="claim-summary">{_escape(c.summary)}</p>
            <div class="evidence-trace-box">
              <div class="trace-row"><strong>Supporting Evidence:</strong> {supp_badges}</div>
              <div class="trace-row"><strong>Contradicting Evidence:</strong> {contra_badges}</div>
            </div>
            <div class="details-grid">
              <div>
                <span class="sub-label">Assumptions:</span>
                <ul class="sub-list">{assump_html}</ul>
              </div>
              <div>
                <span class="sub-label">Known Limitations:</span>
                <ul class="sub-list">{limit_html}</ul>
              </div>
            </div>
          </div>
        </div>
        """)

    # Build Evaluations HTML
    evals_html = []
    for e in evals:
        inputs_html = "<br>".join(f"<code>{_escape(i)}</code>" for i in e.input_evidence_ids[:4])
        if len(e.input_evidence_ids) > 4:
            inputs_html += f"<br><span class='text-muted'>+{len(e.input_evidence_ids)-4} more</span>"
        if not inputs_html:
            inputs_html = "<span class='text-muted'>None</span>"

        prereq_sat = ", ".join(f"<code>{_escape(k)}</code>" for k in e.prerequisites_satisfied[:3]) or "<span class='text-muted'>None</span>"
        prereq_mis = ", ".join(f"<code class='text-warn'>{_escape(k)}</code>" for k in e.prerequisites_missing[:3]) or "<span class='text-muted'>None</span>"

        evals_html.append(f"""
        <tr>
          <td><strong>{_escape(e.rule_id)}</strong><br><span class="text-muted" style="font-size:0.75rem;">v{_escape(e.rule_version)}</span></td>
          <td>{_badge(e.outcome)}</td>
          <td>{_badge(e.certainty)}</td>
          <td>{inputs_html}</td>
          <td>
            <div style="font-size:0.8rem;"><strong>Satisfied:</strong> {prereq_sat}</div>
            <div style="font-size:0.8rem;margin-top:4px;"><strong>Missing:</strong> {prereq_mis}</div>
          </td>
          <td>
            <div>{_escape(e.conclusion)}</div>
            <div class="text-muted" style="font-size:0.75rem;margin-top:4px;">{_escape(e.explanation)}</div>
          </td>
        </tr>
        """)

    # Build Conflicts HTML
    conflicts_html = []
    for cf in conflicts:
        srcs = "".join(
            f"<li><code>{_escape(s['source_ref'])}</code> ({_escape(s['provenance'])}): <strong>{_escape(s['value'])}</strong></li>"
            for s in cf.get("evidence_sources", [])
        )
        conflicts_html.append(f"""
        <div class="conflict-item">
          <div class="conflict-header">⚠ Field Discrepancy: <code>{_escape(cf['key'])}</code> ({_escape(cf['label'])})</div>
          <p class="text-muted" style="margin:4px 0 8px 0;font-size:0.85rem;">Conflicting values detected across sources:</p>
          <ul style="margin:0;padding-left:20px;font-size:0.85rem;">{srcs}</ul>
        </div>
        """)
    conflicts_block = "".join(conflicts_html) or '<p class="text-muted">No cross-source direct value contradictions detected.</p>'

    # Build Missing Evidence HTML
    missing_badges = "".join(f'<code class="tag tag-warn">{_escape(m)}</code> ' for m in missing_inv) or '<span class="text-muted">All standard baseline observations present.</span>'

    # Build Sources HTML
    sources_html = []
    for s in sources:
        fp = s.get("device_fingerprint") or {}
        fp_str = f"{_escape(fp.get('manufacturer', ''))} {_escape(fp.get('model', ''))} (Android {_escape(fp.get('android_version', ''))})" if fp else '<span class="text-muted">N/A</span>'
        hash_str = f"<code>{_escape(s.get('content_hash', ''))[:16]}...</code>" if s.get("content_hash") else '<span class="text-muted">None</span>'

        sources_html.append(f"""
        <tr>
          <td><code>{_escape(s.get('source_ref'))}</code></td>
          <td><span class="badge-neutral">{_escape(s.get('source_type'))}</span></td>
          <td>{_badge(s.get('provenance', 'unknown'))}</td>
          <td>{hash_str}</td>
          <td>{fp_str}</td>
        </tr>
        """)

    # Build Graph Topology Overview
    node_type_counts: dict[str, int] = {}
    for n in graph.nodes:
        node_type_counts[n.node_type] = node_type_counts.get(n.node_type, 0) + 1

    graph_pills = "".join(
        f'<span class="graph-pill"><strong>{_escape(k)}</strong>: {v}</span>'
        for k, v in sorted(node_type_counts.items())
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AEGIS Research Intelligence Report</title>
  <style>
    :root {{
      --bg: #090d16;
      --card-bg: #111827;
      --border: #1f2937;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --accent: #3b82f6;
      --warn: #f59e0b;
      --danger: #ef4444;
      --success: #10b981;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 24px;
      line-height: 1.5;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 16px;
      margin-bottom: 24px;
    }}
    h1 {{ font-size: 1.5rem; margin: 0; font-weight: 700; letter-spacing: -0.025em; }}
    .subtitle {{ color: var(--text-muted); font-size: 0.875rem; margin-top: 4px; }}
    .alert-banner {{
      padding: 12px 16px;
      border-radius: 6px;
      margin-bottom: 20px;
      font-size: 0.875rem;
      border-left: 4px solid;
    }}
    .alert-warn {{ background: #78350f25; border-color: var(--warn); color: #fde68a; }}
    .alert-danger {{ background: #7f1d1d25; border-color: var(--danger); color: #fca5a5; }}
    .alert-info {{ background: #1e3a8a25; border-color: var(--accent); color: #bfdbfe; }}
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .metric-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }}
    .metric-value {{ font-size: 1.75rem; font-weight: 700; color: #fff; margin-top: 4px; }}
    .metric-label {{ font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600; }}
    .section-title {{ font-size: 1.25rem; font-weight: 600; margin: 32px 0 16px 0; }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      margin-bottom: 16px;
      overflow: hidden;
    }}
    .claim-card {{ border-left: 4px solid var(--accent); }}
    .card-header {{ padding: 16px; border-bottom: 1px solid var(--border); }}
    .claim-title-row {{ display: flex; justify-content: space-between; align-items: center; }}
    .claim-title {{ font-size: 1.1rem; font-weight: 600; color: #fff; }}
    .card-body {{ padding: 16px; }}
    .claim-summary {{ font-size: 0.95rem; margin-top: 0; margin-bottom: 16px; color: #e5e7eb; }}
    .evidence-trace-box {{
      background: #0d131f;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 12px;
      margin-bottom: 16px;
      font-size: 0.85rem;
    }}
    .trace-row {{ margin-bottom: 6px; }}
    .trace-row:last-child {{ margin-bottom: 0; }}
    .tag {{
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.75rem;
      margin-right: 4px;
      margin-bottom: 4px;
    }}
    .tag-supp {{ background: #064e3b; color: #a7f3d0; border: 1px solid #10b98140; }}
    .tag-contra {{ background: #7f1d1d; color: #fecaca; border: 1px solid #ef444440; }}
    .tag-warn {{ background: #78350f; color: #fde68a; border: 1px solid #f59e0b40; }}
    .details-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; font-size: 0.85rem; }}
    .sub-label {{ font-weight: 600; color: var(--text-muted); text-transform: uppercase; font-size: 0.7rem; }}
    .sub-list {{ margin: 4px 0 0 0; padding-left: 20px; color: #d1d5db; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
    th, td {{ padding: 12px 14px; text-align: left; border-bottom: 1px solid var(--border); vertical-align: top; }}
    th {{ background: #131c2e; font-weight: 600; color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; }}
    .text-muted {{ color: var(--text-muted); }}
    .text-warn {{ color: var(--warn); }}
    .badge-neutral {{ display: inline-block; padding: 2px 6px; font-size: 0.75rem; border-radius: 4px; background: #1f2937; color: #9ca3af; }}
    .conflict-item {{
      background: #7f1d1d15;
      border: 1px solid #ef444440;
      border-radius: 6px;
      padding: 12px;
      margin-bottom: 12px;
    }}
    .conflict-header {{ font-weight: 600; color: #fca5a5; }}
    .graph-pill {{
      display: inline-block;
      padding: 4px 10px;
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 9999px;
      font-size: 0.8rem;
      margin-right: 8px;
      margin-bottom: 8px;
    }}
    footer {{
      margin-top: 48px;
      border-top: 1px solid var(--border);
      padding-top: 20px;
      font-size: 0.8rem;
      color: var(--text-muted);
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>🔬 AEGIS Research Intelligence Report</h1>
        <div class="subtitle">Evidence-Linked Boot-Chain Traceability &bull; Evaluated: {_escape(report.evaluated_at_utc)}</div>
      </div>
      <div>
        <span class="badge-neutral">AEGIS v{_escape(report.aegis_version)}</span>
        <span class="badge-neutral" style="margin-left:6px;">Schema v{_escape(report.schema_version)}</span>
      </div>
    </header>

    <div class="alert-banner alert-info">
      <strong>Research & Traceability Engine</strong>: This report correlates evidence across live device reconnaissance, snapshots, diffs, and firmware artifacts. Findings document verified evidence traces and explicit limitations; they do not constitute a binary security verdict or hardware-backed attestation.
    </div>

    {'<div class="alert-banner alert-warn"><strong>Synthetic Data Notice</strong>: Analysis incorporates synthetic mock fixtures. Results must not be interpreted as physical device security measurements.</div>' if has_synth else ''}
    {'<div class="alert-banner alert-danger"><strong>Contradictions Detected</strong>: Cross-source value discrepancies exist between correlated inputs. See Conflicts section below.</div>' if has_conflicts else ''}

    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-label">Derived Claims</div>
        <div class="metric-value" style="color:var(--accent);">{summary.get('total_claims', 0)}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Evaluated Rules</div>
        <div class="metric-value">{summary.get('total_evaluations', 0)}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Direct Conflicts</div>
        <div class="metric-value" style="color:{'var(--danger)' if has_conflicts else 'var(--success)'};">{summary.get('total_conflicts', 0)}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Evidence Graph</div>
        <div class="metric-value">{summary.get('graph_nodes_count', 0)} <span style="font-size:0.9rem;font-weight:400;color:var(--text-muted);">nodes / {summary.get('graph_edges_count', 0)} edges</span></div>
      </div>
    </div>

    <div class="section-title">Derived Research Claims ({len(claims)})</div>
    <div>
      {''.join(claims_html) if claims_html else '<p class="text-muted">No derived claims generated for supplied evidence.</p>'}
    </div>

    <div class="section-title">Rule Evaluations ({len(evals)})</div>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th>Rule ID</th>
            <th>Outcome</th>
            <th>Certainty</th>
            <th>Input Evidence</th>
            <th>Prerequisites</th>
            <th>Conclusion</th>
          </tr>
        </thead>
        <tbody>
          {''.join(evals_html)}
        </tbody>
      </table>
    </div>

    <div class="section-title">Evidence Graph Topology ({len(graph.nodes)} Nodes, {len(graph.edges)} Edges)</div>
    <div class="card" style="padding:16px;">
      <div style="margin-bottom:12px;">{graph_pills}</div>
      <div class="text-muted" style="font-size:0.85rem;">All graph nodes and edges have verified referential integrity. Every derived claim traces directly back to contributing raw evidence items.</div>
    </div>

    <div class="section-title">Conflicts & Observation Surface Gaps</div>
    <div class="card" style="padding:16px;">
      <h3 style="margin-top:0;font-size:1rem;color:#fca5a5;">Cross-Source Discrepancies</h3>
      {conflicts_block}
      <h3 style="margin-top:20px;font-size:1rem;color:#fde68a;">Missing / Unobserved Standard Indicators</h3>
      <div>{missing_badges}</div>
    </div>

    <div class="section-title">Correlated Sources ({len(sources)})</div>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th>Source Reference</th>
            <th>Type</th>
            <th>Provenance</th>
            <th>Content Hash</th>
            <th>Device Context</th>
          </tr>
        </thead>
        <tbody>
          {''.join(sources_html)}
        </tbody>
      </table>
    </div>

    <div class="section-title">Core Research Limitations</div>
    <div class="card" style="padding:16px;">
      <ul style="margin:0;padding-left:20px;font-size:0.875rem;color:#d1d5db;">
        {''.join(f'<li>{_escape(lim)}</li>' for lim in report.limitations)}
      </ul>
    </div>

    <footer>
      Generated by AEGIS v{_escape(report.aegis_version)} &bull; Deterministic &bull; Offline &bull; Zero External Network Calls
    </footer>
  </div>
</body>
</html>
"""
