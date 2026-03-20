"""HTML report templates for Okeanus intelligence reports.

Pure Python HTML generation — no external template engine dependency.
Each function returns a complete HTML document string.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Shared CSS / header / footer
# ---------------------------------------------------------------------------

REPORT_CSS = """
:root {
    --bg: #0a0e27;
    --surface: #131835;
    --surface2: #1a2040;
    --border: #2a3060;
    --text: #e0e6ff;
    --text-muted: #8892b0;
    --accent: #64ffda;
    --danger: #ff5370;
    --warning: #ffcb6b;
    --info: #82aaff;
    --success: #c3e88d;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 2rem;
}
.report-container { max-width: 1100px; margin: 0 auto; }
.report-header {
    border-bottom: 2px solid var(--accent);
    padding-bottom: 1.5rem;
    margin-bottom: 2rem;
}
.report-header h1 { font-size: 1.8rem; color: var(--accent); font-weight: 700; }
.report-header .subtitle { color: var(--text-muted); font-size: 0.9rem; margin-top: 0.3rem; }
.report-header .meta {
    display: flex; gap: 2rem; margin-top: 1rem;
    font-size: 0.85rem; color: var(--text-muted);
}
.meta-item { display: flex; align-items: center; gap: 0.4rem; }
.section { margin-bottom: 2rem; }
.section h2 {
    font-size: 1.2rem; color: var(--accent); font-weight: 600;
    margin-bottom: 1rem; padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
}
.section h3 { font-size: 1rem; color: var(--text); margin-bottom: 0.5rem; }
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.2rem;
    margin-bottom: 1rem;
}
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 1rem; }
.stat-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
}
.stat-value { font-size: 2rem; font-weight: 700; color: var(--accent); }
.stat-label { font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
}
th {
    background: var(--surface2);
    color: var(--accent);
    text-align: left;
    padding: 0.7rem 1rem;
    font-weight: 600;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
td {
    padding: 0.6rem 1rem;
    border-bottom: 1px solid var(--border);
}
tr:hover td { background: var(--surface2); }
.badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
}
.badge-low { background: rgba(195,232,141,0.15); color: var(--success); }
.badge-medium { background: rgba(255,203,107,0.15); color: var(--warning); }
.badge-high { background: rgba(255,83,112,0.15); color: var(--danger); }
.badge-critical { background: rgba(255,83,112,0.3); color: var(--danger); border: 1px solid var(--danger); }
.risk-meter {
    width: 100%;
    height: 8px;
    background: var(--surface2);
    border-radius: 4px;
    overflow: hidden;
    margin: 0.5rem 0;
}
.risk-meter-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
}
.risk-low { background: var(--success); }
.risk-medium { background: var(--warning); }
.risk-high { background: var(--danger); }
.risk-critical { background: var(--danger); }
.evidence-list { list-style: none; padding: 0; }
.evidence-list li {
    padding: 0.4rem 0 0.4rem 1.2rem;
    position: relative;
    color: var(--text-muted);
    font-size: 0.85rem;
}
.evidence-list li::before {
    content: '>';
    position: absolute;
    left: 0;
    color: var(--accent);
    font-weight: bold;
}
.footer {
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
    font-size: 0.75rem;
    color: var(--text-muted);
    text-align: center;
}
@media print {
    body { background: white; color: #1a1a2e; padding: 1rem; }
    .card, .stat-card { border-color: #ddd; background: #f8f9fa; }
    th { background: #e9ecef; color: #1a1a2e; }
    .report-header h1, .section h2, .stat-value { color: #0d6efd; }
}
"""


def _header(title: str, subtitle: str, meta_items: list[tuple[str, str]]) -> str:
    meta_html = "".join(
        f'<span class="meta-item">{label}: <strong>{value}</strong></span>'
        for label, value in meta_items
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{_esc(title)} — Okeanus Intelligence Report</title>
    <style>{REPORT_CSS}</style>
</head>
<body>
<div class="report-container">
    <div class="report-header">
        <h1>{_esc(title)}</h1>
        <div class="subtitle">{_esc(subtitle)}</div>
        <div class="meta">{meta_html}</div>
    </div>
"""


def _footer() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""
    <div class="footer">
        Generated by Okeanus Ocean Intelligence Platform &middot; {ts} &middot;
        CLASSIFICATION: UNCLASSIFIED
    </div>
</div>
</body>
</html>"""


def _badge(level: str) -> str:
    css_class = f"badge-{level.lower()}"
    return f'<span class="badge {css_class}">{_esc(level.upper())}</span>'


def _risk_meter(score: float, level: str) -> str:
    css_class = f"risk-{level.lower()}"
    return f"""<div class="risk-meter">
        <div class="risk-meter-fill {css_class}" style="width:{min(score, 100):.0f}%"></div>
    </div>"""


def _esc(s: str) -> str:
    """Basic HTML escaping."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# Report: Vessel Risk Assessment
# ---------------------------------------------------------------------------


def render_risk_report(score_data: dict[str, Any]) -> str:
    """Render a comprehensive vessel risk assessment report."""
    mmsi = score_data.get("mmsi", "Unknown")
    composite = score_data.get("composite_score", 0)
    level = score_data.get("risk_level", "low")
    factors = score_data.get("factors", [])
    summary = score_data.get("summary", "")
    vessel = score_data.get("vessel_info", {})

    html = _header(
        title=f"Vessel Risk Assessment — MMSI {mmsi}",
        subtitle=summary,
        meta_items=[
            ("MMSI", str(mmsi)),
            ("Score", f"{composite:.0f}/100"),
            ("Level", level.upper()),
            ("Generated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")),
        ],
    )

    # Composite score card
    html += f"""
    <div class="section">
        <h2>Composite Risk Score</h2>
        <div class="card" style="text-align:center;">
            <div class="stat-value" style="font-size:3rem;">{composite:.0f}</div>
            <div style="margin:0.5rem 0;">{_badge(level)}</div>
            {_risk_meter(composite, level)}
            <p style="color:var(--text-muted);font-size:0.85rem;margin-top:0.5rem;">
                Scale: 0 (no risk) — 100 (critical risk)
            </p>
        </div>
    </div>
    """

    # Factor breakdown
    html += '<div class="section"><h2>Risk Factor Breakdown</h2>'
    for factor in sorted(factors, key=lambda f: f.get("score", 0), reverse=True):
        fname = factor.get("name", "unknown")
        fscore = factor.get("score", 0)
        fweight = factor.get("weight", 0)
        fweighted = factor.get("weighted_score", 0)
        fevidence = factor.get("evidence", [])

        f_pct = fscore * 100
        f_level = "critical" if f_pct >= 75 else "high" if f_pct >= 50 else "medium" if f_pct >= 25 else "low"

        html += f"""
        <div class="card">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <h3>{_esc(fname.replace('_', ' ').title())}</h3>
                <div>{_badge(f_level)} <strong>{fscore:.0%}</strong></div>
            </div>
            {_risk_meter(f_pct, f_level)}
            <div style="display:flex;gap:2rem;font-size:0.8rem;color:var(--text-muted);margin:0.3rem 0;">
                <span>Weight: {fweight:.0%}</span>
                <span>Weighted contribution: {fweighted:.4f}</span>
            </div>
            <ul class="evidence-list">
                {''.join(f'<li>{_esc(e)}</li>' for e in fevidence)}
            </ul>
        </div>
        """

    html += "</div>"

    # Vessel info table (if available)
    if vessel:
        html += '<div class="section"><h2>Vessel Information</h2><div class="card"><table>'
        for k, v in vessel.items():
            if v is not None:
                html += f"<tr><td><strong>{_esc(k.replace('_', ' ').title())}</strong></td><td>{_esc(str(v))}</td></tr>"
        html += "</table></div></div>"

    html += _footer()
    return html


# ---------------------------------------------------------------------------
# Report: Vessel Profile
# ---------------------------------------------------------------------------


def render_vessel_profile(
    mmsi: int,
    vessel_info: dict[str, Any],
    risk_data: dict[str, Any] | None = None,
    trajectory_data: dict[str, Any] | None = None,
    voyage_data: dict[str, Any] | None = None,
    encounter_data: dict[str, Any] | None = None,
) -> str:
    """Render a comprehensive vessel profile report."""
    name = vessel_info.get("vessel_name", f"MMSI {mmsi}")
    flag = vessel_info.get("flag", "Unknown")

    html = _header(
        title=f"Vessel Profile — {_esc(str(name))}",
        subtitle=f"Comprehensive intelligence dossier for MMSI {mmsi}",
        meta_items=[
            ("MMSI", str(mmsi)),
            ("IMO", str(vessel_info.get("imo", "N/A"))),
            ("Flag", str(flag)),
            ("Type", str(vessel_info.get("ship_type_name", "Unknown"))),
        ],
    )

    # Identity card
    html += '<div class="section"><h2>Vessel Identity</h2><div class="card-grid">'
    id_fields = [
        ("MMSI", str(mmsi)),
        ("IMO", str(vessel_info.get("imo", "N/A"))),
        ("Name", str(vessel_info.get("vessel_name", "Unknown"))),
        ("Call Sign", str(vessel_info.get("call_sign", "N/A"))),
        ("Flag State", str(flag)),
        ("Ship Type", str(vessel_info.get("ship_type_name", "Unknown"))),
        ("Destination", str(vessel_info.get("destination", "N/A"))),
        ("Draught", f"{vessel_info.get('draught', 'N/A')} m"),
    ]
    for label, val in id_fields:
        html += f"""
        <div class="stat-card">
            <div class="stat-label">{_esc(label)}</div>
            <div style="font-size:1.1rem;font-weight:600;margin-top:0.3rem;">{_esc(val)}</div>
        </div>"""
    html += "</div></div>"

    # Risk summary (if available)
    if risk_data:
        composite = risk_data.get("composite_score", 0)
        level = risk_data.get("risk_level", "low")
        html += f"""
        <div class="section">
            <h2>Risk Assessment</h2>
            <div class="card">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div class="stat-value">{composite:.0f}/100</div>
                        <div>{_badge(level)}</div>
                    </div>
                    <div style="flex:1;margin-left:2rem;">
                        {_risk_meter(composite, level)}
                        <p style="font-size:0.85rem;color:var(--text-muted);">
                            {_esc(risk_data.get('summary', ''))}
                        </p>
                    </div>
                </div>
            </div>
        </div>
        """

    # Trajectory summary
    if trajectory_data and trajectory_data.get("segments"):
        summary = trajectory_data.get("behavior_summary", {})
        html += '<div class="section"><h2>Behavioral Analysis</h2><div class="card"><table>'
        html += "<tr><th>Behavior</th><th>Time</th><th>Percentage</th></tr>"
        for behavior, stats in summary.items():
            minutes = stats.get("minutes", 0)
            pct = stats.get("percentage", 0)
            html += f"<tr><td>{_esc(behavior.title())}</td><td>{minutes:.0f} min</td><td>{pct:.1f}%</td></tr>"
        html += "</table></div></div>"

    # Voyage history
    if voyage_data and voyage_data.get("voyages"):
        voyages = voyage_data["voyages"]
        html += '<div class="section"><h2>Voyage History</h2><div class="card"><table>'
        html += "<tr><th>#</th><th>Departure</th><th>Arrival</th><th>Distance</th><th>Avg Speed</th><th>Status</th></tr>"
        for i, v in enumerate(voyages[:20], 1):
            dep = v.get("departure", {})
            arr = v.get("arrival", {})
            html += f"""<tr>
                <td>{i}</td>
                <td>{_esc(str(dep.get('time', 'N/A'))[:16])}</td>
                <td>{_esc(str(arr.get('time', 'N/A'))[:16])}</td>
                <td>{v.get('distance_nm', 0):.1f} nm</td>
                <td>{v.get('avg_speed_kn', 0):.1f} kn</td>
                <td>{_badge('low' if v.get('status') == 'completed' else 'medium')}</td>
            </tr>"""
        html += "</table></div></div>"

    # Encounters
    if encounter_data and encounter_data.get("encounters"):
        enc_list = encounter_data["encounters"]
        html += '<div class="section"><h2>Recent Encounters</h2><div class="card"><table>'
        html += "<tr><th>Type</th><th>Other MMSI</th><th>Duration</th><th>Min Distance</th><th>Risk</th></tr>"
        for enc in enc_list[:20]:
            other = enc.get("mmsi_2") if enc.get("mmsi_1") == mmsi else enc.get("mmsi_1", "?")
            html += f"""<tr>
                <td>{_esc(str(enc.get('encounter_type', 'unknown')))}</td>
                <td>{other}</td>
                <td>{enc.get('duration_minutes', 0):.0f} min</td>
                <td>{enc.get('min_distance_nm', 0):.3f} nm</td>
                <td>{_badge(str(enc.get('risk_level', 'low')))}</td>
            </tr>"""
        html += "</table></div></div>"

    html += _footer()
    return html


# ---------------------------------------------------------------------------
# Report: Area Activity
# ---------------------------------------------------------------------------


def render_area_report(
    bbox: tuple[float, float, float, float],
    vessel_count: int,
    encounters: list[dict[str, Any]],
    risk_scores: list[dict[str, Any]],
    time_start: str,
    time_end: str,
) -> str:
    """Render an area activity intelligence report."""
    w, s, e, n = bbox

    html = _header(
        title="Area Activity Intelligence Report",
        subtitle=f"Maritime activity analysis for region {w:.2f},{s:.2f} to {e:.2f},{n:.2f}",
        meta_items=[
            ("Bounding Box", f"{w:.2f},{s:.2f},{e:.2f},{n:.2f}"),
            ("Period", f"{time_start[:10]} to {time_end[:10]}"),
            ("Vessels", str(vessel_count)),
        ],
    )

    # Summary stats
    high_risk = [r for r in risk_scores if r.get("risk_level") in ("high", "critical")]
    rendezvous = [e for e in encounters if e.get("encounter_type") == "rendezvous"]

    html += f"""
    <div class="section">
        <h2>Area Summary</h2>
        <div class="card-grid">
            <div class="stat-card">
                <div class="stat-value">{vessel_count}</div>
                <div class="stat-label">Vessels Detected</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(encounters)}</div>
                <div class="stat-label">Encounters</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(rendezvous)}</div>
                <div class="stat-label">Rendezvous Events</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(high_risk)}</div>
                <div class="stat-label">High-Risk Vessels</div>
            </div>
        </div>
    </div>
    """

    # High risk vessels
    if risk_scores:
        sorted_scores = sorted(risk_scores, key=lambda r: r.get("composite_score", 0), reverse=True)
        html += '<div class="section"><h2>Vessel Risk Rankings</h2><div class="card"><table>'
        html += "<tr><th>MMSI</th><th>Score</th><th>Level</th><th>Key Factors</th></tr>"
        for rs in sorted_scores[:25]:
            factors = rs.get("factors", [])
            top_factors = sorted(factors, key=lambda f: f.get("score", 0), reverse=True)[:2]
            factor_str = ", ".join(
                f"{f.get('name', '?')} ({f.get('score', 0):.0%})" for f in top_factors
            )
            html += f"""<tr>
                <td>{rs.get('mmsi', '?')}</td>
                <td><strong>{rs.get('composite_score', 0):.0f}</strong></td>
                <td>{_badge(str(rs.get('risk_level', 'low')))}</td>
                <td style="font-size:0.8rem;color:var(--text-muted);">{_esc(factor_str)}</td>
            </tr>"""
        html += "</table></div></div>"

    # Encounters
    if encounters:
        html += '<div class="section"><h2>Encounters Detected</h2><div class="card"><table>'
        html += "<tr><th>Type</th><th>Vessel A</th><th>Vessel B</th><th>Duration</th><th>Risk</th></tr>"
        for enc in encounters[:30]:
            html += f"""<tr>
                <td>{_esc(str(enc.get('encounter_type', '?')))}</td>
                <td>{enc.get('mmsi_1', '?')}</td>
                <td>{enc.get('mmsi_2', '?')}</td>
                <td>{enc.get('duration_minutes', 0):.0f} min</td>
                <td>{_badge(str(enc.get('risk_level', 'low')))}</td>
            </tr>"""
        html += "</table></div></div>"

    html += _footer()
    return html


# ---------------------------------------------------------------------------
# Report: Encounter Detail
# ---------------------------------------------------------------------------


def render_encounter_report(encounter: dict[str, Any]) -> str:
    """Render a detailed encounter analysis report."""
    etype = encounter.get("encounter_type", "unknown")
    mmsi1 = encounter.get("mmsi_1", "?")
    mmsi2 = encounter.get("mmsi_2", "?")
    risk = encounter.get("risk_level", "low")

    html = _header(
        title=f"Encounter Report — {etype.replace('_', ' ').title()}",
        subtitle=f"Vessel {mmsi1} and Vessel {mmsi2}",
        meta_items=[
            ("Type", etype.replace("_", " ").title()),
            ("Risk", risk.upper()),
            ("Duration", f"{encounter.get('duration_minutes', 0):.0f} min"),
            ("Min Distance", f"{encounter.get('min_distance_nm', 0):.3f} nm"),
        ],
    )

    # Encounter overview
    html += f"""
    <div class="section">
        <h2>Encounter Overview</h2>
        <div class="card-grid">
            <div class="stat-card">
                <div class="stat-label">Encounter Type</div>
                <div class="stat-value" style="font-size:1.5rem;">
                    {_esc(etype.replace('_', ' ').title())}
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Risk Level</div>
                <div style="margin-top:0.5rem;">{_badge(risk)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Duration</div>
                <div class="stat-value" style="font-size:1.5rem;">
                    {encounter.get('duration_minutes', 0):.0f} min
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Closest Approach</div>
                <div class="stat-value" style="font-size:1.5rem;">
                    {encounter.get('min_distance_nm', 0):.3f} nm
                </div>
            </div>
        </div>
    </div>
    """

    # Vessel details
    html += '<div class="section"><h2>Vessel Details</h2><div class="card"><table>'
    html += "<tr><th>Property</th><th>Vessel A</th><th>Vessel B</th></tr>"
    html += f"<tr><td>MMSI</td><td>{mmsi1}</td><td>{mmsi2}</td></tr>"
    html += f"""<tr><td>Mean SOG</td>
        <td>{encounter.get('mean_sog_1', 'N/A')} kn</td>
        <td>{encounter.get('mean_sog_2', 'N/A')} kn</td></tr>"""
    html += f"""<tr><td>Mean COG</td>
        <td>{encounter.get('mean_cog_1', 'N/A')}&deg;</td>
        <td>{encounter.get('mean_cog_2', 'N/A')}&deg;</td></tr>"""
    html += "</table></div></div>"

    # Risk indicators
    indicators = encounter.get("indicators", [])
    if indicators:
        html += '<div class="section"><h2>Risk Indicators</h2><div class="card">'
        html += '<ul class="evidence-list">'
        for ind in indicators:
            html += f"<li>{_esc(str(ind))}</li>"
        html += "</ul></div></div>"

    # Timeline
    start = encounter.get("start_time", "")
    end = encounter.get("end_time", "")
    if start or end:
        html += f"""
        <div class="section">
            <h2>Timeline</h2>
            <div class="card">
                <table>
                    <tr><td><strong>Start</strong></td><td>{_esc(str(start))}</td></tr>
                    <tr><td><strong>End</strong></td><td>{_esc(str(end))}</td></tr>
                    <tr><td><strong>Location</strong></td>
                        <td>{encounter.get('lat', 'N/A')}, {encounter.get('lon', 'N/A')}</td></tr>
                </table>
            </div>
        </div>
        """

    html += _footer()
    return html
