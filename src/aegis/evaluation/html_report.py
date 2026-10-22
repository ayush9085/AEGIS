"""Self-contained, offline HTML report generator for AEGIS research evaluations."""

from __future__ import annotations

import html

from aegis.evaluation.models import EvaluationReport


def render_evaluation_html_report(report: EvaluationReport) -> str:
    """Render self-contained HTML document with zero external CDNs, scripts, or fonts."""
    m = report.metrics
    safe_aegis_ver = html.escape(report.aegis_version or "0.1.0")
    safe_commit = html.escape(report.git_commit or "unknown")
    safe_date = html.escape(report.evaluated_at_utc or "unknown")
    safe_schema = html.escape(report.schema_version)
    safe_corpus = html.escape(report.corpus_version)
    safe_repro_hash = html.escape(report.reproducibility_hash[:16])

    status_color = "#10b981" if m.failed == 0 else "#ef4444"
    status_label = "ALL CASES PASSED" if m.failed == 0 else f"{m.failed} FAILURES"

    # Category Breakdown Rows
    cat_rows: list[str] = []
    for cat, cm in sorted(m.category_breakdown.items()):
        badge_cls = "badge-pass" if cm.failed == 0 else "badge-fail"
        rate_pct = f"{cm.pass_rate * 100:.1f}%"
        cat_rows.append(
            f"""
            <tr>
                <td><strong>{html.escape(cat)}</strong></td>
                <td>{cm.total_cases}</td>
                <td style="color: #10b981; font-weight: 600;">{cm.passed}</td>
                <td style="color: #ef4444; font-weight: 600;">{cm.failed}</td>
                <td><span class="{badge_cls}">{rate_pct}</span></td>
            </tr>
            """
        )

    # Rule Coverage Rows
    rule_rows: list[str] = []
    for r_id, rm in sorted(m.rule_metrics.items()):
        agr_pct = f"{rm.agreement_rate * 100:.1f}%"
        rule_rows.append(
            f"""
            <tr>
                <td><code>{html.escape(r_id)}</code></td>
                <td>{html.escape(rm.rule_version)}</td>
                <td>{rm.cases_evaluated}</td>
                <td><strong>{agr_pct}</strong></td>
                <td style="font-size: 0.85rem; color: #94a3b8;">
                    sup: <span style="color:#10b981;">{rm.supported_count}</span> |
                    in-ev: <span style="color:#f59e0b;">{rm.insufficient_evidence_count}</span> |
                    cont: <span style="color:#ef4444;">{rm.contradicted_count}</span> |
                    na: <span style="color:#64748b;">{rm.not_applicable_count}</span>
                </td>
            </tr>
            """
        )

    # Binary Confusion Matrices
    cm_sections: list[str] = []
    for r_id, rm in sorted(m.rule_metrics.items()):
        cm = rm.confusion_matrix
        if not cm:
            continue
        prec_str = f"{cm.precision * 100:.1f}%" if cm.precision is not None else "N/A"
        rec_str = f"{cm.recall * 100:.1f}%" if cm.recall is not None else "N/A"
        f1_str = f"{cm.f1_score:.3f}" if cm.f1_score is not None else "N/A"
        cm_sections.append(
            f"""
            <div class="card" style="margin-bottom: 1.25rem;">
                <h4 style="margin-top: 0; color: #38bdf8;">Rule: <code>{html.escape(r_id)}</code></h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 1rem; margin-bottom: 0.75rem;">
                    <div class="stat-box"><span class="stat-num">{cm.true_positives}</span><span class="stat-lbl">True Positives (TP)</span></div>
                    <div class="stat-box"><span class="stat-num">{cm.false_positives}</span><span class="stat-lbl">False Positives (FP)</span></div>
                    <div class="stat-box"><span class="stat-num">{cm.true_negatives}</span><span class="stat-lbl">True Negatives (TN)</span></div>
                    <div class="stat-box"><span class="stat-num">{cm.false_negatives}</span><span class="stat-lbl">False Negatives (FN)</span></div>
                </div>
                <div style="display: flex; gap: 1.5rem; font-size: 0.9rem; color: #cbd5e1; background: #0f172a; padding: 0.6rem 1rem; border-radius: 6px;">
                    <div><strong>Precision:</strong> {prec_str}</div>
                    <div><strong>Recall:</strong> {rec_str}</div>
                    <div><strong>F1 Score:</strong> {f1_str}</div>
                </div>
                <p style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.5rem; margin-bottom: 0;">{html.escape(cm.notes)}</p>
            </div>
            """
        )

    # Execution Log Cards
    case_cards: list[str] = []
    for res in report.results:
        badge_cls = "badge-pass" if res.status == "passed" else "badge-fail"
        case_cards.append(
            f"""
            <div class="case-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div>
                        <strong style="color: #f1f5f9; font-size: 0.95rem;">{html.escape(res.case_id)}</strong>
                        <span style="color: #94a3b8; font-size: 0.8rem; margin-left: 0.5rem;">({html.escape(res.category)})</span>
                    </div>
                    <div>
                        <span class="{badge_cls}">{html.escape(res.status.upper())}</span>
                        <span style="color: #64748b; font-size: 0.8rem; margin-left: 0.5rem;">{res.execution_time_ms} ms</span>
                    </div>
                </div>
                <div style="font-size: 0.85rem; color: #cbd5e1;">{html.escape(res.message)}</div>
            </div>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AEGIS Phase 5 Research Evaluation Report</title>
    <style>
        :root {{
            --bg: #0b0f19;
            --surface: #131b2e;
            --surface-border: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.15);
            --pass: #10b981;
            --fail: #ef4444;
            --warning: #f59e0b;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-primary);
            margin: 0;
            padding: 2rem;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--surface-border);
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
        }}
        h1 {{
            margin: 0 0 0.5rem 0;
            font-size: 1.8rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .meta-pill {{
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}
        .status-badge {{
            background: {status_color};
            color: #ffffff;
            font-weight: 700;
            font-size: 0.85rem;
            padding: 0.4rem 0.9rem;
            border-radius: 9999px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .grid-summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 8px;
            padding: 1.25rem;
        }}
        .stat-box {{
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 6px;
            padding: 0.75rem;
            text-align: center;
        }}
        .stat-num {{
            display: block;
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
        }}
        .stat-lbl {{
            display: block;
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
        }}
        .card h3 {{
            margin-top: 0;
            margin-bottom: 1rem;
            font-size: 1.15rem;
            color: var(--accent);
            border-bottom: 1px solid var(--surface-border);
            padding-bottom: 0.5rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}
        th, td {{
            text-align: left;
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--surface-border);
        }}
        th {{
            color: var(--text-secondary);
            font-weight: 600;
            background: rgba(15, 23, 42, 0.6);
        }}
        .badge-pass {{
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.8rem;
        }}
        .badge-fail {{
            background: rgba(239, 68, 68, 0.15);
            color: #ef4444;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.8rem;
        }}
        .case-card {{
            background: #0f172a;
            border: 1px solid var(--surface-border);
            border-radius: 6px;
            padding: 0.9rem 1.1rem;
            margin-bottom: 0.75rem;
        }}
        .banner-warning {{
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: 8px;
            padding: 1rem 1.25rem;
            margin-bottom: 2rem;
            color: #fde68a;
            font-size: 0.85rem;
        }}
        code {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            background: rgba(0, 0, 0, 0.3);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            color: #38bdf8;
            font-size: 0.85em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>🛡️ AEGIS Evaluation &amp; Reproducibility Report</h1>
                <div class="meta-pill">
                    AEGIS v{safe_aegis_ver} &bull; Commit: <code>{safe_commit}</code> &bull; Schema: <code>{safe_schema}</code> &bull; Corpus: <code>{safe_corpus}</code> &bull; Evaluated: {safe_date}
                </div>
            </div>
            <div>
                <span class="status-badge">{status_label}</span>
            </div>
        </header>

        <div class="banner-warning">
            <strong>⚠️ SCIENTIFIC RESEARCH &amp; METHODOLOGICAL NOTICE</strong><br>
            This evaluation report documents automated verification across a curated ground-truth corpus.
            Metrics measure internal software determinism and rule logic consistency. They do NOT represent
            hardware-backed cryptographic attestation, real-world exploit detection rates, or guarantees against
            compromise on unverified Android hardware.
        </div>

        <div class="grid-summary">
            <div class="card stat-box">
                <span class="stat-num">{m.total_cases}</span>
                <span class="stat-lbl">Total Cases</span>
            </div>
            <div class="card stat-box">
                <span class="stat-num" style="color: #10b981;">{m.passed}</span>
                <span class="stat-lbl">Passed</span>
            </div>
            <div class="card stat-box">
                <span class="stat-num" style="color: #ef4444;">{m.failed}</span>
                <span class="stat-lbl">Failed</span>
            </div>
            <div class="card stat-box">
                <span class="stat-num" style="color: #38bdf8;">{m.overall_pass_rate * 100:.1f}%</span>
                <span class="stat-lbl">Pass Rate</span>
            </div>
            <div class="card stat-box">
                <span class="stat-num" style="color: #a78bfa;">{m.reproducibility_rate * 100:.1f}%</span>
                <span class="stat-lbl">Reproducibility</span>
            </div>
            <div class="card stat-box">
                <span class="stat-num" style="color: #f59e0b;">{m.security_robustness_rejection_rate * 100:.1f}%</span>
                <span class="stat-lbl">Robustness</span>
            </div>
        </div>

        <div class="card" style="margin-bottom: 2rem;">
            <h3>📂 Results by Evaluation Category</h3>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Cases</th>
                        <th>Passed</th>
                        <th>Failed</th>
                        <th>Pass Rate</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(cat_rows)}
                </tbody>
            </table>
        </div>

        <div class="card" style="margin-bottom: 2rem;">
            <h3>🔬 Research Rule Coverage &amp; Agreement</h3>
            <table>
                <thead>
                    <tr>
                        <th>Rule ID</th>
                        <th>Version</th>
                        <th>Cases</th>
                        <th>Agreement Rate</th>
                        <th>Outcome Distribution</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rule_rows)}
                </tbody>
            </table>
        </div>

        {'<div class="card" style="margin-bottom: 2rem;"><h3>📊 Binary Confusion Matrices</h3>' + ''.join(cm_sections) + '</div>' if cm_sections else ''}

        <div class="card" style="margin-bottom: 2rem;">
            <h3>📋 Detailed Case Execution Log ({len(report.results)} Cases)</h3>
            {''.join(case_cards)}
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem;">
            <div class="card">
                <h3>📌 Known Limitations</h3>
                <ul style="font-size: 0.85rem; color: var(--text-secondary); padding-left: 1.25rem;">
                    {''.join(f'<li>{html.escape(lim)}</li>' for lim in report.known_limitations)}
                </ul>
            </div>
            <div class="card">
                <h3>🔍 Threats to Validity</h3>
                <ul style="font-size: 0.85rem; color: var(--text-secondary); padding-left: 1.25rem;">
                    {''.join(f'<li>{html.escape(ttv)}</li>' for ttv in report.threats_to_validity)}
                </ul>
            </div>
        </div>

        <footer style="border-top: 1px solid var(--surface-border); padding-top: 1.5rem; font-size: 0.8rem; color: var(--text-secondary); text-align: center;">
            AEGIS Phase 5 Research Evaluation Suite &bull; Reproducibility Hash: <code>{safe_repro_hash}</code> &bull; Pure Offline Execution
        </footer>
    </div>
</body>
</html>
"""
