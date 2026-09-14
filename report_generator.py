"""
Report Generator — Produces a premium interactive HTML investigation report.

Takes the consolidated pipeline JSON output and writes a single self-contained
HTML file with embedded CSS and JavaScript.
"""
from __future__ import annotations
import json
from pathlib import Path


def generate_report(data: dict, output_path: str) -> None:
    """Generate an interactive HTML report from pipeline results."""
    json_blob = json.dumps(data, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Investigation Report — {_esc(data.get('case_id',''))}</title>
<meta name="description" content="Multi-statement forensic investigation report with timeline, conflict analysis, and credibility assessment.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
{_css()}
</style>
</head>
<body>
<div id="app"></div>
<script>
const CASE_DATA = {json_blob};
{_js()}
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _css() -> str:
    return """
:root {
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
  --green-bg: rgba(16,185,129,0.08);
  --red-bg: rgba(239,68,68,0.08);
  --amber-bg: rgba(245,158,11,0.08);
  --radius: 14px;
  --radius-sm: 8px;
  --shadow: 0 4px 24px rgba(0,0,0,0.35);
}

* { margin:0; padding:0; box-sizing:border-box; }

body {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.6;
  min-height: 100vh;
  background-image:
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(59,130,246,0.08), transparent),
    radial-gradient(ellipse 60% 40% at 80% 100%, rgba(139,92,246,0.06), transparent);
}

#app { max-width: 1280px; margin: 0 auto; padding: 32px 24px 80px; }

/* ─── Header ─── */
.case-header {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 40px 48px;
  margin-bottom: 32px;
  backdrop-filter: blur(20px);
  position: relative;
  overflow: hidden;
}
.case-header::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple), var(--accent-cyan));
}
.case-header h1 {
  font-size: 28px; font-weight: 800;
  background: linear-gradient(135deg, #fff 30%, var(--accent-blue));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  margin-bottom: 6px;
}
.case-header .case-id {
  font-family: 'JetBrains Mono', monospace; font-size: 13px;
  color: var(--accent-blue); margin-bottom: 16px; letter-spacing: 0.5px;
}
.case-header .meta { color: var(--text-secondary); font-size: 14px; }
.stats-row {
  display: flex; gap: 16px; margin-top: 24px; flex-wrap: wrap;
}
.stat-chip {
  background: rgba(255,255,255,0.04); border: 1px solid var(--border);
  border-radius: 40px; padding: 8px 20px; font-size: 13px; font-weight: 500;
  display: flex; align-items: center; gap: 8px;
}
.stat-chip .num { font-weight: 700; font-size: 16px; }
.stat-chip.green .num { color: var(--green); }
.stat-chip.red .num { color: var(--red); }
.stat-chip.amber .num { color: var(--amber); }
.stat-chip.blue .num { color: var(--accent-blue); }
.stat-chip.purple .num { color: var(--accent-purple); }

/* ─── Section ─── */
.section { margin-bottom: 36px; }
.section-title {
  font-size: 20px; font-weight: 700; margin-bottom: 20px;
  display: flex; align-items: center; gap: 10px;
}
.section-title .icon { font-size: 22px; }

/* ─── Nav Tabs ─── */
.nav-tabs {
  display: flex; gap: 4px; margin-bottom: 28px;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 12px; padding: 4px; flex-wrap: wrap;
}
.nav-tab {
  padding: 10px 22px; border-radius: 10px; cursor: pointer;
  font-size: 14px; font-weight: 500; color: var(--text-secondary);
  transition: all 0.2s; border: none; background: none;
}
.nav-tab:hover { color: var(--text-primary); background: rgba(255,255,255,0.04); }
.nav-tab.active {
  color: #fff; background: var(--accent-blue);
  box-shadow: 0 2px 12px rgba(59,130,246,0.3);
}
.tab-panel { display: none; animation: fadeIn 0.3s ease; }
.tab-panel.active { display: block; }
@keyframes fadeIn { from { opacity:0; transform: translateY(8px); } to { opacity:1; transform: translateY(0); } }

/* ─── Timeline ─── */
.timeline { position: relative; padding-left: 40px; }
.timeline::before {
  content: ''; position: absolute; left: 15px; top: 0; bottom: 0;
  width: 2px; background: linear-gradient(180deg, var(--accent-blue), var(--accent-purple), var(--accent-cyan), transparent);
}
.tl-event {
  position: relative; margin-bottom: 20px; padding: 20px 24px;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--radius); transition: all 0.25s;
  backdrop-filter: blur(12px);
}
.tl-event:hover { border-color: var(--border-hover); transform: translateX(4px); box-shadow: var(--shadow); }
.tl-event::before {
  content: ''; position: absolute; left: -33px; top: 24px;
  width: 12px; height: 12px; border-radius: 50%;
  border: 2px solid var(--bg-primary);
}
.tl-event.corroborated { border-left: 3px solid var(--green); }
.tl-event.corroborated::before { background: var(--green); box-shadow: 0 0 8px var(--green); }
.tl-event.contested { border-left: 3px solid var(--red); }
.tl-event.contested::before { background: var(--red); box-shadow: 0 0 8px var(--red); }
.tl-event.single_source { border-left: 3px solid var(--amber); }
.tl-event.single_source::before { background: var(--amber); box-shadow: 0 0 8px var(--amber); }

.tl-time {
  font-family: 'JetBrains Mono', monospace; font-size: 12px;
  color: var(--accent-cyan); margin-bottom: 6px; letter-spacing: 0.5px;
}
.tl-desc { font-size: 14px; margin-bottom: 8px; font-weight: 500; }
.tl-meta { font-size: 12px; color: var(--text-secondary); display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.tl-badge {
  font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 20px;
  text-transform: uppercase; letter-spacing: 0.5px;
}
.tl-badge.corroborated { background: var(--green-bg); color: var(--green); }
.tl-badge.contested { background: var(--red-bg); color: var(--red); }
.tl-badge.single_source { background: var(--amber-bg); color: var(--amber); }
.role-badge {
  font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 20px;
  text-transform: uppercase; letter-spacing: 0.4px;
}
.role-badge.victim { background: rgba(239,68,68,0.12); color: #f87171; }
.role-badge.witness { background: rgba(59,130,246,0.12); color: #60a5fa; }
.role-badge.suspect { background: rgba(245,158,11,0.12); color: #fbbf24; }
.conflict-detail {
  margin-top: 12px; padding: 12px 16px; border-radius: var(--radius-sm);
  background: var(--red-bg); border: 1px solid rgba(239,68,68,0.15); font-size: 13px;
}
.conflict-detail .cd-label { color: var(--red); font-weight: 600; font-size: 11px; text-transform: uppercase; margin-bottom: 6px; }
.conflict-versions { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 8px; }
.cv-item { padding: 10px; border-radius: 8px; background: rgba(0,0,0,0.2); font-size: 12px; }
.cv-item .cv-speaker { color: var(--accent-cyan); font-weight: 600; font-size: 11px; margin-bottom: 4px; }

/* ─── Conflict Resolution ─── */
.cr-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 768px) { .cr-grid { grid-template-columns: 1fr; } }
.cr-card {
  padding: 20px; border-radius: var(--radius); border: 1px solid var(--border);
  background: var(--bg-card);
}
.cr-card h3 { font-size: 14px; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.cr-list { list-style: none; }
.cr-list li {
  padding: 8px 12px; margin-bottom: 6px; border-radius: var(--radius-sm);
  font-size: 13px; font-family: 'JetBrains Mono', monospace;
}
.cr-list.selected li { background: var(--green-bg); border-left: 2px solid var(--green); }
.cr-list.rejected li { background: var(--red-bg); border-left: 2px solid var(--red); }

/* ─── PageRank Bars ─── */
.pr-bar-row {
  display: flex; align-items: center; gap: 12px; margin-bottom: 10px; font-size: 13px;
}
.pr-label {
  min-width: 140px; font-family: 'JetBrains Mono', monospace;
  font-size: 12px; text-align: right; color: var(--text-secondary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.pr-track { flex: 1; height: 24px; background: rgba(255,255,255,0.03); border-radius: 6px; overflow: hidden; }
.pr-fill {
  height: 100%; border-radius: 6px;
  background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
  transition: width 0.8s cubic-bezier(0.22, 1, 0.36, 1);
  min-width: 2px;
}
.pr-value { min-width: 50px; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--accent-cyan); }

/* ─── Entropy ─── */
.entropy-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.entropy-card {
  padding: 24px; border-radius: var(--radius); border: 1px solid var(--border);
  background: var(--bg-card);
}
.entropy-card .fact-label { font-size: 14px; font-weight: 600; margin-bottom: 16px; }
.entropy-gauge { position: relative; height: 8px; background: rgba(255,255,255,0.06); border-radius: 4px; overflow: hidden; margin-bottom: 10px; }
.entropy-gauge-fill { height: 100%; border-radius: 4px; transition: width 0.8s ease; }
.entropy-gauge-fill.low { background: var(--green); }
.entropy-gauge-fill.med { background: var(--amber); }
.entropy-gauge-fill.high { background: var(--red); }
.entropy-vals { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary); }
.entropy-vals .ent-num { font-family: 'JetBrains Mono', monospace; color: var(--accent-cyan); }
.entropy-interp {
  margin-top: 8px; padding: 8px 12px; border-radius: var(--radius-sm);
  background: rgba(255,255,255,0.03); font-size: 12px; color: var(--text-secondary);
}

/* ─── Speaker Dossiers ─── */
.speaker-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px; }
.speaker-card {
  border-radius: var(--radius); border: 1px solid var(--border);
  background: var(--bg-card); overflow: hidden; transition: all 0.25s;
}
.speaker-card:hover { border-color: var(--border-hover); box-shadow: var(--shadow); }
.speaker-head {
  padding: 20px 24px; cursor: pointer; display: flex; justify-content: space-between;
  align-items: center; user-select: none;
}
.speaker-head h3 { font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 10px; }
.speaker-head .arrow { transition: transform 0.25s; color: var(--text-muted); font-size: 18px; }
.speaker-card.open .arrow { transform: rotate(180deg); }
.speaker-body { padding: 0 24px; max-height: 0; overflow: hidden; transition: max-height 0.4s ease, padding 0.3s ease; }
.speaker-card.open .speaker-body { max-height: 5000px; padding: 0 24px 24px; }

.criteria-section { margin-bottom: 20px; }
.criteria-section h4 {
  font-size: 13px; font-weight: 600; color: var(--accent-blue);
  margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px;
}
.criterion-row {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.03); font-size: 13px;
}
.criterion-row:last-child { border-bottom: none; }
.cr-indicator { font-size: 14px; min-width: 20px; text-align: center; padding-top: 1px; }
.cr-name { font-weight: 500; min-width: 200px; }
.cr-strength {
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  color: var(--accent-cyan); min-width: 40px;
}
.cr-evidence { font-size: 12px; color: var(--text-secondary); font-style: italic; flex: 1; }

/* ─── RM Profiles ─── */
.rm-profiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
@media (max-width: 768px) { .rm-profiles { grid-template-columns: 1fr; } }
.rm-profile-card {
  padding: 14px 16px; border-radius: var(--radius-sm);
  border: 1px solid var(--border); background: rgba(255,255,255,0.02);
}
.rm-profile-card h5 { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 8px; }
.rm-profile-card .count { font-size: 28px; font-weight: 800; }
.rm-profile-card.external .count { color: var(--green); }
.rm-profile-card.internal .count { color: var(--accent-purple); }
.rm-profile-card.contextual .count { color: var(--amber); }

/* ─── Limitations ─── */
.limitations {
  margin-top: 40px; padding: 24px 28px; border-radius: var(--radius);
  background: rgba(245,158,11,0.04); border: 1px solid rgba(245,158,11,0.12);
}
.limitations h3 { color: var(--amber); font-size: 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.limitations ul { list-style: none; }
.limitations li { font-size: 13px; color: var(--text-secondary); padding: 4px 0; padding-left: 16px; position: relative; }
.limitations li::before { content: '•'; position: absolute; left: 0; color: var(--amber); }

/* ─── Scrollbar ─── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.15); }
"""


def _js() -> str:
    return r"""
(function() {
  const D = CASE_DATA;
  const app = document.getElementById('app');

  // ─── Helpers ───
  function el(tag, attrs, ...children) {
    const e = document.createElement(tag);
    if (attrs) Object.entries(attrs).forEach(([k,v]) => {
      if (k === 'className') e.className = v;
      else if (k === 'innerHTML') e.innerHTML = v;
      else if (k.startsWith('on')) e.addEventListener(k.slice(2).toLowerCase(), v);
      else e.setAttribute(k, v);
    });
    children.flat().forEach(c => {
      if (typeof c === 'string') e.appendChild(document.createTextNode(c));
      else if (c) e.appendChild(c);
    });
    return e;
  }

  function roleBadge(role) {
    return `<span class="role-badge ${role}">${role}</span>`;
  }

  function statusBadge(status) {
    const labels = { corroborated: 'Corroborated', contested: 'Contested', single_source: 'Single Source' };
    return `<span class="tl-badge ${status}">${labels[status] || status}</span>`;
  }

  // ─── Header ───
  function renderHeader() {
    const stmts = Object.values(D.statements || {});
    const tl = D.master_timeline || [];
    const conflicts = (D.cross_analysis || {}).conflicts || [];
    const corrs = (D.cross_analysis || {}).corroborations || [];

    const hdr = el('div', { className: 'case-header' },
      el('div', { className: 'case-id', innerHTML: D.case_id || '' }),
      el('h1', null, D.incident || 'Investigation Report'),
      el('div', { className: 'meta', innerHTML:
        `Date: <strong>${D.incident_date || '—'}</strong> &nbsp;|&nbsp; Timeframe: <strong>${D.incident_timeframe || '—'}</strong> &nbsp;|&nbsp; Generated: <strong>${(D.generated_at || '').slice(0,19).replace('T',' ')}</strong>`
      }),
      el('div', { className: 'stats-row' },
        el('div', { className: 'stat-chip blue' }, el('span', { className: 'num' }, ''+stmts.length), ' Statements'),
        el('div', { className: 'stat-chip purple' }, el('span', { className: 'num' }, ''+tl.length), ' Events'),
        el('div', { className: 'stat-chip red' }, el('span', { className: 'num' }, ''+conflicts.length), ' Conflicts'),
        el('div', { className: 'stat-chip green' }, el('span', { className: 'num' }, ''+corrs.length), ' Corroborations'),
      )
    );
    app.appendChild(hdr);
  }

  // ─── Tab Navigation ───
  function renderTabs() {
    const tabs = [
      { id: 'timeline', label: '🕒 Master Timeline' },
      { id: 'conflicts', label: '⚔️ Conflict Resolution' },
      { id: 'pagerank', label: '📊 Evidence Ranking' },
      { id: 'entropy', label: '🎲 Uncertainty' },
      { id: 'dossiers', label: '👤 Speaker Dossiers' },
    ];

    const nav = el('div', { className: 'nav-tabs' });
    const panels = {};

    tabs.forEach((t, i) => {
      const btn = el('button', {
        className: 'nav-tab' + (i === 0 ? ' active' : ''),
        id: 'tab-' + t.id,
        onClick: () => {
          nav.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          Object.values(panels).forEach(p => p.classList.remove('active'));
          panels[t.id].classList.add('active');
        }
      }, t.label);
      nav.appendChild(btn);
      const panel = el('div', { className: 'tab-panel' + (i === 0 ? ' active' : ''), id: 'panel-' + t.id });
      panels[t.id] = panel;
    });

    app.appendChild(nav);

    // Render content into panels
    renderTimeline(panels.timeline);
    renderConflictResolution(panels.conflicts);
    renderPageRank(panels.pagerank);
    renderEntropy(panels.entropy);
    renderDossiers(panels.dossiers);

    Object.values(panels).forEach(p => app.appendChild(p));
  }

  // ─── Timeline ───
  function renderTimeline(container) {
    const sec = el('div', { className: 'section' },
      el('div', { className: 'section-title' }, el('span', { className: 'icon' }, '🕒'), 'Unified Master Timeline')
    );
    const tl = el('div', { className: 'timeline' });

    (D.master_timeline || []).forEach(ev => {
      const timeStr = [ev.time_start, ev.time_end].filter(Boolean).join(' – ') || 'Time unknown';
      const card = el('div', { className: 'tl-event ' + ev.status });

      let inner = `<div class="tl-time">${esc(timeStr)}</div>`;
      inner += `<div class="tl-desc">${esc(ev.description)}</div>`;
      inner += `<div class="tl-meta">`;
      inner += `<span>${esc(ev.speaker_name)}</span>`;
      inner += roleBadge(ev.speaker_role);
      inner += statusBadge(ev.status);
      if (ev.location) inner += `<span>📍 ${esc(ev.location)}</span>`;
      inner += `</div>`;

      // Conflict details
      if (ev.status === 'contested' && ev.conflicts && ev.conflicts.length) {
        inner += `<div class="conflict-detail"><div class="cd-label">⚠ Contradiction Details</div>`;
        ev.conflicts.forEach(c => {
          inner += `<div style="margin-top:6px;font-size:12px;color:var(--text-secondary)">${esc(c.description || c.fact_category || '')}</div>`;
          if (c.version_a && c.version_b) {
            inner += `<div class="conflict-versions">`;
            inner += `<div class="cv-item"><div class="cv-speaker">Version A</div>${esc(c.version_a)}</div>`;
            inner += `<div class="cv-item"><div class="cv-speaker">Version B</div>${esc(c.version_b)}</div>`;
            inner += `</div>`;
          }
        });
        inner += `</div>`;
      }

      card.innerHTML = inner;
      tl.appendChild(card);
    });

    sec.appendChild(tl);
    container.appendChild(sec);
  }

  // ─── Conflict Resolution ───
  function renderConflictResolution(container) {
    const mis = D.conflict_graph_result || {};
    const sec = el('div', { className: 'section' },
      el('div', { className: 'section-title' }, el('span', { className: 'icon' }, '⚔️'), 'Conflict Resolution — Maximum Independent Set')
    );

    const desc = el('p', { className: 'meta', style: 'margin-bottom:16px;font-size:13px;color:var(--text-secondary)' });
    desc.textContent = `Algorithm: ${mis.algorithm || 'N/A'}. The largest set of mutually non-conflicting claims was selected.`;
    sec.appendChild(desc);

    const grid = el('div', { className: 'cr-grid' });

    // Selected
    const selCard = el('div', { className: 'cr-card' });
    selCard.innerHTML = `<h3><span style="color:var(--green)">✓</span> Selected (${(mis.selected_statements||[]).length})</h3>`;
    const selList = el('ul', { className: 'cr-list selected' });
    (mis.selected_statements || []).forEach(s => {
      selList.appendChild(el('li', null, s));
    });
    selCard.appendChild(selList);
    grid.appendChild(selCard);

    // Rejected
    const rejCard = el('div', { className: 'cr-card' });
    rejCard.innerHTML = `<h3><span style="color:var(--red)">✗</span> Rejected (${(mis.rejected_statements||[]).length})</h3>`;
    const rejList = el('ul', { className: 'cr-list rejected' });
    (mis.rejected_statements || []).forEach(s => {
      rejList.appendChild(el('li', null, s));
    });
    rejCard.appendChild(rejList);
    grid.appendChild(rejCard);

    sec.appendChild(grid);

    // Conflict pairs detail
    const conflicts = (D.cross_analysis || {}).conflicts || [];
    if (conflicts.length) {
      const pairsSec = el('div', { style: 'margin-top:24px' });
      pairsSec.innerHTML = `<h3 style="font-size:14px;font-weight:600;margin-bottom:12px">Contradiction Pairs (${conflicts.length})</h3>`;
      conflicts.forEach(c => {
        const pair = el('div', { className: 'conflict-detail', style: 'margin-bottom:10px' });
        pair.innerHTML = `
          <div class="cd-label">${esc(c.fact_category || 'conflict')}</div>
          <div style="font-size:13px;margin-bottom:6px">${esc(c.description || '')}</div>
          <div class="conflict-versions">
            <div class="cv-item"><div class="cv-speaker">${esc(c.event_a_id || '')}</div>${esc(c.version_a || '')}</div>
            <div class="cv-item"><div class="cv-speaker">${esc(c.event_b_id || '')}</div>${esc(c.version_b || '')}</div>
          </div>`;
        pairsSec.appendChild(pair);
      });
      sec.appendChild(pairsSec);
    }

    container.appendChild(sec);
  }

  // ─── PageRank ───
  function renderPageRank(container) {
    const pr = D.pagerank_result || {};
    const scores = pr.scores || {};
    const ranking = pr.ranking || Object.keys(scores).sort((a,b) => scores[b] - scores[a]);

    const sec = el('div', { className: 'section' },
      el('div', { className: 'section-title' }, el('span', { className: 'icon' }, '📊'), 'Evidence Corroboration Ranking (PageRank)')
    );

    const desc = el('p', { style: 'margin-bottom:20px;font-size:13px;color:var(--text-secondary)' });
    desc.textContent = 'Higher scores indicate claims with more structural corroboration from other sources.';
    sec.appendChild(desc);

    const maxScore = Math.max(...Object.values(scores), 0.001);

    ranking.slice(0, 30).forEach(nodeId => {
      const score = scores[nodeId] || 0;
      const pct = (score / maxScore * 100).toFixed(1);
      const row = el('div', { className: 'pr-bar-row' });
      row.innerHTML = `
        <div class="pr-label" title="${esc(nodeId)}">${esc(nodeId)}</div>
        <div class="pr-track"><div class="pr-fill" style="width:${pct}%"></div></div>
        <div class="pr-value">${score.toFixed(4)}</div>`;
      sec.appendChild(row);
    });

    container.appendChild(sec);
  }

  // ─── Entropy ───
  function renderEntropy(container) {
    const results = D.entropy_results || [];
    const sec = el('div', { className: 'section' },
      el('div', { className: 'section-title' }, el('span', { className: 'icon' }, '🎲'), 'Uncertainty Analysis (Shannon Entropy)')
    );

    if (!results.length) {
      sec.appendChild(el('p', { style: 'color:var(--text-secondary);font-size:14px' }, 'No contested facts detected.'));
      container.appendChild(sec);
      return;
    }

    const desc = el('p', { style: 'margin-bottom:20px;font-size:13px;color:var(--text-secondary)' });
    desc.textContent = 'Entropy measures disagreement across witness accounts for each contested fact. Higher entropy = more uncertainty.';
    sec.appendChild(desc);

    const grid = el('div', { className: 'entropy-grid' });
    results.forEach(r => {
      const ne = r.normalized_entropy || 0;
      const level = ne < 0.33 ? 'low' : ne < 0.67 ? 'med' : 'high';
      const card = el('div', { className: 'entropy-card' });
      card.innerHTML = `
        <div class="fact-label">${esc(r.fact || 'Unknown')}</div>
        <div class="entropy-gauge"><div class="entropy-gauge-fill ${level}" style="width:${(ne*100).toFixed(0)}%"></div></div>
        <div class="entropy-vals">
          <span>Entropy: <span class="ent-num">${(r.entropy||0).toFixed(3)} bits</span></span>
          <span>Normalized: <span class="ent-num">${ne.toFixed(3)}</span></span>
        </div>
        <div class="entropy-interp">${esc(r.interpretation || '')}</div>`;
      grid.appendChild(card);
    });
    sec.appendChild(grid);
    container.appendChild(sec);
  }

  // ─── Speaker Dossiers ───
  function renderDossiers(container) {
    const sec = el('div', { className: 'section' },
      el('div', { className: 'section-title' }, el('span', { className: 'icon' }, '👤'), 'Individual Speaker Dossiers')
    );

    const grid = el('div', { className: 'speaker-grid' });

    Object.values(D.statements || {}).forEach(stmt => {
      const card = el('div', { className: 'speaker-card' });

      // Head
      const head = el('div', { className: 'speaker-head' });
      head.innerHTML = `<h3>${esc(stmt.speaker_name)} ${roleBadge(stmt.speaker_role)}</h3><span class="arrow">▼</span>`;
      head.addEventListener('click', () => card.classList.toggle('open'));
      card.appendChild(head);

      // Body
      const body = el('div', { className: 'speaker-body' });

      // CBCA
      const cbca = stmt.cbca_result || {};
      const cbcaCriteria = cbca.criteria || {};
      const cbcaSummary = cbca.summary || {};
      body.innerHTML = `
        <div class="criteria-section">
          <h4>CBCA Analysis — ${cbcaSummary.observed_criteria || 0} criteria observed</h4>
          ${renderCriteriaTable(cbcaCriteria, 'cbca')}
        </div>`;

      // RM
      const rm = stmt.rm_result || {};
      const rmCriteria = rm.criteria || {};
      const rmSummary = rm.summary || {};
      const ext = Object.keys(rmSummary.external_memory_profile || {}).length;
      const int_ = Object.keys(rmSummary.internal_memory_profile || {}).length;
      const ctx = Object.keys(rmSummary.contextual_profile || {}).length;

      body.innerHTML += `
        <div class="criteria-section">
          <h4>Reality Monitoring Analysis</h4>
          <div class="rm-profiles">
            <div class="rm-profile-card external"><h5>External Memory</h5><div class="count">${ext}</div></div>
            <div class="rm-profile-card internal"><h5>Internal Memory</h5><div class="count">${int_}</div></div>
            <div class="rm-profile-card contextual"><h5>Contextual</h5><div class="count">${ctx}</div></div>
          </div>
          ${renderCriteriaTable(rmCriteria, 'rm')}
        </div>`;

      card.appendChild(body);
      grid.appendChild(card);
    });

    sec.appendChild(grid);
    container.appendChild(sec);
  }

  function renderCriteriaTable(criteria, type) {
    let html = '';
    Object.entries(criteria).forEach(([key, c]) => {
      const observed = type === 'cbca' ? c.observed : c.observed;
      const icon = observed === true ? '✅' : observed === false ? '❌' : '➖';
      const strength = c.evidence_strength != null ? (c.evidence_strength * 100).toFixed(0) + '%' : '—';
      const evidence = (c.evidence || []).join(' | ') || '';
      const name = c.name || key;
      html += `
        <div class="criterion-row">
          <span class="cr-indicator">${icon}</span>
          <span class="cr-name">${esc(name)}</span>
          <span class="cr-strength">${strength}</span>
          <span class="cr-evidence">${esc(evidence.substring(0, 120))}${evidence.length > 120 ? '…' : ''}</span>
        </div>`;
    });
    return html;
  }

  // ─── Limitations ───
  function renderLimitations() {
    const lims = el('div', { className: 'limitations' });
    lims.innerHTML = `<h3>⚠️ Scientific & Ethical Limitations</h3><ul>
      <li>CBCA and Reality Monitoring are research frameworks, not lie detectors.</li>
      <li>Presence or absence of criteria does not establish truthfulness or deception.</li>
      <li>Evidence strength reflects textual characteristic prominence, not probability of truth.</li>
      <li>Conflict resolution is algorithmic (greedy MIS approximation) and may not reflect ground truth.</li>
      <li>PageRank scores measure structural corroboration, not factual accuracy.</li>
      <li>Entropy measures disagreement, not which version is correct.</li>
      <li>LLM-based extraction may contain errors; annotations should be verified by a human expert.</li>
      <li>This report is a decision-support tool, not a substitute for professional forensic analysis.</li>
    </ul>`;
    app.appendChild(lims);
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
  }

  // ─── Render All ───
  renderHeader();
  renderTabs();
  renderLimitations();
})();
"""


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python report_generator.py <case_result.json> <output.html>")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    generate_report(data, sys.argv[2])
    print(f"Report generated: {sys.argv[2]}")
