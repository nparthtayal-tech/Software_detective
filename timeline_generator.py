"""
TIMELINE GENERATOR — Interactive SVG/HTML timeline visualisation.

Takes a case_result dict (with master_timeline, conflict_graph_result,
pagerank_result, etc.) and produces a self-contained HTML file with:

• A horizontal timeline axis
• Perpendicular vertical stems ending in circles for each event
• Hover tooltips showing speaker, description, time, conflicts, corroborations
• Curved conflict arcs (red) and corroboration arcs (green)
• Speaker colour legend
• Graph theory metadata overlay
• Dark premium theme matching the existing report.html design language
"""

from __future__ import annotations

import html
import json
from typing import Any


# ---------------------------------------------------------------------------
# Colour palette for speakers — up to 10 unique speakers
# ---------------------------------------------------------------------------
_SPEAKER_COLOURS = [
    "#3b82f6",   # blue
    "#f59e0b",   # amber
    "#10b981",   # emerald
    "#ef4444",   # red
    "#8b5cf6",   # violet
    "#06b6d4",   # cyan
    "#ec4899",   # pink
    "#f97316",   # orange
    "#14b8a6",   # teal
    "#a855f7",   # purple
]


def _esc(text: Any) -> str:
    """HTML-escape helper."""
    return html.escape(str(text)) if text is not None else ""


def generate(case_result: dict[str, Any], output_path: str = "output/timeline.html") -> str:
    """
    Generate the interactive timeline HTML and write to *output_path*.

    Returns the HTML string.
    """
    timeline = case_result.get("master_timeline", [])
    if not timeline:
        raise ValueError("master_timeline is empty — nothing to render.")

    # Sort by time_start so the timeline is left-to-right chronological.
    timeline.sort(key=lambda e: e.get("time_start", "00:00"))

    # Build speaker → colour map.
    speakers_seen: list[str] = []
    for ev in timeline:
        name = ev.get("speaker_name", "Unknown")
        if name not in speakers_seen:
            speakers_seen.append(name)
    speaker_colour = {
        name: _SPEAKER_COLOURS[i % len(_SPEAKER_COLOURS)]
        for i, name in enumerate(speakers_seen)
    }

    # Layout constants.
    left_pad = 120
    right_pad = 120
    event_spacing = 180
    canvas_w = left_pad + right_pad + max(1, len(timeline) - 1) * event_spacing + 60
    axis_y = 420  # y-position of the horizontal line
    circle_r = 18
    stem_top = 160  # top of the tallest stem
    stem_bottom = axis_y

    # Pre-compute x positions.
    x_positions = [left_pad + i * event_spacing for i in range(len(timeline))]

    # Build quick lookup: event_full_id → index
    id_to_idx = {}
    for idx, ev in enumerate(timeline):
        id_to_idx[ev["event_full_id"]] = idx

    # ── SVG construction ──────────────────────────────────────────────
    svg_parts: list[str] = []

    # Defs: glow filter, gradient
    svg_parts.append(f"""
<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="720"
     id="timeline-svg" style="display:block;">
  <defs>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <linearGradient id="axisGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.1"/>
      <stop offset="50%" stop-color="#8b5cf6" stop-opacity="0.6"/>
      <stop offset="100%" stop-color="#06b6d4" stop-opacity="0.1"/>
    </linearGradient>
    <linearGradient id="stemGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="currentColor" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="currentColor" stop-opacity="0.2"/>
    </linearGradient>
  </defs>
""")

    # Horizontal axis line (the literal timeline).
    svg_parts.append(f"""
  <!-- Horizontal timeline axis -->
  <line x1="40" y1="{axis_y}" x2="{canvas_w - 40}" y2="{axis_y}"
        stroke="url(#axisGrad)" stroke-width="3" stroke-linecap="round"/>
  <line x1="40" y1="{axis_y}" x2="{canvas_w - 40}" y2="{axis_y}"
        stroke="rgba(255,255,255,0.08)" stroke-width="1"/>
""")

    # ── Conflict arcs (curved red dashed lines) ─────────────────────
    conflicts = case_result.get("cross_analysis", {}).get("conflicts", [])
    for conf in conflicts:
        a_id = conf.get("event_a_id", "")
        b_id = conf.get("event_b_id", "")
        if a_id in id_to_idx and b_id in id_to_idx:
            ax = x_positions[id_to_idx[a_id]]
            bx = x_positions[id_to_idx[b_id]]
            mid_x = (ax + bx) / 2
            arc_height = axis_y + 60 + abs(id_to_idx[a_id] - id_to_idx[b_id]) * 20
            desc = _esc(conf.get("description", ""))
            svg_parts.append(f"""
  <!-- Conflict arc: {a_id} ↔ {b_id} -->
  <path d="M {ax} {axis_y + 8} Q {mid_x} {arc_height} {bx} {axis_y + 8}"
        fill="none" stroke="#ef4444" stroke-width="2" stroke-dasharray="6 4"
        opacity="0.55" class="conflict-arc">
    <title>⚠ CONFLICT: {desc}</title>
  </path>
""")

    # ── Corroboration arcs (curved green lines) ──────────────────────
    corroborations = case_result.get("cross_analysis", {}).get("corroborations", [])
    for corr in corroborations:
        a_id = corr.get("event_a_id", "")
        b_id = corr.get("event_b_id", "")
        if a_id in id_to_idx and b_id in id_to_idx:
            ax = x_positions[id_to_idx[a_id]]
            bx = x_positions[id_to_idx[b_id]]
            mid_x = (ax + bx) / 2
            arc_height = stem_top - 30 - abs(id_to_idx[a_id] - id_to_idx[b_id]) * 15
            weight = corr.get("weight", 0)
            desc = _esc(corr.get("description", ""))
            svg_parts.append(f"""
  <!-- Corroboration arc: {a_id} ↔ {b_id} -->
  <path d="M {ax} {stem_top + circle_r + 8} Q {mid_x} {arc_height} {bx} {stem_top + circle_r + 8}"
        fill="none" stroke="#10b981" stroke-width="2" opacity="{0.35 + weight * 0.45:.2f}"
        class="corroboration-arc">
    <title>✓ CORROBORATION (w={weight}): {desc}</title>
  </path>
""")

    # ── Event markers: stems + circles + labels ──────────────────────
    for idx, ev in enumerate(timeline):
        x = x_positions[idx]
        full_id = ev["event_full_id"]
        speaker = ev.get("speaker_name", "Unknown")
        role = ev.get("speaker_role", "")
        colour = speaker_colour.get(speaker, "#888")
        desc = ev.get("description", "")
        t_start = ev.get("time_start", "??:??")
        t_end = ev.get("time_end", "??:??")
        location = ev.get("location", "")
        action = ev.get("action", "")
        status = ev.get("status", "single_source")
        in_set = ev.get("in_consistent_set", False)
        pr_score = ev.get("pagerank_score", 0)

        # Scale circle radius by PageRank (min 14, max 28).
        r = max(14, min(28, int(14 + pr_score * 70)))

        # Border style by status.
        dash = ""
        if status == "contested":
            dash = 'stroke-dasharray="5 3"'
        elif status == "single_source":
            dash = 'stroke-dasharray="2 2"'

        # Stem: vertical line from axis up to the circle.
        # Alternate above/below for clarity if events are dense — but keep above.
        cy = stem_top + (idx % 3) * 30  # stagger slightly

        svg_parts.append(f"""
  <!-- Event: {full_id} -->
  <g class="event-group" data-id="{_esc(full_id)}" style="cursor:pointer;">
    <!-- Stem -->
    <line x1="{x}" y1="{axis_y}" x2="{x}" y2="{cy + r + 4}"
          stroke="{colour}" stroke-width="2" opacity="0.45" stroke-dasharray="4 3"/>
    <!-- Tick on axis -->
    <line x1="{x}" y1="{axis_y - 6}" x2="{x}" y2="{axis_y + 6}"
          stroke="{colour}" stroke-width="2.5" opacity="0.7"/>
    <!-- Circle -->
    <circle cx="{x}" cy="{cy}" r="{r}" fill="{colour}" fill-opacity="0.15"
            stroke="{colour}" stroke-width="2.5" {dash} filter="url(#glow)"
            class="event-circle"/>
    <!-- Inner dot -->
    <circle cx="{x}" cy="{cy}" r="4" fill="{colour}" opacity="0.9"/>
    <!-- Time label below axis -->
    <text x="{x}" y="{axis_y + 28}" text-anchor="middle"
          font-size="11" fill="#8b95a8" font-family="'JetBrains Mono', monospace">
      {_esc(t_start)}
    </text>
    <!-- Description label above circle -->
    <text x="{x}" y="{cy - r - 10}" text-anchor="middle"
          font-size="11" fill="#e8ecf4" font-weight="500"
          font-family="Inter, system-ui, sans-serif">
      {_esc(desc[:22])}
    </text>
  </g>
""")

    svg_parts.append("</svg>")
    svg_content = "\n".join(svg_parts)

    # ── Build tooltip data as JSON for the JS layer ──────────────────
    tooltip_data = {}
    for ev in timeline:
        fid = ev["event_full_id"]
        conf_list = ev.get("conflicts", [])
        corr_list = ev.get("corroborations", [])
        tooltip_data[fid] = {
            "speaker": ev.get("speaker_name", "Unknown"),
            "role": ev.get("speaker_role", ""),
            "description": ev.get("description", ""),
            "time": f"{ev.get('time_start', '??:??')} – {ev.get('time_end', '??:??')}",
            "location": ev.get("location", ""),
            "action": ev.get("action", ""),
            "status": ev.get("status", ""),
            "in_consistent_set": ev.get("in_consistent_set", False),
            "pagerank": round(ev.get("pagerank_score", 0), 4),
            "conflicts": [c.get("description", "") for c in conf_list],
            "corroborations": [c.get("description", "") for c in corr_list],
        }

    # ── Speaker legend ───────────────────────────────────────────────
    legend_items = ""
    for name in speakers_seen:
        col = speaker_colour[name]
        # Find the role
        role = ""
        for ev in timeline:
            if ev.get("speaker_name") == name:
                role = ev.get("speaker_role", "")
                break
        legend_items += f"""
        <div class="legend-item">
          <span class="legend-dot" style="background:{col};box-shadow:0 0 8px {col}55;"></span>
          <span class="legend-name">{_esc(name)}</span>
          <span class="legend-role">{_esc(role)}</span>
        </div>"""

    # ── Full HTML page ───────────────────────────────────────────────
    case_id = case_result.get("case_id", "CASE")
    incident = case_result.get("incident", "Investigation Timeline")
    mis_size = len(case_result.get("conflict_graph_result", {}).get("selected_statements", []))

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Timeline — {_esc(case_id)}</title>
<meta name="description" content="Interactive investigation timeline with graph theory analysis for {_esc(case_id)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
  --bg-primary: #06080f;
  --bg-secondary: #0c1220;
  --bg-card: rgba(14, 22, 40, 0.75);
  --bg-card-hover: rgba(20, 30, 55, 0.85);
  --border: rgba(255,255,255,0.06);
  --border-hover: rgba(255,255,255,0.12);
  --text-primary: #e8ecf4;
  --text-secondary: #8b95a8;
  --text-muted: #5a6478;
  --accent-blue: #3b82f6;
  --accent-purple: #8b5cf6;
  --accent-cyan: #06b6d4;
  --green: #10b981;
  --red: #ef4444;
  --amber: #f59e0b;
  --radius: 14px;
  --radius-sm: 8px;
  --shadow: 0 4px 24px rgba(0,0,0,0.35);
}}

* {{ margin:0; padding:0; box-sizing:border-box; }}

body {{
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.6;
  min-height: 100vh;
  background-image:
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(59,130,246,0.08), transparent),
    radial-gradient(ellipse 60% 40% at 80% 100%, rgba(139,92,246,0.06), transparent);
}}

#app {{
  max-width: 100%;
  margin: 0 auto;
  padding: 32px 24px 80px;
}}

/* ─── Header ─── */
.header {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 32px 40px;
  margin-bottom: 28px;
  backdrop-filter: blur(20px);
  position: relative;
  overflow: hidden;
}}
.header::before {{
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple), var(--accent-cyan));
}}
.header h1 {{
  font-size: 24px; font-weight: 800;
  background: linear-gradient(135deg, #fff 30%, var(--accent-blue));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  margin-bottom: 4px;
}}
.header .case-id {{
  font-family: 'JetBrains Mono', monospace; font-size: 12px;
  color: var(--accent-blue); letter-spacing: 0.5px;
}}

/* ─── Legend ─── */
.legend {{
  display: flex; gap: 20px; flex-wrap: wrap;
  margin-bottom: 24px; padding: 16px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  backdrop-filter: blur(20px);
}}
.legend-title {{
  font-size: 12px; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 1px;
  width: 100%; margin-bottom: 4px;
}}
.legend-item {{
  display: flex; align-items: center; gap: 8px; font-size: 13px;
}}
.legend-dot {{
  width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0;
}}
.legend-name {{ color: var(--text-primary); font-weight: 500; }}
.legend-role {{
  color: var(--text-muted); font-size: 11px;
  background: rgba(255,255,255,0.04); padding: 2px 8px;
  border-radius: 20px; border: 1px solid var(--border);
}}

/* ─── Status Legend ─── */
.status-legend {{
  display: flex; gap: 24px; flex-wrap: wrap;
  margin-bottom: 24px; padding: 14px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  backdrop-filter: blur(20px);
  font-size: 12px; color: var(--text-secondary);
}}
.status-item {{
  display: flex; align-items: center; gap: 8px;
}}
.status-line {{
  width: 28px; height: 0; border-top: 2.5px solid var(--text-secondary);
}}
.status-line.dashed {{ border-top-style: dashed; }}
.status-line.dotted {{ border-top-style: dotted; }}
.status-line.conflict {{ border-color: var(--red); border-top-style: dashed; }}
.status-line.corrob {{ border-color: var(--green); }}

/* ─── Timeline container ─── */
.timeline-container {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 32px 20px;
  overflow-x: auto;
  backdrop-filter: blur(20px);
  position: relative;
}}

/* ─── Tooltip ─── */
#tooltip {{
  display: none;
  position: fixed;
  z-index: 1000;
  background: rgba(10, 16, 30, 0.96);
  border: 1px solid var(--border-hover);
  border-radius: var(--radius-sm);
  padding: 16px 20px;
  min-width: 280px;
  max-width: 380px;
  backdrop-filter: blur(24px);
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  pointer-events: none;
  animation: tooltipIn 0.15s ease-out;
}}
@keyframes tooltipIn {{
  from {{ opacity: 0; transform: translateY(6px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}
#tooltip .tt-speaker {{
  font-size: 15px; font-weight: 700; margin-bottom: 2px;
}}
#tooltip .tt-role {{
  font-size: 11px; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.5px;
  margin-bottom: 10px;
}}
#tooltip .tt-desc {{
  font-size: 13px; font-weight: 500; color: var(--text-primary);
  margin-bottom: 8px;
}}
#tooltip .tt-row {{
  display: flex; gap: 8px; font-size: 12px; color: var(--text-secondary);
  margin-bottom: 4px;
}}
#tooltip .tt-label {{
  color: var(--text-muted); min-width: 70px; font-weight: 500;
}}
#tooltip .tt-conflict {{
  font-size: 11px; color: var(--red); margin-top: 8px;
  padding: 6px 10px; background: rgba(239,68,68,0.08);
  border-radius: 6px; border-left: 3px solid var(--red);
}}
#tooltip .tt-corrob {{
  font-size: 11px; color: var(--green); margin-top: 6px;
  padding: 6px 10px; background: rgba(16,185,129,0.08);
  border-radius: 6px; border-left: 3px solid var(--green);
}}
#tooltip .tt-badge {{
  display: inline-block; font-size: 10px; padding: 2px 8px;
  border-radius: 20px; font-weight: 600; margin-top: 8px;
}}
#tooltip .tt-badge.in-set {{
  background: rgba(16,185,129,0.12); color: var(--green);
  border: 1px solid rgba(16,185,129,0.25);
}}
#tooltip .tt-badge.not-in-set {{
  background: rgba(239,68,68,0.12); color: var(--red);
  border: 1px solid rgba(239,68,68,0.25);
}}

/* ─── Hover effects ─── */
.event-group:hover .event-circle {{
  filter: url(#glow) brightness(1.3);
  transition: filter 0.2s;
}}
.event-circle {{ transition: filter 0.2s ease; }}

/* ─── Header Layout & Nav ─── */
.header {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px 32px;
  margin-bottom: 24px;
  backdrop-filter: blur(20px);
  position: relative;
  overflow: hidden;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}}
.header::before {{
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple), var(--accent-cyan));
}}
.header-actions {{
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}}
.btn-nav {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  background: rgba(255,255,255,0.06);
  border: 1px solid var(--border);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}}
.btn-nav:hover {{
  background: rgba(255,255,255,0.12);
  border-color: var(--border-hover);
  transform: translateY(-1px);
}}
.btn-nav-primary {{
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
  color: #fff;
  border: none;
  box-shadow: 0 2px 10px rgba(59,130,246,0.3);
}}
.btn-nav-primary:hover {{
  box-shadow: 0 4px 16px rgba(59,130,246,0.5);
}}
.sync-indicator {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(16,185,129,0.1);
  color: #10b981;
  border: 1px solid rgba(16,185,129,0.25);
  font-family: 'JetBrains Mono', monospace;
}}
.sync-indicator .dot {{
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}}

/* ─── Graph Info Cards ─── */
.info-cards {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px; margin-top: 28px;
}}
.info-card {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px 24px;
  backdrop-filter: blur(20px);
}}
.info-card .card-title {{
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;
}}
.info-card .card-value {{
  font-size: 28px; font-weight: 800;
  background: linear-gradient(135deg, #fff 30%, var(--accent-blue));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}
.info-card .card-sub {{
  font-size: 12px; color: var(--text-secondary); margin-top: 4px;
}}
</style>
</head>
<body>
<div id="app">

  <!-- Header with Coordinated Controls -->
  <div class="header">
    <div>
      <div class="case-id">{_esc(case_id)}</div>
      <h1 id="page-title">🔍 {_esc(incident)}</h1>
    </div>
    <div class="header-actions">
      <div class="sync-indicator" id="sync-pill"><span class="dot"></span> Coordinated Tab</div>
      <button class="btn-nav" onclick="location.reload()" title="Refresh Timeline data">🔄 Refresh</button>
      <a href="/" class="btn-nav btn-nav-primary" title="Open Case Input Form">📝 Case Input</a>
      <a href="/output/report.html" class="btn-nav" target="_blank" title="View Full Report">📋 Report</a>
    </div>
  </div>

  <!-- Speaker Legend -->
  <div class="legend">
    <div class="legend-title">Speakers</div>
    {legend_items}
  </div>

  <!-- Status Legend -->
  <div class="status-legend">
    <div class="status-item">
      <div class="status-line"></div> Corroborated
    </div>
    <div class="status-item">
      <div class="status-line dashed"></div> Contested
    </div>
    <div class="status-item">
      <div class="status-line dotted"></div> Single Source
    </div>
    <div class="status-item">
      <div class="status-line conflict"></div> Conflict Arc
    </div>
    <div class="status-item">
      <div class="status-line corrob"></div> Corroboration Arc
    </div>
  </div>

  <!-- Timeline -->
  <div class="timeline-container" id="timeline-container">
    {svg_content}
  </div>

  <!-- Info Cards -->
  <div class="info-cards">
    <div class="info-card">
      <div class="card-title">Total Events</div>
      <div class="card-value">{len(timeline)}</div>
      <div class="card-sub">Across {len(speakers_seen)} speakers</div>
    </div>
    <div class="info-card">
      <div class="card-title">Conflicts Detected</div>
      <div class="card-value" style="-webkit-text-fill-color:var(--red);">{len(conflicts)}</div>
      <div class="card-sub">Cross-statement contradictions</div>
    </div>
    <div class="info-card">
      <div class="card-title">Corroborations</div>
      <div class="card-value" style="-webkit-text-fill-color:var(--green);">{len(corroborations)}</div>
      <div class="card-sub">Cross-statement agreements</div>
    </div>
    <div class="info-card">
      <div class="card-title">Consistent Set (MIS)</div>
      <div class="card-value">{mis_size}</div>
      <div class="card-sub">Conflict-free events</div>
    </div>
  </div>

</div>

<!-- Tooltip element -->
<div id="tooltip"></div>

<script>
// Tooltip data injected from Python.
const tooltipData = {json.dumps(tooltip_data, ensure_ascii=False)};

const tooltip = document.getElementById('tooltip');
const groups = document.querySelectorAll('.event-group');

groups.forEach(g => {{
  g.addEventListener('mouseenter', (e) => {{
    const id = g.getAttribute('data-id');
    const d = tooltipData[id];
    if (!d) return;

    let html = `<div class="tt-speaker" style="color:${{getColour(d.speaker)}}">${{d.speaker}}</div>`;
    html += `<div class="tt-role">${{d.role}}</div>`;
    html += `<div class="tt-desc">${{d.description}}</div>`;
    html += `<div class="tt-row"><span class="tt-label">Time</span>${{d.time}}</div>`;
    html += `<div class="tt-row"><span class="tt-label">Location</span>${{d.location || '—'}}</div>`;
    html += `<div class="tt-row"><span class="tt-label">Action</span>${{d.action || '—'}}</div>`;
    html += `<div class="tt-row"><span class="tt-label">Status</span>${{d.status.replace(/_/g, ' ')}}</div>`;
    html += `<div class="tt-row"><span class="tt-label">PageRank</span>${{d.pagerank.toFixed(4)}}</div>`;

    if (d.conflicts && d.conflicts.length) {{
      d.conflicts.forEach(c => {{
        html += `<div class="tt-conflict">⚠ ${{c}}</div>`;
      }});
    }}
    if (d.corroborations && d.corroborations.length) {{
      d.corroborations.forEach(c => {{
        html += `<div class="tt-corrob">✓ ${{c}}</div>`;
      }});
    }}

    html += d.in_consistent_set
      ? `<span class="tt-badge in-set">✓ In Consistent Set</span>`
      : `<span class="tt-badge not-in-set">✗ Excluded by MIS</span>`;

    tooltip.innerHTML = html;
    tooltip.style.display = 'block';
  }});

  g.addEventListener('mousemove', (e) => {{
    const pad = 16;
    let x = e.clientX + pad;
    let y = e.clientY + pad;
    const rect = tooltip.getBoundingClientRect();
    if (x + rect.width > window.innerWidth - pad) x = e.clientX - rect.width - pad;
    if (y + rect.height > window.innerHeight - pad) y = e.clientY - rect.height - pad;
    tooltip.style.left = x + 'px';
    tooltip.style.top = y + 'px';
  }});

  g.addEventListener('mouseleave', () => {{
    tooltip.style.display = 'none';
  }});
}});

// Speaker colour map (must match Python).
const speakerColours = {json.dumps(speaker_colour, ensure_ascii=False)};

function getColour(name) {{
  return speakerColours[name] || '#888';
}}

// ─── Cross-Tab Live Coordination with Case Input Form ───
function showUpdateNotification() {{
  let notif = document.getElementById('live-update-toast');
  if (!notif) {{
    notif = document.createElement('div');
    notif.id = 'live-update-toast';
    notif.style.cssText = 'position:fixed;top:24px;right:24px;z-index:99999;background:rgba(12,20,36,0.95);border:1px solid #10b981;color:#fff;padding:14px 20px;border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,0.6);display:flex;align-items:center;gap:14px;backdrop-filter:blur(16px);font-size:13px;font-family:Inter,sans-serif;';
    notif.innerHTML = `
      <span style="display:flex;align-items:center;gap:8px;font-weight:600;color:#10b981;">
        <span style="font-size:18px;">⚡</span> Pipeline updated! New timeline ready.
      </span>
      <button onclick="location.reload()" style="background:#10b981;color:#fff;border:none;padding:6px 14px;border-radius:8px;font-weight:700;cursor:pointer;font-size:12px;">Reload Now</button>
      <button onclick="this.parentElement.remove()" style="background:transparent;border:none;color:#8b95a8;cursor:pointer;font-size:16px;">✕</button>
    `;
    document.body.appendChild(notif);
  }}
}}

const syncChannel = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('investigation_channel') : null;
if (syncChannel) {{
  syncChannel.onmessage = (e) => {{
    if (e.data && (e.data.type === 'PIPELINE_COMPLETE' || e.data.type === 'CASE_SAVED')) {{
      showUpdateNotification();
    }}
  }};
}}
window.addEventListener('storage', (e) => {{
  if (e.key === 'investigation_last_run' || e.key === 'investigation_case_saved') {{
    showUpdateNotification();
  }}
}});
</script>
</body>
</html>"""

    # Write to file.
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    return full_html
